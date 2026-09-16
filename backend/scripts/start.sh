#!/bin/bash
set -e

echo "[FlyCast] Starting backend bootstrap and service..."

# 1. Ensure connectome is acquired or built into /data/brain
echo "[FlyCast] Running connectome bootstrap..."
python -m app.brain.bootstrap

# 2. Start Uvicorn ASGI server
PORT="${PORT:-8000}"
echo "[FlyCast] Launching Uvicorn on port $PORT..."
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 1
