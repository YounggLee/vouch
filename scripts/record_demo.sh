#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

if [ -f .env ]; then
  set -a; . ./.env; set +a
fi
export VOUCH_CACHE_ONLY=1
export VOUCH_CACHE_DIR="$ROOT/fixtures/responses"

cd fixtures/todo_app
git reset -q --hard HEAD
git clean -fdq
git apply "$ROOT/fixtures/auth_change.diff"
git add -A
cd "$ROOT"

exec "$ROOT/.venv/bin/python" "$ROOT/scripts/capture_demo.py"
