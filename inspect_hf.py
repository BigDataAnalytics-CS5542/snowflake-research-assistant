from huggingface_hub import InferenceClient
import os
import json

client = InferenceClient(token=os.getenv('HF_TOKEN'))
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
                "required": ["city"]
            }
        }
    }
]

messages = [{"role": "user", "content": "What is the weather in Paris?"}]

response = client.chat_completion(
    model=model_id,
    messages=messages,
    tools=tools,
    max_tokens=100
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
