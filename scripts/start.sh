#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
run_dir="${TMPDIR:-/tmp}/openhfta"
api_port="${API_PORT:-8000}"
api_host="${API_HOST:-::}"
mkdir -p "$run_dir"
cd "$project_dir"

npm --prefix web run build >"$run_dir/web-build.log" 2>&1
nohup uvicorn api.main:app --host "$api_host" --port "$api_port" >"$run_dir/api.log" 2>&1 &
echo $! >"$run_dir/api.pid"

sleep 2
if ! curl -fsS "http://localhost:${api_port}/health" >/dev/null; then
  echo "Falha ao iniciar a API. Veja $run_dir/api.log e $run_dir/web-build.log" >&2
  exit 1
fi
echo "OpenHFTA: http://localhost:${api_port}"
echo "Logs:     $run_dir/api.log e $run_dir/web-build.log"
