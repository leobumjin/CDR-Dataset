#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo 'Usage: bash shells/serve.sh [PORT=8000] [HOST=127.0.0.1]'
  exit 0
fi
PORT="${1:-8000}"
BIND_HOST="${2:-127.0.0.1}"
if [[ $# -gt 2 || ! "$PORT" =~ ^[0-9]+$ || ${#PORT} -gt 5 ]]; then
  echo 'Usage: bash shells/serve.sh [PORT=8000] [HOST=127.0.0.1]' >&2
  exit 1
fi
if (( 10#$PORT < 1 || 10#$PORT > 65535 )); then
  echo 'PORT must be between 1 and 65535.' >&2
  exit 1
fi
PORT="$((10#$PORT))"
printf 'Project page: http://%s:%s/\nv2 page:      http://%s:%s/v2/\nStop: Ctrl+C\n' "$BIND_HOST" "$PORT" "$BIND_HOST" "$PORT"
exec "${PYTHON_BIN:-python3}" -m http.server "$PORT" --bind "$BIND_HOST" --directory "$PROJECT_ROOT/docs"
