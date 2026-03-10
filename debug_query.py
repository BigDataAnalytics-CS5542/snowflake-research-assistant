from backend.app import query, QueryRequest
import os
from dotenv import load_dotenv

# Load env in case it's needed
load_dotenv()

# Simulate a request
req = QueryRequest(
    question="What institutions or universities are studying the physics of black holes?",
    top_k=5,
    passcode="DEBUG_SIMULATION" # This will likely fail Snowflake auth, but let's see where it crashes
)

try:
    result = query(req)
    print("Result:", result)
except Exception as e:
    import traceback
    traceback.print_exc()
