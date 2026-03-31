import sys
import os
from pathlib import Path
from datasets import Dataset
from ragas import evaluate
import math
import json

from ragas.metrics import Faithfulness, AnswerRelevancy

# Modern Google GenAI Imports
from ragas.llms import llm_factory
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from google import genai

root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))
from backend.logger import logger
from scripts.sf_connect import get_conn


def run_ragas_evaluation(conn):
    """Batch job to backfill Ragas scores for rows with NULL metrics."""
    logger.info("Starting Ragas batch evaluation...")
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT LOG_ID, QUESTION, GENERATED_RESPONSE, CONTEXT_USED 
            FROM APP.EVAL_METRICS 
            WHERE FAITHFULNESS_SCORE IS NULL OR ANSWER_RELEVANCE_SCORE IS NULL LIMIT 20
        """)
        rows = cur.fetchall()
        
        if not rows:
            logger.info("No records found requiring Ragas evaluation.")
            return

        # Modern Ragas expects updated column names
        data = {
            "user_input": [],       
            "response": [],         
            "retrieved_contexts": [], 
            "ids": []
        }
        for r in rows:
            data["ids"].append(r[0])
            data["user_input"].append(r[1])
            data["response"].append(r[2])
            data["retrieved_contexts"].append([r[3]])

        dataset = Dataset.from_dict(data)
        
        # Initialize Google GenAI Client
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is missing.")
            
        client = genai.Client(api_key=api_key)
        
        # Setup Ragas-compatible LLM (forces structured JSON output natively)
        evaluator_llm = llm_factory(
            model="gemini-3.1-flash-lite-preview", 
            provider="google", 
            client=client
        )
        
        # Setup Langchain-compatible Google Embeddings
        evaluator_embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001", 
            google_api_key=api_key
        )

        # Initialize the STANDARD metric objects (compatible with evaluate())
        ragas_metrics = [
            Faithfulness(llm=evaluator_llm),
            AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings)
        ]

        # Evaluate
        results = evaluate(dataset, metrics=ragas_metrics)
        df = results.to_pandas()

        for idx, row in df.iterrows():
            # Safely extract values
            raw_f = row.get('faithfulness', 0.0)
            raw_a = row.get('answer_relevancy', 0.0)
            
            # Convert to float and catch NaNs
            f_score = None if math.isnan(float(raw_f)) else float(raw_f)
            a_score = None if math.isnan(float(raw_a)) else float(raw_a)
            
            cur.execute(
                "UPDATE APP.EVAL_METRICS SET FAITHFULNESS_SCORE = %s, ANSWER_RELEVANCE_SCORE = %s WHERE LOG_ID = %s",
                (f_score, a_score, data["ids"][idx])
            )
            
        logger.info(f"Successfully updated {len(rows)} records with Ragas scores.")
        
    except Exception as e:
        logger.error(f"Ragas evaluation failed: {e}", exc_info=True)
    finally:
        cur.close()

def log_metrics_to_snowflake(log_data: dict, conn=None):
    '''
    Automatically capture Q&A pairs, retrieval latency, and confidence scores back to APP.EVAL_METRICS.
    '''
    if not conn:
        raise ValueError("A valid Snowflake connection is required.")
        
    try:
        cur = conn.cursor()
        
        # Extract variables from our payload
        log_id = log_data.get('log_id')
        question = log_data.get('question', '')
        answer = log_data.get('answer', '')
        context_used = log_data.get('context_used', '')
        retrieval_mode = log_data.get('retrieval_mode', 'agentic')
        confidence = log_data.get('confidence', 0.0)
        latency_ms = log_data.get('latency_ms', 0)
        tool_calls = log_data.get('tool_calls', [])
        num_iterations = log_data.get('num_iterations', 0)
        
        # Serialize list to JSON string for Snowflake ARRAY column
        tool_calls_json = json.dumps(tool_calls)
        
        insert_query = """
        INSERT INTO APP.EVAL_METRICS (
            LOG_ID, QUESTION, GENERATED_RESPONSE, CONTEXT_USED, 
            RETRIEVAL_MODE, CONFIDENCE, LATENCY_MS, TOOL_CALLS, NUM_ITERATIONS
        ) 
        SELECT %s, %s, %s, %s, %s, %s, %s, PARSE_JSON(%s), %s
        """
        
        cur.execute(insert_query, (
            log_id, question, answer, context_used,
            retrieval_mode, confidence, latency_ms,
            tool_calls_json, num_iterations
        ))
    except Exception as e:
        # Re-raise to let the orchestrator handle the failure gracefully
        raise e
    finally:
        cur.close()
    pass

if __name__ == "__main__":
    print("Running automated evaluation for Vector vs Graph RAG...")
    run_ragas_evaluation(get_conn(input("Enter OTP: ").strip()))
    print("Evaluation Complete.")
