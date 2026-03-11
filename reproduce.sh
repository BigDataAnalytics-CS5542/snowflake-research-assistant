#!/usr/bin/env bash
# =============================================================================
# reproduce.sh — Single-command runner for the Snowflake Research Assistant
# CS 5542 — Lab 7: Reproducibility by Design
#
# Usage:
#   bash reproduce.sh   # validate env, start backend, run smoke test, start frontend
# Ingestion is not run here — MFA expires quickly; run python data/ingestion.py manually for upload.
# =============================================================================

set -e  # exit immediately on any error
set -m  # background jobs in own process group so we can kill them cleanly

# ── Colours for output ───────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Colour

log()  { echo -e "${GREEN}[reproduce.sh]${NC} $1"; }
warn() { echo -e "${YELLOW}[reproduce.sh]${NC} $1"; }
fail() { echo -e "${RED}[reproduce.sh] ERROR:${NC} $1"; exit 1; }

# ── Step 0: Check Python version ────────────────────────────
log "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || [ "$PYTHON_MINOR" -lt 12 ]; then
  fail "Python 3.12+ is required. You have Python $PYTHON_VERSION."
fi
log "Python $PYTHON_VERSION ✓"

# ── Step 1: Check .env exists ────────────────────────────────
log "Checking .env file..."
if [ ! -f ".env" ]; then
  fail ".env file not found. Run: cp .env.example .env  and fill in your credentials."
fi

# Check required variables are not empty
source .env
for var in SNOWFLAKE_ACCOUNT SNOWFLAKE_USER SNOWFLAKE_PASSWORD SNOWFLAKE_WAREHOUSE SNOWFLAKE_DATABASE SNOWFLAKE_SCHEMA GEMINI_API_KEY; do
  if [ -z "${!var}" ]; then
    fail "Missing required .env variable: $var"
  fi
done
log ".env variables verified ✓"

# ── Step 2: Set up virtual environment ───────────────────────
log "Setting up virtual environment..."
if [ ! -d "venv" ]; then
  python3 -m venv venv
  log "Created venv ✓"
else
  warn "venv already exists, skipping creation."
fi

source venv/bin/activate
log "Virtual environment activated ✓"

# ── Step 3: Install dependencies ─────────────────────────────
log "Installing dependencies from requirements.txt..."
pip install -q -r requirements.txt
log "Dependencies installed ✓"

# ── Step 4: Create output directories ────────────────────────
log "Creating output directories..."
mkdir -p artifacts logs tests
log "Directories ready: artifacts/ logs/ tests/ ✓"

# ── Step 5: Start backend ─────────────────────────────────────
log "Starting FastAPI backend on port 3001..."
if command -v lsof >/dev/null 2>&1 && lsof -i :3001 -sTCP:LISTEN -t >/dev/null 2>&1; then
  warn "Port 3001 already in use — killing existing process..."
  kill $(lsof -i :3001 -sTCP:LISTEN -t) 2>/dev/null || true
  sleep 1
fi
uvicorn backend.app:app --port 3001 >> logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > logs/backend.pid

# Wait for backend to be ready (model load on first boot can take 60s+)
log "Waiting for backend to be ready..."
for i in {1..45}; do
  if curl -s http://localhost:3001/health | grep -q "ok"; then
    log "Backend is up ✓"
    break
  fi
  if [ $i -eq 45 ]; then
    kill -- -$BACKEND_PID 2>/dev/null || kill $BACKEND_PID 2>/dev/null
    fail "Backend did not start in time. Check logs/backend.log for errors."
  fi
  sleep 2
done

# ── Step 6: Run smoke test ────────────────────────────────────
log "Running smoke test..."
pytest tests/smoke_test.py -v 2>&1 | tee logs/smoke_test.log
log "Smoke test complete. Log saved to logs/smoke_test.log ✓"

# ── Step 7: Save artifacts ────────────────────────────────────
log "Saving run artifacts..."
echo "{
  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
  \"python_version\": \"$PYTHON_VERSION\",
  \"backend_pid\": $BACKEND_PID
}" > artifacts/run_summary.json
log "Run summary saved to artifacts/run_summary.json ✓"

# ── Step 8: Start frontend ────────────────────────────────────
log "Starting Streamlit frontend on port 3000..."
warn "Press Ctrl+C to stop both servers when done."
streamlit run frontend/app.py --server.port 3000 >> logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > logs/frontend.pid

# ── Cleanup on exit ──────────────────────────────────────────
cleanup() {
  log 'Shutting down servers...'
  [ -n "$BACKEND_PID" ]  && kill -- -$BACKEND_PID 2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill -- -$FRONTEND_PID 2>/dev/null || true
  log 'Done.'
}
trap cleanup EXIT

# Keep script alive until Ctrl+C
wait $FRONTEND_PID