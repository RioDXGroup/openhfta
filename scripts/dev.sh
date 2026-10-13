#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

uvicorn api.main:app --host "${API_HOST:-::}" --port "${API_PORT:-8000}" &
api_pid=$!

cleanup() {
  kill "$api_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "OpenHFTA API: http://localhost:${API_PORT:-8000}"
echo "OpenHFTA web: http://localhost:5174"
npm --prefix web run dev -- --host 0.0.0.0 --port 5174
