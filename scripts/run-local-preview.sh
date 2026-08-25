#!/bin/zsh
set -eu

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_DIR="$PROJECT_DIR/.local-runtime"
PG_ISREADY_BIN="${PG_ISREADY_BIN:-$(command -v pg_isready || true)}"
PG_CTL_BIN="${PG_CTL_BIN:-$(command -v pg_ctl || true)}"

if [[ -z "$PG_ISREADY_BIN" || -z "$PG_CTL_BIN" ]]; then
  echo "PostgreSQL tools not found. Add pg_isready and pg_ctl to PATH, or set PG_ISREADY_BIN and PG_CTL_BIN." >&2
  exit 1
fi

cd "$PROJECT_DIR"
export LANG="C.UTF-8"
export LC_ALL="C.UTF-8"

if ! "$PG_ISREADY_BIN" -h 127.0.0.1 -p 5432 -q; then
  "$PG_CTL_BIN" -D "$RUNTIME_DIR/postgres" -l "$RUNTIME_DIR/postgres.log" start
fi

set -a
source "${DEEPSEEK_ENV_FILE:-$PROJECT_DIR/.env.deepseek.local}"
set +a
export APP_AUTH_MODE=public
export DATABASE_URL="${DATABASE_URL:-postgresql://postgres@127.0.0.1:5432/cowork_dev}"

exec "${PYTHON_BIN:-$RUNTIME_DIR/venv/bin/python}" -m uvicorn backend.app:app --host 127.0.0.1 --port "${PORT:-4184}"
