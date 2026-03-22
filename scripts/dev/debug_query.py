#!/usr/bin/env python3
"""
Dev script: call the FastAPI `query` handler directly (no HTTP server).

Useful for stepping through `/query` logic in a debugger.

Run from repo root:
    python scripts/dev/debug_query.py
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv

# Repo root on sys.path so `import backend` works when run as scripts/dev/debug_query.py
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

load_dotenv(_ROOT / ".env")

from backend.app import QueryRequest, query  # noqa: E402

req = QueryRequest(
    question="What institutions or universities are studying the physics of black holes?",
    top_k=5,
    passcode="DEBUG_SIMULATION",  # may fail Snowflake auth — useful to see where it breaks
)

try:
    result = query(req)
    print("Result:", result)
except Exception:
    traceback.print_exc()
