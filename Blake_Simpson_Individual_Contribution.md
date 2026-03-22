# Phase 2 — Individual Contribution

**Name:** Blake Simpson
**Role:** Engineer 3 — Frontend & Evaluation
**Contribution:** 25%

---

## Overview

Responsible for building out the frontend interface with real backend integration, adding MFA authentication flow, implementing citation display, connecting evaluation metrics logging, and optimizing the backend retrieval pipeline.

---

## Components Built

### 1. Frontend Application (`frontend/app.py`)

Replaced the placeholder frontend with a fully functional Streamlit interface:

- **MFA-Aware Authentication** — Sidebar passcode input with "Verify Connection" button that calls the backend `/auth` endpoint
- **Live Query Processing** — Wired up the chat input to call `POST /query` on the backend with question, top_k, and passcode
- **Citation Display** — Renders retrieved sources in an expandable section with confidence score, chunk ID, paper title, section, relevance score (3-decimal precision), and text snippets
- **Error Handling** — Graceful error messaging when the backend is unreachable
- **Session State** — Persists chat messages across Streamlit reruns

### 2. Backend Enhancements (`backend/app.py`)

Added authentication, connection caching, and metrics logging to the FastAPI backend:

- **Connection Caching** — Global `_GLOBAL_CONN` object with `get_active_conn()` to avoid repeated Snowflake authentication on every request
- **`POST /auth` Endpoint** — New authentication endpoint that accepts a passcode and establishes a Snowflake connection
- **Query Endpoint Fixes** — Replaced hardcoded `input()` calls with passcode from request body; fixed return statement (was returning `{result}` set literal instead of `result` dict)
- **Metrics Logging** — Integrated `log_metrics_to_snowflake()` to record question, answer, context, retrieval mode, confidence, and latency to Snowflake after each query
- **History Logging** — Saves query/answer pairs with timestamps to `backend/history.json`

### 3. Retrieval Optimizations (`backend/retrieval.py`)

- **Global Model Loading** — Moved `SentenceTransformer` initialization to module level so the embedding model loads once at boot instead of on every query
- **Graph Search Fix** — Fixed `graph_search()` SQL parameter binding (was passing `normalized_entities` twice, now passes it once)

---

## Commit History

| Commit | Date | Description |
|--------|------|-------------|
| `d19b0cf` | Mar 3, 2026 | Completed my tasks — Frontend integration, auth flow, connection caching, retrieval fixes |

---

## Files Changed

- `frontend/app.py` — Replaced placeholder UI with live backend integration, auth, and citations
- `backend/app.py` — Added `/auth` endpoint, connection caching, metrics logging, fixed `/query` return
- `backend/retrieval.py` — Global model loading, graph search parameter fix
- `backend/history.json` — Query history data
