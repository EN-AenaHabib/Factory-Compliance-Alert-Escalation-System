#!/usr/bin/env bash
# scripts/run_dashboard.sh
# Starts the React dashboard dev server (added in Phase 7).
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/src/dashboard"
npm run dev
