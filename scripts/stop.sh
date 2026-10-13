#!/usr/bin/env bash
set -euo pipefail

run_dir="${TMPDIR:-/tmp}/openhfta"
for name in api; do
  pid_file="$run_dir/$name.pid"
  if [ -f "$pid_file" ]; then
    pid="$(sed -n '1p' "$pid_file")"
    kill "$pid" 2>/dev/null || true
    rm -f "$pid_file"
  fi
done
echo "Serviços OpenHFTA encerrados."
