# RUN.md — How to Run the Snowflake Research Assistant

## Requirements

| Requirement | Version |
|---|---|
| Python | 3.12 |
| Snowflake Account | Required for schema/database |
| Google Gemini API Key | Free — see Step 3 |

---

## Step 1 — Clone the Repository

```bash
git clone <repo-url>
cd snowflake-research-assistant
```

---

## Step 2 — Create and Activate a Virtual Environment

```bash
python3.12 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

---

## Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

> Uses loose `>=` version pins so pip resolves compatible versions automatically.

---

## Step 4 — Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and fill in your credentials:

```
SNOWFLAKE_ACCOUNT=         # e.g. abc123.us-east-1
SNOWFLAKE_USER=            # your Snowflake username
SNOWFLAKE_PASSWORD=        # your Snowflake password
SNOWFLAKE_ROLE=            # e.g. SYSADMIN
SNOWFLAKE_WAREHOUSE=       # e.g. ROHAN_BLAKE_KENNETH_WH
SNOWFLAKE_DATABASE=        # e.g. CS5542_PROJECT_ROHAN_BLAKE_KENNETH
SNOWFLAKE_SCHEMA=          # e.g. RAW
GEMINI_API_KEY=            # Get free key at https://aistudio.google.com/app/apikey
HF_TOKEN=                  # Optional — https://huggingface.co/settings/tokens
```

---

## Step 5 — Create Snowflake Schema

```bash
python scripts/run_sql_file.py sql/01_create_schema.sql
# You will be prompted for your MFA code — press Enter if you don't use MFA
```

---

## Step 6 — Start the Backend

Open a new terminal tab, activate the venv, then run:

```bash
uvicorn backend.app:app --reload --port 3001
```

Verify it is running by visiting: [http://localhost:3001/health](http://localhost:3001/health)

You should see: `{"status": "ok"}`

---

## Step 7 — Start the Frontend

Open another new terminal tab, activate the venv, then run:

```bash
streamlit run frontend/app.py --server.port 3000
```

The UI will open automatically at: [http://localhost:3000](http://localhost:3000)

---

## Step 8 — Authenticate and Query

1. In the sidebar, enter your Snowflake MFA passcode (or leave blank if no MFA)
2. Click **Verify Connection**
3. Type a question in the chat box, e.g. *"How are neural networks used for text summarization?"*
4. The Agentic RAG loop will run up to 5 iterations and return a cited answer

---

## Running the Smoke Test

To verify the backend is up and responding correctly:

```bash
pytest tests/smoke_test.py -v
```

---

## Optional — Populate Snowflake (Ingestion)

To load papers into Snowflake (e.g. 1000 arXiv papers, ~1 hour), run the ingestion pipeline manually.  
**Note:** This is not part of `reproduce.sh` because MFA codes expire quickly (e.g. Duo every 30s); the upload stage needs an interactive prompt.

```bash
python data/ingestion.py              # full run
python data/ingestion.py --resume     # resume from checkpoints
```

You will be prompted for your Snowflake MFA code before the upload stage.  
**Warning:** Ingestion truncates all Snowflake tables before uploading.

---

## Checkpoint System

The ingestion pipeline saves progress after each stage so you can resume:

```
data/checkpoints/
├── papers.parquet           # Stage 1 — loaded papers
├── chunks.parquet           # Stage 2+3 — chunks with embeddings
├── nodes.parquet            # Stage 4 — knowledge graph nodes
├── edges.parquet            # Stage 4 — knowledge graph edges
└── chunk_entity_map.parquet # Stage 4 — chunk to entity links
```

Checkpoints are gitignored — each team member runs ingestion independently.

---

## Troubleshooting

| Error | Fix |
|---|---|
| `Missing env vars` | Make sure `.env` is filled in and you ran `cp .env.example .env` |
| `GEMINI_API_KEY not set` | Add your Gemini key to `.env` |
| `Unknown function VECTOR_COSINE_SIMILARITY` | Upgrade Snowflake or check VECTOR support in your region |
| `Cannot reach backend` | Make sure `uvicorn` is running on port 3001 before starting the frontend |
| `MFA error` | Enter your current Duo token — it expires every 30 seconds |