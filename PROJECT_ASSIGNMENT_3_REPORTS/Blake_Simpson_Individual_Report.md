# Project 3 — Individual Contribution Report

**Name:** Blake Simpson
**Course:** CS 5542 — Big Data Analytics and Applications
**Project:** Integrated System Report and Final System Enhancement
**Date:** March 30, 2026

---

## Personal Contributions

### 1. Project Scaffolding and Initial Architecture

Set up the initial repository structure, including stub files for the FastAPI backend, Streamlit frontend, Snowflake schema, data ingestion script, retrieval module, and evaluation scaffold. This established the project layout and directory conventions that the team built upon throughout the semester.

**Key commits:** `b2f10eb` (initial commit), `020a381` (project scaffolding)

### 2. Agentic Search Layer (Lab 6)

Implemented the AI agent reasoning loop in the FastAPI backend. The agent uses Gemini 2.5 Flash with two tool declarations (vector database search and knowledge graph search) and runs up to 5 reasoning iterations with autonomous tool selection. Added citation tracking so responses include bracketed source references tied to retrieved chunks, and added the Snowflake vector type migration script.

**Key commits:** `1c3eb32` (agentic search), `d19b0cf` (backend and frontend integration)

### 3. Frontend Chat UI and History

Built the Streamlit chat interface with message history display, citation rendering, and a sidebar showing past queries. Added tool call transparency so each response shows how many tool calls and agent iterations were used.

**Key commits:** `1d0a919` (chat history frontend), `d19b0cf` (frontend integration), `a644713` (tool call display)

### 4. Metrics Dashboard (Lab 9)

Added a "Dashboard" tab to the Streamlit application with real-time system monitoring:

- Summary KPI row (total queries, average latency, average confidence, corpus size)
- Query latency over time (line chart)
- Confidence score distribution (histogram)
- Tool usage breakdown (bar chart)
- Recent queries table (last 20 queries with metadata)
- Snowflake table inventory (row counts across RAW, GRAPH, APP schemas)

Also added the `GET /metrics/history` backend endpoint and enriched the query logging to persist confidence, latency, retrieval mode, tool calls, and iteration count alongside each query.

**Key commits:** `a644713` (metrics dashboard), `9ff4541` (metrics dashboard PR merge)

### 5. Lab 8 Integration — Domain Adaptation

Integrated the team's Lab 8 domain adaptation artifacts into the main project repository so the Project 3 repo reflects all four lab enhancements. The integrated materials include the QLoRA fine-tuning notebook, GEPA prompt optimization notebook, the 50-example instruction dataset, and the evaluation notebook comparing four configurations.

**Key commit:** `862c94e` (lab 8 integration)

---

## Percentage Contribution

**25%** of total project work.

---

## GitHub Contribution Evidence

| Commit | Date | Description |
|--------|------|-------------|
| `b2f10eb` | 2026-02-09 | Initial commit — README, proposal |
| `020a381` | 2026-02-25 | Project scaffolding — backend, frontend, schema, ingestion, evaluation stubs |
| `d19b0cf` | 2026-03-03 | Backend and frontend integration |
| `1c3eb32` | 2026-03-09 | Agentic search — multi-iteration agent, tool definitions, vector migration |
| `1d0a919` | 2026-03-09 | Chat history frontend |
| `a644713` | 2026-03-23 | Metrics dashboard — frontend tabs, backend endpoint, tool call display |
| `9ff4541` | 2026-03-23 | Metrics dashboard PR merge |
| `862c94e` | 2026-03-29 | Lab 8 domain adaptation integration |

---

## Tools Used

- **Claude Code (Anthropic Claude)** — Used for planning implementations, generating code, and reviewing teammate contributions for integration. All AI-generated code was reviewed and tested before committing.

---

## Reflection

My contributions focused on the project foundation, the agentic reasoning layer, and the frontend experience. Setting up the initial scaffolding gave the team a shared structure to work from early on. The agentic search implementation was the most technically involved piece — coordinating the LLM tool-calling loop with Snowflake-backed retrieval across multiple reasoning iterations. The metrics dashboard in Lab 9 added observability to the system, making performance trends visible for the first time. Finally, consolidating the Lab 8 domain adaptation work into the main repository brought all four lab enhancements together in one place for Project 3.
