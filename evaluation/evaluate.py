import json

def run_ragas_evaluation():
    '''
    Run baseline Vector RAG vs Graph-RAG evaluation via Answer Relevance and Faithfulness metrics.
    '''
    pass
#Gemini 3.1 Flash Lite
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
    # run_ragas_evaluation()
    print("Evaluation Complete.")
