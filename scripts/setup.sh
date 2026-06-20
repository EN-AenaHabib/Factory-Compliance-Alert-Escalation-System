#!/usr/bin/env bash
# ============================================================================
# scripts/setup.sh
#
# Single entry point. From a clean checkout, this script:
#   1. Creates a Python virtual environment (CPU-only deps, no CUDA)
#   2. Installs backend dependencies
#   3. Installs the React dashboard dependencies
#   4. Downloads the Kaggle video dataset (if credentials are present)
#   5. Builds the offline policy vector store from the compliance PDF
#   6. Initializes the SQLite audit database schema
#   7. Prints the commands to start the backend and dashboard
#
# Usage:
#   cp .env.example .env   # fill in KAGGLE_USERNAME / KAGGLE_KEY first
#   bash scripts/setup.sh
# ============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "=============================================================="
echo " Factory Compliance & Alert Escalation System — Setup"
echo "=============================================================="

# --- 1. Python virtual environment -----------------------------------------
if [ ! -d ".venv" ]; then
  echo "[1/7] Creating Python virtual environment..."
  python3 -m venv .venv
else
  echo "[1/7] Virtual environment already exists, skipping."
fi
source .venv/bin/activate

# --- 2. Backend dependencies -------------------------------------------------
echo "[2/7] Installing Python dependencies (CPU-only wheels)..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# --- 3. Dashboard dependencies ------------------------------------------------
if [ -d "src/dashboard" ] && [ -f "src/dashboard/package.json" ]; then
  echo "[3/7] Installing React dashboard dependencies..."
  (cd src/dashboard && npm install --silent)
else
  echo "[3/7] Dashboard not yet present (added in Phase 7), skipping."
fi

# --- 4. Load environment variables --------------------------------------------
if [ -f ".env" ]; then
  set -a; source .env; set +a
fi

# --- 5. Dataset download -------------------------------------------------------
echo "[4/7] Checking dataset..."
if [ -n "${KAGGLE_USERNAME:-}" ] && [ -n "${KAGGLE_KEY:-}" ]; then
  python3 scripts/download_dataset.py
else
  echo "      KAGGLE_USERNAME/KAGGLE_KEY not set — skipping auto-download."
  echo "      Place clips manually in data/raw_clips/ or set credentials in .env and re-run."
fi

# --- 6. Build offline policy vector store --------------------------------------
echo "[5/7] Building offline RAG vector store from compliance policy PDF..."
if [ -f "data/policy/compliance_policy.pdf" ]; then
  python3 -m src.policy_agent.build_index
else
  echo "      data/policy/compliance_policy.pdf not found — place the policy PDF there and re-run this step:"
  echo "      python3 -m src.policy_agent.build_index"
fi

# --- 7. Initialize audit database -----------------------------------------------
echo "[6/7] Initializing SQLite audit database schema..."
python3 -m src.audit_agent.init_db

echo "[7/7] Setup complete."
echo "--------------------------------------------------------------"
echo "Start backend:    bash scripts/run_backend.sh"
echo "Start dashboard:  bash scripts/run_dashboard.sh"
echo "Or both via Docker: docker-compose up --build"
echo "--------------------------------------------------------------"
