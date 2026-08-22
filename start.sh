#!/usr/bin/env bash
# start.sh — 由 Guard 拉起业务主进程；末行必须 exec
set -eo pipefail
cd "$(dirname "$0")"

# monorepo：backend/ 子目录。uvicorn 入口是 backend.app:app（从项目根解析）。
# Pod 镜像预置 /opt/venv/bin 在 PATH 最前，直接用 python3。
export APP_PORT="${APP_PORT:-3000}"
exec python3 -m uvicorn backend.app:app --host 0.0.0.0 --port "${APP_PORT}" 2>&1
