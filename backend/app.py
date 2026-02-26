from fastapi import FastAPI

app = FastAPI(title="Research Assistant API")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Research Assistant API"}
