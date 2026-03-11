# OpenPaper Local Setup Guide

This document outlines the steps taken to successfully run the OpenPaper project locally, bypassing several undocumented dependencies and port conflicts.

## 1. Prerequisites
Ensure you have the following installed on your machine:
- **Docker Desktop** (Must be running for database and message brokers)
- **Homebrew** (For installing system packages)
- **Python 3.12** (The `jobs` worker fails with Python 3.14)
- **Node.js & Yarn** (`brew install node yarn`)

## 2. API Keys
To actually test the application, you will need a few API keys. While the `.env` setup below uses dummy values to bypass startup errors, the app will *fail* when attempting to process PDFs or generate answers without real keys.

**Required Keys (Cheapest/Free Tier Available):**
1. **Google Gemini API Key (`GEMINI_API_KEY`, `GOOGLE_API_KEY`)**
   - **Cost**: Free tier available (generous limits for individuals).
   - **How to get**: Visit [Google AI Studio](https://aistudio.google.com/), sign in, and create an API key.
2. **OpenAI API Key (`OPENAI_API_KEY`)**
   - **Cost**: Pay-as-you-go (very cheap for testing, usually fractions of a cent per request). Requires $5 initial credit.
   - **How to get**: Visit [OpenAI Platform](https://platform.openai.com/), sign up, add a payment method, and generate a key.

**Optional Keys (Safe to leave as "dummy" variables):**
- **PostHog** (`POSTHOG_API_KEY`, `POSTHOG_HOST`): Only tracks telemetry/analytics.
- **Stripe** (`STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`): Only needed if you are testing the payment functionality.
- **Exa** (`EXA_API_KEY`): Used for an optional "discover" web search feature.
- **Resend** (`RESEND_API_KEY`): Used for sending emails. *Note: The local email sender prints the verification code to the console output if the key is dummy, avoiding backend crashes!*
- **AWS S3/Cloudflare R2** (`AWS_...`, `S3_...`, `CLOUDFLARE_...`): Used for storing processed PDFs. If using Cloudflare R2, you MUST specify `AWS_ENDPOINT_URL_S3` (e.g. `https://<account-id>.r2.cloudflarestorage.com`) and `AWS_REGION=auto`. You will also need to manually attach a CORS Policy in the Cloudflare Dashboard to allow `localhost:3000` to fetch the PDFs from the browser!

## 3. Infrastructure (PostgreSQL, Redis, RabbitMQ)
The OpenPaper project requires PostgreSQL, Redis, and RabbitMQ. 
The easiest way to orchestrate these is with `docker-compose`.

1. Create a `docker-compose.yml` in the root of the `openpaper` directory:
```yaml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: annotated-paper
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"

volumes:
  postgres_data:
```
2. Run `docker compose up -d` to start the containers in the background.

## 4. Server Setup (`openpaper/server`)
The server uses FastAPI and requires several environment variables to start, even if you are not using all the features.

1. **Install `pg_config`**: The PostgreSQL Python driver requires this to build.
   ```bash
   brew install postgresql
   # Add it to your PATH
   export PATH="/opt/homebrew/opt/postgresql@18/bin:$HOME/.local/bin:$PATH"
   ```
2. **Install `uv`**: The project uses `uv` for dependency management.
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   export PATH="$HOME/.local/bin:$PATH"
   ```
3. **Set Environment Variables**: Create `openpaper/server/.env` with the following:
   ```ini
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/annotated-paper
   GEMINI_API_KEY=your-gemini-key
   OPENAI_API_KEY=dummy-openai-key
   POSTHOG_API_KEY=dummy-posthog-key
   POSTHOG_HOST=dummy-host
   STRIPE_API_KEY=dummy-stripe-key
   STRIPE_WEBHOOK_SECRET=dummy-webhook
   EXA_API_KEY=dummy-exa-key
   RESEND_API_KEY=dummy-resend-key
   CELERY_BROKER_URL=amqp://guest:guest@localhost:5672/
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   AWS_ACCESS_KEY_ID=your-key
   AWS_SECRET_ACCESS_KEY=your-secret
   AWS_REGION=auto
   AWS_ENDPOINT_URL_S3=https://your-r2-url.r2.cloudflarestorage.com
   S3_BUCKET_NAME=openpaper
   CLOUDFLARE_BUCKET_NAME=openpaper
   ```
   *Note: Dummy values are required to bypass `ValueError` thrown during server startup, but Celery/S3 need exact configurations to process PDFs.*
4. **Install Missing Dependencies & Run Migrations**:
   The `server` is missing the `redis` python package to communicate with the Celery backend, preventing tasks from queuing.
   ```bash
   cd server
   uv add redis
   uv sync --python 3.12
   uv run app/scripts/run_migrations.py
   ```
5. **Start the Server**:
   ```bash
   uv run python3 -m app.main
   ```
   The server will run on `http://localhost:8000`.

## 5. Jobs Worker Setup (`openpaper/jobs`)
The Jobs service handles async tasks via Celery.

1. **Fix `start.sh`**: Remove lines 6-8 in `jobs/scripts/start.sh` to prevent it from trying to start new Docker containers that conflict with your `docker-compose` setup.
2. **Set Environment Variables**: Create `openpaper/jobs/.env`:
   ```ini
   AWS_ACCESS_KEY_ID=dummy_key
   AWS_SECRET_ACCESS_KEY=dummy_secret
   AWS_REGION=auto
   AWS_ENDPOINT_URL_S3=https://your-r2-url.r2.cloudflarestorage.com
   S3_BUCKET_NAME=openpaper
   CLOUDFLARE_BUCKET_NAME=openpaper
   CELERY_BROKER_URL=amqp://guest:guest@localhost:5672/
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   LLM_API_KEY=dummy-llm-key
   GOOGLE_API_KEY=dummy-google-key
   POSTHOG_API_KEY=dummy-posthog-key
   POSTHOG_HOST=dummy-host
   OPENAI_API_KEY=dummy-openai
   ```
3. **Configure the Queues**: Ensure `jobs/scripts/start_worker.sh` has the `-Q` flag to pick up PDF tasks, otherwise jobs will silently hang:
   ```bash
   python -m celery --app src.celery_app worker \
       --loglevel=info \
       --concurrency=2 \
       -Q celery,pdf_processing \ # <-- This is required!
   ```
4. **Start the Worker**:
   ```bash
   cd jobs
   # Must use Python 3.12, onnxruntime fails on 3.14
   uv sync --python 3.12
   # Kill any zombie processes on port 8001: lsof -ti:8001 | xargs kill -9
   uv run start
   ```

## 6. Client Setup (`openpaper/client`)
The Next.js frontend connects to the backend server.

1. **Install Dependencies & Start**:
   ```bash
   cd client
   yarn install
   yarn dev
   ```
   The client will run on `http://localhost:3000`.

---
## Summary of Your Action Items
To run the full stack effortlessly next time:
1. Ensure **Docker Desktop** is running.
2. In terminal 1 (root): `docker compose up -d`
3. In terminal 2 (`openpaper/server`): `export PATH="/opt/homebrew/opt/postgresql@18/bin:$HOME/.local/bin:$PATH" && uv run python3 -m app.main`
4. In terminal 3 (`openpaper/jobs`): `uv run start` (make sure port 8001 is clear).
5. In terminal 4 (`openpaper/client`): `yarn dev`
