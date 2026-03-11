## CS 5542 – Phase 2 Individual Contributions

| Member | Role | Contribution % |
|---|---|---|
| Rohan Ashraf Hashmi | Engineer 1 — Data & Ingestion | 40% |
| Kenneth Kakie | Engineer 2 — Backend & Retrieval | 35% |
| Blake Simpson | Engineer 3 — Frontend & Evaluation | 25% |

**Total: 100%**

---

## Rohan Ashraf Hashmi — 40%

**Data Infrastructure & Ingestion Pipeline**

- Designed and implemented complete Snowflake schema (`sql/01_create_schema.sql`)
  - RAW schema: PAPERS, CHUNKS, FIGURES tables
  - GRAPH schema: KNOWLEDGE_NODES, KNOWLEDGE_EDGES, CHUNK_ENTITY_MAP tables
  - APP schema: CHUNKS_V view, EVAL_METRICS table
- Built full 6-stage ingestion pipeline (`data/ingestion.py`):
  - Stage 1: HuggingFace dataset loading with streaming + text cleaning
  - Stage 2: Section-aware chunking (200 words, 30 overlap)
  - Stage 3: Embedding generation (all-mpnet-base-v2, 768-dim)
  - Stage 4: Knowledge graph extraction (scispaCy NER, CO_OCCURS edges)
  - Stage 5: Snowflake upload with auto-truncate and MFA handling
  - Stage 6: Automated verification with row count validation
- Built `data/config.py` — centralized configuration (no magic numbers)
- Built `scripts/sf_connect.py` — MFA-aware Snowflake connection helper
- Built `scripts/run_sql_file.py` — SQL file executor with env-based context
- Populated Snowflake with 1000 arXiv papers corpus

**Commit evidence:** All files in `data/`, `sql/`, `scripts/` directories, snowflake tables

---

## Kenneth Kakie — 30%

**Backend API & Retrieval Engine**

- Implemented `backend/retrieval.py`:
  - Vector search using cosine similarity on stored embeddings
  - Graph-enhanced retrieval via CHUNK_ENTITY_MAP traversal
  - Hybrid retrieval combining vector + graph signals
- Implemented `backend/app.py` (FastAPI, port 3001):
  - `POST /query` — main retrieval endpoint
  - `GET /papers` — corpus browser
  - `GET /history` — query history
  - `GET /health` — health check
- Standardized API response schema (answer, citations, confidence, latency)

**Commit evidence:** All files in `backend/` directory

---

## Blake Simpson — 30%

**Frontend Interface & Evaluation**

- Implemented `frontend/app.py` (Streamlit, port 3000):
  - Query interface with retrieval mode selector (vector/graph/hybrid)
  - Citation display with paper title, section, text snippet, confidence score
  - Corpus browser sidebar
  - Query history panel
- Implemented `evaluation/evaluate.py`:
  - RAGAS metrics (faithfulness, answer relevance)
  - Precision@K, Recall@K
  - All queries logged to APP.EVAL_METRICS in Snowflake
- Created test query suite (5 queries including 1 unanswerable)

**Commit evidence:** All files in `frontend/`, `evaluation/` directories

---

*Contributions verified by commit history in GitHub repository.*

---
---

## CS 5542 – Lab 7 Individual Contributions (Reproducibility by Design)

| Member | Role | Contribution % |
|---|---|---|
| Rohan Ashraf Hashmi | Teammate 1 — Infrastructure & Environment Setup | 33% |
| Blake Simpson | Teammate 2 — Related Work & System Enhancement | 34% |
| Kenneth Kakie | Teammate 3 — Determinism & Documentation | 33% |

**Total: 100%**

---

## Rohan Ashraf Hashmi — 33%

**Infrastructure & Reproducibility**

- Fixed `.env.example` — added missing `GEMINI_API_KEY` introduced by Teammate 2's Gemini upgrade; without this fix the `/query` endpoint crashes silently for anyone cloning the repo
- Wrote `RUN.md` — complete step-by-step setup guide covering Python 3.12 requirement, Snowflake setup, MFA handling, and a troubleshooting table
- Built `reproduce.sh` — single-command runner that:
  - Validates Python 3.12+ and all required `.env` variables before doing anything
  - Creates `venv`, installs dependencies, creates `artifacts/` `logs/` `tests/` directories
  - Starts backend with health check polling loop before proceeding
  - Runs smoke test and saves log to `logs/smoke_test.log`
  - Saves `artifacts/run_summary.json` with timestamp and run metadata
  - Starts frontend and cleanly kills both servers on exit via `trap`
  - Does not run ingestion — run `python data/ingestion.py` manually to populate Snowflake (due to MFA expiring quickly; upload needs interactive prompt)
- Wrote `tests/smoke_test.py` — 4 pytest tests for `/health`, `/`, `/history` endpoints that run without a live Snowflake connection

**Commit evidence:** `.env.example`, `requirements.txt`, `RUN.md`, `reproduce.sh`, `tests/smoke_test.py`

---

## Blake Simpson — 34%

**Related Work Reproduction & System Enhancement**

- Reproduced OpenPaper (NeurIPS-adjacent tool) locally:
  - Orchestrated full infrastructure via `docker-compose` (PostgreSQL, Redis, RabbitMQ)
  - Resolved silent hang in Celery worker by fixing queue routing (`-Q pdf_processing`)
  - Fixed Cloudflare R2 endpoint configuration
  - Successfully uploaded and processed PDFs through the full stack
- Implemented Agentic RAG loop in `backend/app.py` inspired by OpenPaper's `gather_evidence` pattern:
  - Replaced single-shot retrieval with an autonomous `while` loop (up to 5 iterations)
  - Switched LLM from Llama-3.2-3B to Gemini 2.5 Flash (`google-genai`)
  - Defined two tool schemas: `search_vector_database` and `search_knowledge_graph`
  - LLM autonomously decides which tool to call and when to stop
  - Responses include bracketed citations (`[1]`, `[2]`) tied to retrieved chunks
- Migrated Snowflake embeddings from VARCHAR to native `VECTOR(FLOAT, 768)`:
  - `get_top_chunks()` now uses `VECTOR_COSINE_SIMILARITY()` server-side
  - Eliminates fetching all 35,000 rows to Python for dot product computation
  - Added `_migrate_embeddings_to_vector()` post-upload helper in `ingestion.py`
  - Created `sql/02_migrate_to_vector_type.sql` for existing databases
- Added `/auth` endpoint for Snowflake MFA passcode handling
- Added `save_to_history()` — persists every Q&A to `backend/history.json`
- Documented all work in `RELATED_WORK_REPRO.md` and `OPENPAPER_LOCAL_SETUP.md`

**Commit evidence:** `backend/app.py`, `backend/retrieval.py`, `sql/02_migrate_to_vector_type.sql`, `data/ingestion.py`, `RELATED_WORK_REPRO.md`, `OPENPAPER_LOCAL_SETUP.md`

---

## Kenneth Kakie — 33%

**Determinism & Documentation**

- Fixed random seeds across ingestion and embedding stages for deterministic output
- Verified all data paths and removed hardcoded directory references
- Set up and verified `artifacts/`, `logs/`, `tests/` directory structure
- Ran full integration smoke test to confirm end-to-end pipeline works
- Compiled `REPRO_AUDIT.md` — complete reproducibility audit checklist
- Wrote two-page team reproducibility report (submitted separately)

**Commit evidence:** `REPRO_AUDIT.md`, seed fixes in `data/ingestion.py`, team report

---

*Contributions verified by commit history in GitHub repository.*