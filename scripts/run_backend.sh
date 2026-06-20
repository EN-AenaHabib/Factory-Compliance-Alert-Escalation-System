#!/usr/bin/env bash
# scripts/run_backend.sh
# Starts the FastAPI backend (detection pipeline orchestration + API + SSE stream).
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
source .venv/bin/activate 2>/dev/null || true
uvicorn src.backend.main:app --host "${BACKEND_HOST:-0.0.0.0}" --port "${BACKEND_PORT:-8000}" --reload
