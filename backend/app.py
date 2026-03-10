from fastapi import FastAPI
from pydantic import BaseModel
from backend.retrieval import get_top_chunks, graph_search
from evaluation.evaluate import log_metrics_to_snowflake
import os, time
from google import genai
from google.genai import types
from scripts.sf_connect import get_conn
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

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


def save_to_history(query_text: str, answer: str, citations: list):
    """
    Saves the query details to /backend/history.json.
    """
    # 1. Define path and ensure directory exists
    history_path = Path("backend/history.json")
    history_path.parent.mkdir(parents=True, exist_ok=True)

    # 2. Create the new history entry
    new_entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query_text,
        "answer": answer,
        "chunks": citations  # citations contains the chunk metadata from your return
    }

    # 3. Load existing data or initialize a new list
    if history_path.exists():
        with open(history_path, "r", encoding="utf-8") as f:
            try:
                history_data = json.load(f)
            except json.JSONDecodeError:
                history_data = []
    else:
        history_data = []

    # 4. Append and save
    history_data.append(new_entry)
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history_data, f, indent=4, ensure_ascii=False)



class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    passcode: str = ""

@app.post('/query')
def query(req: QueryRequest):
    try:
        return _query_logic(req)
    except Exception as e:
        import traceback
        print("\n=== CRITICAL ERROR IN /query ===")
        traceback.print_exc()
        print("================================\n")
        raise e

def _query_logic(req: QueryRequest):
    start = time.time()
    conn = get_active_conn(passcode=req.passcode.strip())

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

    contents = [types.Content(role="user", parts=[types.Part.from_text(text=req.question)])]

    max_iterations = 5
    iterations = 0
    all_citations = []

    # Track the highest chunk confidence seen during the loop
    max_confidence = 0.0

    print(f"\n--- Starting Agentic Loop for query: '{req.question}' ---")

    while iterations < max_iterations:
        iterations += 1
        print(f"\n[Iteration {iterations}/{max_iterations}] Calling LLM...")

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

                print(f"  -> Tool Call: {function_name}({arguments})")

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

                print(f"  <- Tool Returning {len(tool_result)} characters of context.")
                tool_response_parts.append(
                    types.Part.from_function_response(name=function_name, response={"result": tool_result})
                )

            # Append all tool results back to the conversation
            contents.append(types.Content(role="user", parts=tool_response_parts))

        # If the model replies with text (final answer phase)
        else:
            text_parts = [part.text for part in candidate.content.parts if part.text]
            if text_parts:
                print(f"  -> Model provided a text response. Exiting loop.")
                answer = "\n".join(text_parts)
                break

    else:
        # If we broke out of the while loop because of iterations
        print("  -> Hit max iterations without a final text answer. Forcing generation.")
        answer = "I apologize, but I was unable to compile a complete answer after searching the databases."
        if all_citations:
             answer += "\nHowever, I did find some relevant sources, though I couldn't synthesize them in time."

    result = {
        'answer': answer,
        'citations': all_citations,
        'confidence': round(max_confidence, 3),
        'retrieval_mode': 'agentic',
        'latency_ms': int((time.time() - start) * 1000)
    }

    save_to_history(
        query_text=req.question, 
        answer=result['answer'], 
        citations=result['citations']
    )

    context_used = "\n".join([c['text'] for c in result['citations']])
    log_data = {
        'question': req.question,
        'answer': result['answer'],
        'context_used': context_used[:10000], # max length to be safe
        'retrieval_mode': result['retrieval_mode'],
        'confidence': result['confidence'],
        'latency_ms': result['latency_ms']
    }
    
    try:
        log_metrics_to_snowflake(log_data, conn=conn)
        print("Successfully logged metrics to Snowflake.")
    except Exception as e:
        print(f"Failed to log metrics: {e}")

    return result

@app.get('/papers')
def papers(passcode: str = ""):
    conn = get_active_conn(passcode=passcode.strip())
    cur = conn.cursor()
    
    # 1. Setup session context
    cur.execute('USE WAREHOUSE ROHAN_BLAKE_KENNETH_WH')
    cur.execute('USE DATABASE CS5542_PROJECT_ROHAN_BLAKE_KENNETH')

    query = f"""
    SELECT * FROM RAW.PAPERS;
    """
    cur.execute(query)
    rows = cur.fetchall()
    return rows

@app.get('/health')
def health(): return {'status': 'ok'}

