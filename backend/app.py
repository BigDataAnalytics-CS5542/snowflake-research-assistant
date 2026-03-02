from fastapi import FastAPI
from pydantic import BaseModel
from backend.retrieval import get_top_chunks
import os, time
from huggingface_hub import InferenceClient

app = FastAPI(title="Research Assistant API")
@app.get("/")
def read_root():
    return {"message": "Welcome to the Research Assistant API"}

class QueryRequest(BaseModel):
    question: str
    top_k: int = 5

@app.post('/query')
def query(req: QueryRequest):
    start = time.time()
    chunks = get_top_chunks(req.question, top_k=req.top_k, passcode=input("OTP : ").strip())
    context = '  '.join([c[5] for c in chunks])

    model_id = "meta-llama/Llama-3.2-3B-Instruct"
    client = InferenceClient(token=os.getenv('HF_TOKEN'))
    messages = [{"role": "user", "content": f"Answer: {req.question}\nContext: {context}"}]
    
    response = client.chat_completion(
        model=model_id,
        messages=messages,
        max_tokens=500
    )
    
    answer =response.choices[0].message.content

    return {
        'answer': answer,
        'citations': [
            {'chunk_id': c[1], 'paper_id': c[2], 'title': c[3],
             'section': c[4], 'text': c[5][:200], 'score': c[0]}
            for c in chunks
        ],
        'confidence': round(chunks[0][0], 3) if chunks else 0,
        'retrieval_mode': 'vector',
        'latency_ms': int((time.time() - start) * 1000)
    }

@app.get('/health')
def health(): return {'status': 'ok'}
