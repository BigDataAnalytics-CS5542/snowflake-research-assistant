# Lab 9 Individual Contribution Report

**Name:** Blake Simpson
**Course:** CS 5542 — Big Data Analytics and Applications
**Lab:** Lab 9 — Application and Deployment Enhancement
**Date:** March 23, 2026

---

## Focus Area

**Area B — System Evaluation and Monitoring:** Built the metrics dashboard tab in the Streamlit frontend, providing real-time visibility into system performance and query behavior.

---

## Personal Contributions

### 1. Metrics Dashboard (Frontend)

Added a new "Dashboard" tab to the Streamlit application alongside the existing "Chat" tab. The dashboard pulls live data from the backend `/metrics` and `/metrics/history` endpoints and displays:

- **Summary KPI row** — Total Queries, Average Latency (ms), Average Confidence Score, and Corpus Size (papers), using `st.metric()` widgets
- **Query Latency Over Time** — Line chart showing how response latency varies across queries
- **Confidence Score Distribution** — Bar chart histogram (5 bins from 0–1.0) showing the spread of retrieval confidence
- **Tool Usage Breakdown** — Bar chart showing how frequently each agent tool (vector search, knowledge graph search) is called
- **Recent Queries Table** — Sortable dataframe of the last 20 queries with timestamp, question, confidence, latency, and iteration count
- **Snowflake Table Inventory** — Displays row counts for all tables across the RAW, GRAPH, and APP schemas

### 2. Chat UI Improvements

- Added tool call transparency to chat responses — each assistant message now shows how many tool calls were made and across how many agent iterations (e.g., "Agent used 3 tool calls across 2 iterations")
- Moved citations display to persist via session state so they survive Streamlit reruns
- Refactored the sidebar chat history to use a cached data fetcher, eliminating duplicate HTTP calls

### 3. Backend Enhancements

- Enriched `save_to_history()` to persist `confidence`, `latency_ms`, `retrieval_mode`, `tool_calls`, and `num_iterations` alongside each query entry — previously only timestamp, query, answer, and chunks were saved
- Added `GET /metrics/history` endpoint returning per-query rows from `APP.EVAL_METRICS` for the dashboard charts (Kenneth's `/metrics` endpoint only returned aggregates)

### 4. Dependency Updates

- Added `pandas>=2.0.0` to `frontend/requirements.txt` for dashboard data processing

---

## Key Commits

| Commit | Description |
|--------|-------------|
| `a644713` | Added metric dashboard — frontend tabs, dashboard rendering, cached fetchers, tool call display in chat |
| `1b335ff` | Merge of Kenneth's backend monitoring branch into metrics-dashboard branch |

---

## Tools Used

- **Claude Code (Anthropic Claude)** — Used for planning the dashboard architecture, generating the implementation code, and reviewing Kenneth's backend changes for integration points. All code was reviewed and tested before committing.

---

## How This Extends the Phase-2 Prototype

The Phase-2 system had no visibility into its own performance. Users could ask questions and get answers, but there was no way to understand how the system was performing over time. The metrics dashboard adds observability: query latency trends, confidence distributions, tool usage patterns, and a complete query log — making the system ready for the Research-A-Thon demonstration where we can show both the AI capabilities and the system's operational health.
