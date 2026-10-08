#!/usr/bin/env bash
# Starts only the two new services. Never stops or modifies Streamlit.
set -euo pipefail
task_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$task_root"
if [[ "${1:-}" != "" && "${1:-}" != "--dev" ]]; then
  echo "Usage: bash scripts/start-nextjs.sh [--dev]" >&2
  exit 2
fi
if [[ ! -x .venv/bin/python ]]; then
  echo "Install Python dependencies first: .bootstrap/bin/uv sync --frozen" >&2
  exit 1
fi
if ! command -v node >/dev/null || ! command -v npm >/dev/null; then
  echo "Node.js 20.9 or newer and npm are required." >&2
  exit 1
fi
.venv/bin/python -c 'import socket
for port in (3000, 8000):
    with socket.socket() as connection:
        if connection.connect_ex(("127.0.0.1", port)) == 0:
            raise SystemExit(f"Port {port} is already in use. Existing services were left untouched.")'
if [[ ! -d frontend/node_modules ]]; then
  npm --prefix frontend ci
fi
if [[ "${1:-}" != "--dev" ]]; then
  npm --prefix frontend run build
fi
export QCOMPASS_ROOT="$task_root"
export QCOMPASS_API_URL="http://127.0.0.1:8000"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 NUMEXPR_NUM_THREADS=4
api_pid=""
web_pid=""
cleanup() {
  trap - EXIT INT TERM
  [[ -z "$web_pid" ]] || kill "$web_pid" 2>/dev/null || true
  [[ -z "$api_pid" ]] || kill "$api_pid" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
.venv/bin/python -m uvicorn qcompass.api.app:app --host 127.0.0.1 --port 8000 &
api_pid=$!
if [[ "${1:-}" == "--dev" ]]; then
  (cd frontend && exec node node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port 3000) &
else
  (cd frontend && exec node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3000) &
fi
web_pid=$!
echo "Next.js: http://127.0.0.1:3000 — Streamlit remains separate at http://127.0.0.1:8501"
echo "Ctrl+C stops only these two web services. A queued simulation worker may finish independently."
while kill -0 "$api_pid" 2>/dev/null && kill -0 "$web_pid" 2>/dev/null; do
  sleep 1
done
echo "One web service stopped; closing the other service started by this script." >&2
exit 1
