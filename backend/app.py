from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.retrieval import get_top_chunks, graph_search, use_snowflake_session_context
from evaluation.evaluate import log_metrics_to_snowflake
import os, time
from google import genai
from google.genai import types
from scripts.sf_connect import get_conn
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import csv
import uuid
from backend.logger import logger, query_id_var, latency_var

# Load .env file
load_dotenv()

app = FastAPI(title="Research Assistant API")
@app.get("/")
def read_root():
    return {"message": "Welcome to the Research Assistant API"}

# --- Connection Caching ---
_GLOBAL_CONN = None

def get_active_conn(passcode: str = ""):
    global _GLOBAL_CONN
    if _GLOBAL_CONN is not None and not _GLOBAL_CONN.is_closed():
        return _GLOBAL_CONN
        
    # If no active connection, we must create one.
    _GLOBAL_CONN = get_conn(passcode=passcode.strip())
    return _GLOBAL_CONN

class AuthRequest(BaseModel):
    passcode: str = ""

@app.post("/auth")
def authenticate(req: AuthRequest):
    global _GLOBAL_CONN
    try:
        # Force a new connection for fresh auth
        if _GLOBAL_CONN is not None and not _GLOBAL_CONN.is_closed():
            _GLOBAL_CONN.close()
            
        _GLOBAL_CONN = get_conn(passcode=req.passcode.strip())
        return {"status": "success", "message": "Successfully authenticated with Snowflake."}
    except Exception as e:
        return {"status": "error", "message": f"Authentication failed: {str(e)}"}


def save_to_csv_log(req_question: str, result: dict):
    """
    Appends query metrics and results to /logs/query_log.csv.
    """
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "query_log.csv"
    
    # Define the columns we want to track
    fieldnames = ['timestamp', 'question', 'answer_preview', 'confidence', 'retrieval_mode', 'latency_ms']
    
    file_exists = log_file.exists()
    
    with open(log_file, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # Write header only if we are creating the file for the first time
        if not file_exists:
            writer.writeheader()
        
        writer.writerow({
            'timestamp': datetime.now().isoformat(),
            'question': req_question,
            'answer_preview': result['answer'][:100].replace('\n', ' ') + "...", # Keep CSV tidy
            'confidence': result['confidence'],
            'retrieval_mode': result['retrieval_mode'],
            'latency_ms': result['latency_ms']
        })

def save_to_history(query_text: str, answer: str, citations: list,
                    confidence: float = 0.0, latency_ms: int = 0,
                    retrieval_mode: str = "", tool_calls: list = None,
                    num_iterations: int = 0, chat_id: str = None):
    """
    Saves the query details to /backend/history.json grouped by chat_id.
    """
    history_path = Path("backend/history.json")
    history_path.parent.mkdir(parents=True, exist_ok=True)

    if history_path.exists():
        with open(history_path, "r", encoding="utf-8") as f:
            try:
                history_data = json.load(f)
            except json.JSONDecodeError:
                history_data = []
    else:
        history_data = []

    # Format the message packet
    msg_packet = {
        "timestamp": datetime.now().isoformat(),
        "query": query_text,
        "answer": answer,
        "chunks": citations,
        "confidence": confidence,
        "latency_ms": latency_ms,
        "retrieval_mode": retrieval_mode,
        "tool_calls": tool_calls or [],
        "num_iterations": num_iterations,
    }

    # Search for an existing chat ID
    found = False
    if chat_id:
        for chat in history_data:
            if chat.get("chat_id") == chat_id:
                chat["messages"].append(msg_packet)
                chat["updated_at"] = datetime.now().isoformat()
                found = True
                break
                
    if not found:
        # Create a new chat object
        if not chat_id:
            chat_id = uuid.uuid4().hex
        new_chat = {
            "chat_id": chat_id,
            "title": query_text[:50] + "..." if len(query_text) > 50 else query_text,
            "updated_at": datetime.now().isoformat(),
            "messages": [msg_packet]
        }
        history_data.append(new_chat)

    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history_data, f, indent=4, ensure_ascii=False)



class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    passcode: str = ""
    chat_id: Optional[str] = None
    chat_history: List[Dict[str, Any]] = []

@app.post('/query')
def query(req: QueryRequest):
    try:
        return _query_logic(req)
    except Exception as e:
        logger.error("CRITICAL ERROR IN /query", exc_info=True)
        raise e

def _query_logic(req: QueryRequest):
    start = time.time()
    conn = get_active_conn(passcode=req.passcode.strip())
    
    # Setup Request Tracing
    current_log_id = uuid.uuid4().hex
    query_id_var.set(current_log_id)
    latency_var.set("N/A")

    gemini_client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    model_id = "gemini-2.5-flash"

    # Define the tools available to the model using Gemini's format
    search_vector_db = types.FunctionDeclaration(
        name="search_vector_database",
        description="Searches a database of academic papers to find contextually relevant text chunks based on semantic similarity.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "query": types.Schema(type=types.Type.STRING, description="The search string to use for finding relevant text in the database."),
                "top_k": types.Schema(type=types.Type.INTEGER, description="The number of top results to return. Keep this small (e.g., 5-10) to avoid overloading context.")
            },
            required=["query", "top_k"]
        )
    )

    search_kg = types.FunctionDeclaration(
        name="search_knowledge_graph",
        description="Searches a knowledge graph of scientific concepts extracted from academic papers. Returns CO_OCCURS relationships showing which methods, models, and techniques appear together. Use this tool to discover connections between concepts that may not appear in the same text chunk.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "query": types.Schema(type=types.Type.STRING, description="A natural language query describing the relationships or entities you are investigating.")
            },
            required=["query"]
        )
    )

    gemini_tools = types.Tool(function_declarations=[search_vector_db, search_kg])

    # Setup the robust system prompt for the Autonomous RAG Agent
    system_prompt = (
        "You are an autonomous Research Assistant specialized in analyzing academic papers and their relationships.\n\n"
        "You have access to two tools:\n"
        "  1. search_vector_database — finds relevant text passages from papers via semantic similarity.\n"
        "  2. search_knowledge_graph — finds relationships between scientific concepts (e.g., which methods co-occur with which datasets).\n"
        "When the user asks a question, act as an autonomous agent. You MUST use BOTH tools at least once to gather comprehensive evidence before answering.\n"
        "Start with a vector search, then use the knowledge graph to discover related concepts, then optionally refine with another vector search.\n\n"
        "CRITICAL INSTRUCTIONS FOR ANSWERING:\n"
        "1. You MUST explicitly cite the sources of your claims using the index number of the text chunks provided via the vector database.\n"
        "2. Format citations as [1], [2], etc.\n"
        "3. Never invent facts, and never invent citations.\n"
        "4. If you use information from the knowledge graph, explicitly state the relationship."
    )

    chat_id = req.chat_id if req.chat_id else uuid.uuid4().hex
    
    contents = []
    
    if req.chat_history:
        history_text = "Here is the prior conversation history for context:\n"
        for msg in req.chat_history:
            role_label = "Assistant" if msg.get("role") in ["assistant", "model"] else "User"
            history_text += f"{role_label}: {msg.get('content')}\n\n"
        
        history_text += f"Now, answer the user's newest question:\nUser: {req.question}"
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=history_text)]))
    else:
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=req.question)]))

    max_iterations = 5
    iterations = 0
    all_citations = []
    tool_calls = [] 

    # Track the highest chunk confidence seen during the loop
    max_confidence = 0.0

    logger.info(f"Starting Agentic Loop for query: '{req.question}'")

    while iterations < max_iterations:
        iterations += 1
        logger.info(f"[Iteration {iterations}/{max_iterations}] Calling LLM...")

        response = gemini_client.models.generate_content(
            model=model_id,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[gemini_tools],
                max_output_tokens=600,
            )
        )

        candidate = response.candidates[0]

        # Check if the model wants to call tools
        function_calls = [part for part in candidate.content.parts if part.function_call]

        if function_calls:
            # Append the model's response (with function calls) to conversation
            contents.append(candidate.content)

            tool_response_parts = []

            for fc_part in function_calls:
                fc = fc_part.function_call
                function_name = fc.name
                arguments = dict(fc.args) if fc.args else {}

                tool_calls.append(function_name)
                logger.info(f"-> Tool Call: {function_name}({arguments})")

                if function_name == "search_vector_database":
                    search_query = arguments.get("query", req.question)
                    k = int(arguments.get("top_k", req.top_k))
                    chunks = get_top_chunks(conn=conn, query_text=search_query, top_k=k)

                    if chunks and chunks[0][0] > max_confidence:
                        max_confidence = chunks[0][0]

                    formatted_chunks = []
                    start_idx = len(all_citations) + 1

                    for i, chunk in enumerate(chunks, start=start_idx):
                        title = chunk[3]
                        section = chunk[4]
                        text = chunk[5]

                        formatted_string = f"[{i}] Paper Title: {title}\nSection: {section}\nText: {text}"
                        formatted_chunks.append(formatted_string)

                        all_citations.append({
                            'chunk_id': chunk[1],
                            'paper_id': chunk[2],
                            'title': chunk[3],
                            'section': chunk[4],
                            'text': chunk[5][:200],
                            'score': chunk[0]
                        })

                    tool_result = '\n\n'.join(formatted_chunks) if formatted_chunks else "No results found in the vector database."

                elif function_name == "search_knowledge_graph":
                    search_query = arguments.get("query", req.question)
                    graph_data = graph_search(conn=conn, query=search_query)

                    if graph_data:
                        formatted_rels = [f"{r['source']} -[{r['relation']}]-> {r['target']} (Weight: {r['weight']})" for r in graph_data]
                        tool_result = "Knowledge Graph Matches Found:\n" + "\n".join(formatted_rels)
                    else:
                        tool_result = "No relationships found in the knowledge graph for the given query."

                else:
                    tool_result = f"Error: Tool '{function_name}' is not recognized."

                logger.info(f"<- Tool Returning {len(tool_result)} characters of context.")
                tool_response_parts.append(
                    types.Part.from_function_response(name=function_name, response={"result": tool_result})
                )

            # Append all tool results back to the conversation
            contents.append(types.Content(role="user", parts=tool_response_parts))

        # If the model replies with text (final answer phase)
        else:
            text_parts = [part.text for part in candidate.content.parts if part.text]
            if text_parts:
                logger.info("-> Model provided a text response. Exiting loop.")
                answer = "\n".join(text_parts)
                break

    else:
        # If we broke out of the while loop because of iterations
        logger.warning("Hit max iterations without a final text answer. Forcing generation.")
        answer = "I apologize, but I was unable to compile a complete answer after searching the databases."
        if all_citations:
             answer += "\nHowever, I did find some relevant sources, though I couldn't synthesize them in time."

    # Finalize metrics
    final_latency = int((time.time() - start) * 1000)
    latency_var.set(f"{final_latency}ms") # Update logger context

    result = {
        'chat_id': chat_id,
        'answer': answer,
        'citations': all_citations,
        'confidence': round(max_confidence, 3),
        'retrieval_mode': 'agentic',
        'latency_ms': final_latency,
        'tool_calls': tool_calls,         
        'num_iterations': iterations      
    }

    save_to_csv_log(req.question, result)
    
    save_to_history(
        query_text=req.question,
        answer=result['answer'],
        citations=result['citations'],
        confidence=result['confidence'],
        latency_ms=result['latency_ms'],
        retrieval_mode=result['retrieval_mode'],
        tool_calls=result['tool_calls'],
        num_iterations=result['num_iterations'],
        chat_id=chat_id
    )

    context_used = "\n".join([c['text'] for c in result['citations']])
    log_data = {
        'log_id': current_log_id,
        'question': req.question,
        'answer': result['answer'],
        'context_used': context_used[:10000],
        'retrieval_mode': result['retrieval_mode'],
        'confidence': result['confidence'],
        'latency_ms': result['latency_ms'],
        'tool_calls': result['tool_calls'],
        'num_iterations': result['num_iterations']
    }
    
    try:
        log_metrics_to_snowflake(log_data, conn=conn)
        logger.info("Successfully logged metrics to Snowflake.")
    except Exception as e:
        logger.error(f"Failed to log metrics to Snowflake: {e}")

    return result

@app.get('/papers')
def papers(passcode: str = ""):
    conn = get_active_conn(passcode=passcode.strip())
    cur = conn.cursor()
    
    use_snowflake_session_context(cur)

    query = f"""
    SELECT * FROM RAW.PAPERS;
    """
    cur.execute(query)
    rows = cur.fetchall()
    return rows

@app.get('/history')
def history():
    history_path = Path("backend/history.json")
    if not history_path.exists():
        return []
    with open(history_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

@app.get("/health/snowflake")
def health_snowflake(passcode: str = ""):
    """
    Snowflake connectivity + row counts for RAW / GRAPH / APP tables (from INFORMATION_SCHEMA).

    Uses the same optional MFA `passcode` query param as `/papers` if your account needs it.
    Row counts are whatever Snowflake exposes in INFORMATION_SCHEMA (can be stale for very large tables).
    """
    try:
        conn = get_active_conn(passcode=passcode.strip())
        cur = conn.cursor()
        use_snowflake_session_context(cur)
        cur.execute(
            """
            SELECT TABLE_SCHEMA, TABLE_NAME, ROW_COUNT, TABLE_TYPE
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA IN ('RAW', 'GRAPH', 'APP')
            ORDER BY TABLE_SCHEMA, TABLE_NAME
            """
        )
        rows = cur.fetchall()
        tables = [
            {
                "schema": r[0],
                "name": r[1],
                "row_count": r[2],
                "table_type": r[3],
            }
            for r in rows
        ]
        return {
            "status": "ok",
            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
            "database": os.getenv("SNOWFLAKE_DATABASE"),
            "tables": tables,
            "note": "ROW_COUNT comes from INFORMATION_SCHEMA.TABLES (NULL for some views; may be approximate).",
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Snowflake health check failed: {e}",
        ) from e

@app.get('/health')
def health(): return {'status': 'ok'}

@app.get('/metrics/history')
def get_metrics_history(passcode: str = "", limit: int = 100):
    """Returns per-query rows from EVAL_METRICS for dashboard charts."""
    conn = get_active_conn(passcode=passcode.strip())
    try:
        cur = conn.cursor()
        use_snowflake_session_context(cur)
        cur.execute("""
            SELECT LOG_ID, QUESTION, CONFIDENCE, LATENCY_MS, RETRIEVAL_MODE,
                   NUM_ITERATIONS, TOOL_CALLS, TIMESTAMP
            FROM APP.EVAL_METRICS
            ORDER BY TIMESTAMP DESC
            LIMIT %s
        """, (limit,))
        columns = [desc[0] for desc in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        return rows
    except Exception as e:
        logger.error(f"Metrics history fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch metrics history")
    finally:
        cur.close()

@app.get('/metrics')
def get_metrics(passcode: str = ""):
    """Returns aggregated stats for the Streamlit dashboard."""
    conn = get_active_conn(passcode=passcode.strip())
    try:
        cur = conn.cursor()
        use_snowflake_session_context(cur)
        
        # Core aggregates
        query = """
        SELECT 
            COUNT(LOG_ID) as total_queries,
            AVG(LATENCY_MS) as avg_latency,
            AVG(CONFIDENCE) as avg_confidence,
            AVG(NUM_ITERATIONS) as avg_iterations
        FROM APP.EVAL_METRICS;
        """
        cur.execute(query)
        row = cur.fetchone()
        
        # Grouped counts by retrieval mode
        mode_query = """
        SELECT RETRIEVAL_MODE, COUNT(*) as count 
        FROM APP.EVAL_METRICS 
        GROUP BY RETRIEVAL_MODE;
        """
        cur.execute(mode_query)
        modes = {r[0]: r[1] for r in cur.fetchall()}
        
        return {
            "total_queries": row[0] or 0,
            "avg_latency_ms": round(row[1] or 0, 2),
            "avg_confidence": round(row[2] or 0, 3),
            "avg_iterations": round(row[3] or 0, 2),
            "retrieval_modes": modes
        }
    except Exception as e:
        logger.error(f"Metrics fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch metrics")
    finally:
        cur.close()