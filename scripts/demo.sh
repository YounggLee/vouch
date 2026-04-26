#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f .env ]; then
  set -a; . ./.env; set +a
fi
export VOUCH_CACHE_ONLY=1
export VOUCH_CACHE_DIR="$(pwd)/fixtures/responses"
cd fixtures/todo_app
exec ../../.venv/bin/vouch
