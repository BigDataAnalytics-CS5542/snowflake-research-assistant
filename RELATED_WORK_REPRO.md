# Related Work Reproduction: OpenPaper

## Phase 1: Repository Understanding
**Repository:** [OpenPaper](https://github.com/sabaimran/openpaper)
**Summary:** OpenPaper is an AI-powered copilot for reading and annotating research papers. It provides a web interface (Next.js client) and a Python backend (FastAPI server) that allows users to upload PDFs, run an agentic evidence-gathering loop over their corpus, and chat with the papers contextually.
**Structure:**
- `client/`: Next.js frontend application.
- `server/`: FastAPI backend managing PostgreSQL database, LLM tools, and core logic.
- `jobs/`: Celery worker service for asynchronous tasks (e.g., PDF processing).
- **Assumptions:** It assumes an active PostgreSQL database, and for async jobs, RabbitMQ and Redis. It's not fully optimized for self-hosting according to the authors, but provides `DEVELOPMENT.md` for local setup.

## Phase 3: Credential Detection
We scanned the OpenPaper codebase for required API keys, cloud services, and offline dependencies:
- **Cloud LLM API Keys:** Requires a `GEMINI_API_KEY` (Google AI Studio) as seen in `.env.example` and `README.md`. It also optionally uses OpenAI, Cerebras, and Groq depending on the provider used.
- **External Services:** 
    - Database: Requires PostgreSQL (`DATABASE_URL`).
    - Cache/Broker: Requires Redis and RabbitMQ for the Celery `jobs` service.
    - Search: Uses `exa-py` for external knowledge search.
    - Email/Payment: Integrates with Resend (email) and Stripe (payments) as seen in `pyproject.toml`.
- **Offline Capabilities:** Local models are not strictly enforced out of the box (requires cloud APIs), but the vector storage and database operations are run locally via SQLAlchemy/Postgres.

## Phase 8: Paper-to-Code Alignment
*(Note: OpenPaper is built as a tooling application rather than an academic paper release. Its core "novelty" is the Agentic RAG multi-paper evidence gathering loop implementation, which we analyzed below.)*

## Integration Plan
**Improvement Identified:** *Agentic Evidence Gathering / Multi-Tool RAG*
**Current State in `snowflake-research-assistant`:** Our `/query` endpoint currently performs a single-shot vector similarity search (`get_top_chunks`) and blindly feeds the top-K chunks into our Llama-3.2-3B model.
**Target Improvement:** We will implement an Agentic RAG approach inspired by OpenPaper's `gather_evidence` loop. Instead of just a single vector retrieval, our Llama model will have the ability to explicitly use tools (e.g., our existing `graph_search` and `get_top_chunks`) iteratively before streaming a final, citation-backed response. This leverages the rich graph data we have but currently aren't exploiting in the `/query` endpoint.

## Phase 9: Reproduction Completion & Results
We have successfully completed the reproduction of OpenPaper's core agentic loop logic and integrated it into our own `snowflake-research-assistant` project.

### 1. Local Environment Reproduction
- **Containerization**: Orchestrated the full OpenPaper infrastructure (PostgreSQL, Redis, RabbitMQ) via `docker-compose`.
- **Worker Configuration**: Resolved a critical "silent hang" issue in the OpenPaper `jobs` service by correcting Celery queue routing (`-Q pdf_processing`) and fixing Cloudflare R2 endpoint configurations.
- **Frontend/Backend Sync**: Successfully uploaded and processed PDFs through the full stack locally.

### 2. Implementation of Agentic RAG Loop
- **Autonomous Reasoning**: Overhauled our `/query` endpoint in `snowflake-research-assistant` to use a `while` loop (up to 5 iterations) instead of single-shot retrieval.
- **Tool Calling**: Integrated HuggingFace Tool Calling schemas for `search_vector_database` and `search_knowledge_graph`, allowing the LLM to choose its own retrieval strategy.
- **Multi-Hop Evidence Gathering**: The system now iteratively gathers evidence from both vector similarity searches and Neo4j-style knowledge graph relationship searches before synthesizing an answer.

### 3. Verification & Challenges Overcome
- **Snowflake MFA Integration**: Implemented a secure passcode passthrough mechanism and verified the connection against the Snowflake EDU environment.
- **Citation Fidelity**: Enforced strict system prompts (reproduced from OpenPaper's strategies) to ensure the model only answers based on retrieved context and provides bracketed citations (e.g., `[1]`, `[2]`).
- **Debugging**: Resolved environment variable loading issues and non-serializable object errors in the LLM response handling.

**Result:** Our project now functions as an autonomous research agent, capable of exploring relationships and text simultaneously—a significant upgrade over the original baseline RAG implementation.
