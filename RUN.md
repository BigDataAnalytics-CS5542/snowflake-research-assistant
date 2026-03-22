# Runbook — Snowflake Research Assistant

Operational steps to install, configure, and run the application locally or in a split deployment (API + Streamlit).

---

## Prerequisites

| Item | Notes |
|------|--------|
| Python | 3.12 |
| Snowflake | Account with database/warehouse access; VECTOR support for embeddings |
| Google Gemini API | API key ([Google AI Studio](https://aistudio.google.com/app/apikey)) for `/query` |

---

## 1. Clone and environment

```bash
git clone <repository-url>
cd snowflake-research-assistant
python3.12 -m venv venv
source venv/bin/activate   # Linux / macOS
# venv\Scripts\activate   # Windows
```

---

## 2. Dependencies

```bash
pip install -r requirements.txt
```

Version constraints use `>=`; resolve conflicts in your environment as needed.

---

## 3. Configuration

```bash
cp .env.example .env
```

Edit `.env`. Required variables:

| Variable | Purpose |
|----------|---------|
| `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`, `SNOWFLAKE_SCHEMA` | Snowflake session context |
| `GEMINI_API_KEY` | LLM for agentic RAG |
| `BACKEND_URL` | FastAPI base URL used by Streamlit (no trailing slash); must match the API process |

Authentication (choose one path):

- **Key pair:** set `SNOWFLAKE_PRIVATE_KEY` (PEM; use `\n` for newlines in a single-line env value). Leave `SNOWFLAKE_PASSWORD` empty if unused.
- **Password:** set `SNOWFLAKE_PASSWORD`. If the account enforces MFA, see **Snowflake MFA** below.

Optional: `SNOWFLAKE_ROLE`, `HF_TOKEN` (Hugging Face, ingestion).

---

## 4. Snowflake schema

```bash
python scripts/run_sql_file.py sql/01_create_schema.sql
```

You may be prompted for an MFA passcode; press Enter if not applicable.

For legacy databases still on VARCHAR embeddings, apply `sql/02_migrate_to_vector_type.sql` per project documentation.

---

## 5. Snowflake MFA (password-based accounts)

When the backend uses **username, password, and MFA** (e.g. Duo):

- After **each API process start** (including restarts with `--reload`), establish a session **once** with a current passcode:
  - **HTTP:** `POST /auth` with JSON body `{"passcode":"<code>"}`.
  - **Streamlit:** use the sidebar expander **Snowflake MFA (password + Duo)** when it is visible.

Example:

```bash
curl -s -X POST "http://localhost:3001/auth" \
  -H "Content-Type: application/json" \
  -d '{"passcode":"<mfa-code>"}'
```

**Streamlit sidebar:** The MFA expander is **not shown** when `SNOWFLAKE_PRIVATE_KEY` is non-empty in the Streamlit process environment. For deployments where only the API has the private key, the expander may still appear on the frontend; it can be ignored if the API authenticates with key pair.

---

## 6. API (FastAPI)

```bash
uvicorn backend.app:app --reload --port 3001
```

| Endpoint | Use |
|----------|-----|
| `GET /health` | Process liveness |
| `GET /health/snowflake` | Snowflake connectivity and `INFORMATION_SCHEMA` row counts; optional query `?passcode=` if MFA applies |

---

## 7. Frontend (Streamlit)

```bash
streamlit run frontend/app.py --server.port 3000
```

Ensure `BACKEND_URL` in `.env` points at the running API. Load the URL shown in the terminal (default `http://localhost:3000`).

---

## 8. Smoke tests

Requires the API running.

```bash
pytest tests/smoke_test.py -v
```

---

## 9. Data ingestion (optional)

Loads corpus into Snowflake. Not invoked by `reproduce.sh`; run manually when you need a fresh or resumed load. Upload stage prompts for MFA when applicable.

```bash
python data/ingestion.py
python data/ingestion.py --resume
```

**Behavior:** Truncates target Snowflake tables before upload. Plan accordingly.

Checkpoints under `data/checkpoints/` (gitignored) support `--resume`.

---

## Troubleshooting

| Symptom | Action |
|---------|--------|
| Missing configuration errors | Confirm `.env` exists and required keys are set |
| Frontend: `BACKEND_URL is required` | Set `BACKEND_URL` to the API base URL |
| `VECTOR_COSINE_SIMILARITY` / VECTOR errors | Confirm Snowflake edition/region supports VECTOR; run migration SQL if needed |
| Frontend cannot reach API | Confirm API is listening and host/port match `BACKEND_URL` |
| Gemini `429` / quota | Reduce request rate; agentic flow issues multiple model calls per question |
| Snowflake MFA failures | Use a new passcode; re-`POST /auth` after API restart |

---

*Further detail: root `README.md`, `reproducibility/README.md`.*
