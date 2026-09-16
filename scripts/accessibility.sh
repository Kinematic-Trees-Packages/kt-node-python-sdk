#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

node scripts/static_server.mjs "$repo_root/build/docs/v0.2" >/tmp/kt-docs-http.log 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT

for _ in $(seq 1 50); do
  if curl -fsS http://127.0.0.1:8000/ >/dev/null; then
    break
  fi
  sleep 0.1
done

node scripts/accessibility.mjs
