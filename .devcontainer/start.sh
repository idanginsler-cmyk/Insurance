#!/usr/bin/env bash
# Runs every time the user (re)attaches to the Codespace.
# Starts the API server in the background and prints the local URL.
# Note: pre-existing uvicorn processes are killed first to avoid
# port-in-use errors after a Codespace stop/restart.

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE/fraud-detection"

pkill -f "uvicorn fraud_detection" 2>/dev/null || true
sleep 1

mkdir -p /tmp
nohup uvicorn fraud_detection.api.server:app \
  --host 0.0.0.0 --port 8000 \
  > /tmp/fraud-detection-api.log 2>&1 &

# Give uvicorn a moment to bind the port.
for i in 1 2 3 4 5 6 7 8; do
  if curl -sS -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ 2>/dev/null | grep -q "^[23]"; then
    echo ""
    echo "✓ API server is running on port 8000."
    echo ""
    echo "  → Click the PORTS tab below (next to TERMINAL)"
    echo "  → Hover/right-click port 8000 → 'Open in Browser' (globe icon)"
    echo ""
    echo "  Server logs: tail -f /tmp/fraud-detection-api.log"
    echo "  Stop server: pkill -f 'uvicorn fraud_detection'"
    exit 0
  fi
  sleep 1
done

echo "⚠ Server did not respond within 8 seconds. Last log lines:"
tail -30 /tmp/fraud-detection-api.log 2>/dev/null || true
