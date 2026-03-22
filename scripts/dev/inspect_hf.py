#!/usr/bin/env python3
"""
Optional dev script: Hugging Face Inference API tool-calling smoke test.

Not part of the app runtime and not related to OpenPaper.
Requires HF_TOKEN in the environment.

Run from repo root:
    python scripts/dev/inspect_hf.py
"""
from __future__ import annotations

import os

from huggingface_hub import InferenceClient

client = InferenceClient(token=os.getenv("HF_TOKEN"))
model_id = "meta-llama/Llama-3.2-3B-Instruct"

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    }
]

messages = [{"role": "user", "content": "What is the weather in Paris?"}]

response = client.chat_completion(
    model=model_id,
    messages=messages,
    tools=tools,
    max_tokens=100,
)

message = response.choices[0].message
print("Type of message:", type(message))
print("Message content:", message)

if hasattr(message, "tool_calls") and message.tool_calls:
    print("Type of tool_calls:", type(message.tool_calls))
    print("Tool calls:", message.tool_calls)
    for tc in message.tool_calls:
        print("Type of tc:", type(tc))
        print("tc.function:", tc.function)
        print("tc.function.name:", tc.function.name)
        print("tc.function.arguments:", tc.function.arguments)
