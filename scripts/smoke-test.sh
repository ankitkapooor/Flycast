#!/usr/bin/env bash
set -eo pipefail

echo "============================================================"
echo "          FLYCAST END-TO-END SMOKE TEST                     "
echo "============================================================"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PORT=8976
TEMP_DATA_DIR=$(mktemp -d /tmp/flycast_smoke_XXXXXX)
PID_FILE="$TEMP_DATA_DIR/backend.pid"

cleanup() {
    echo ""
    echo "[Smoke Test] Cleaning up..."
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "[Smoke Test] Stopping backend server (PID $PID)..."
            kill "$PID" || true
        fi
    fi
    rm -rf "$TEMP_DATA_DIR"
    echo "[Smoke Test] Finished cleanup."
}
trap cleanup EXIT

echo "[Smoke Test] 1. Initializing backend with fixture reservoir on port $PORT..."
export PYTHONPATH="$PROJECT_ROOT/backend"
export DATA_DIR="$TEMP_DATA_DIR"
export USE_FIXTURE_BRAIN="true"
export LOG_LEVEL="WARNING"

echo "[Smoke Test] Bootstrapping fixture connectome..."
"$PROJECT_ROOT/backend/.venv/bin/python" -m app.brain.bootstrap

echo "[Smoke Test] Launching server on port $PORT..."
"$PROJECT_ROOT/backend/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port $PORT > "$TEMP_DATA_DIR/server.log" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

echo "[Smoke Test] Waiting for backend server to be healthy..."
READY=0
for i in {1..60}; do
    HEALTH_RESP=$(curl -s "http://127.0.0.1:$PORT/health" || true)
    if echo "$HEALTH_RESP" | grep -q '"brain_loaded":true'; then
        READY=1
        break
    fi
    sleep 0.5
done

if [ "$READY" -ne 1 ]; then
    echo "ERROR: Backend failed to become healthy within 30 seconds."
    echo "Last response from /health: $HEALTH_RESP"
    cat "$TEMP_DATA_DIR/server.log"
    exit 1
fi
echo "[Smoke Test] ✓ Backend healthy."

echo "[Smoke Test] 2. Submitting synthetic Lorenz experiment..."
SUBMIT_RESP=$(curl -s -X POST "http://127.0.0.1:$PORT/api/v1/experiments" \
    -F "demo_id=lorenz" \
    -F "forecast_horizon=5" \
    -F "run_control=true")

EXP_ID=$(echo "$SUBMIT_RESP" | grep -o '"id":"[^"]*' | cut -d'"' -f4)
if [ -z "$EXP_ID" ]; then
    echo "ERROR: Could not acquire experiment ID. Response was:"
    echo "$SUBMIT_RESP"
    exit 1
fi
echo "[Smoke Test] ✓ Experiment enqueued with ID: $EXP_ID"

echo "[Smoke Test] 3. Polling for experiment completion..."
COMPLETED=0
for i in {1..40}; do
    STATUS_JSON=$(curl -s "http://127.0.0.1:$PORT/api/v1/experiments/$EXP_ID")
    if echo "$STATUS_JSON" | grep -q '"status":"complete"'; then
        COMPLETED=1
        break
    elif echo "$STATUS_JSON" | grep -q '"status":"failed"'; then
        echo "ERROR: Experiment reported failure:"
        echo "$STATUS_JSON"
        exit 1
    fi
    sleep 0.5
done

if [ "$COMPLETED" -ne 1 ]; then
    echo "ERROR: Experiment did not complete in time."
    exit 1
fi
echo "[Smoke Test] ✓ Experiment completed successfully."

echo "[Smoke Test] 4. Verifying results and evaluation metrics..."
RESULTS_JSON=$(curl -s "http://127.0.0.1:$PORT/api/v1/experiments/$EXP_ID/results")

if ! echo "$RESULTS_JSON" | grep -q '"rmse"'; then
    echo "ERROR: Missing RMSE metric in results."
    exit 1
fi

WINNER=$(echo "$RESULTS_JSON" | grep -o '"winner":"[^"]*' | cut -d'"' -f4)
FLY_RMSE=$(echo "$RESULTS_JSON" | grep -o '"rmse":[0-9.]*' | head -n 1 | cut -d':' -f2)
echo "[Smoke Test] ✓ Verified metrics. Winner: $WINNER | Fly RMSE: $FLY_RMSE"

echo "[Smoke Test] 5. Verifying predictions CSV download..."
CSV_DATA=$(curl -s "http://127.0.0.1:$PORT/api/v1/experiments/$EXP_ID/predictions.csv")
if ! echo "$CSV_DATA" | grep -q "flycast"; then
    echo "ERROR: Predictions CSV download failed or did not contain flycast column."
    exit 1
fi
echo "[Smoke Test] ✓ Verified predictions CSV format."

echo ""
echo "============================================================"
echo "          FLYCAST SMOKE TEST PASSED SUCCESSFULLY!           "
echo "============================================================"
exit 0
