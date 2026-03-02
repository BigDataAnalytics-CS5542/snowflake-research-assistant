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
