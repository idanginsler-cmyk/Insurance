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
    DOMAIN="${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
    if [ -n "$CODESPACE_NAME" ]; then
      PUBLIC_URL="https://${CODESPACE_NAME}-8000.${DOMAIN}"
    else
      PUBLIC_URL="(set CODESPACE_NAME or check the PORTS tab)"
    fi
    echo ""
    echo "============================================================"
    echo " ✓ Fraud Detection API is running on port 8000."
    echo "============================================================"
    echo ""
    echo "  Open this URL on your phone or any browser:"
    echo ""
    echo "    $PUBLIC_URL"
    echo ""
    echo "  (If it asks for GitHub login, sign in with the same account"
    echo "   that owns this Codespace. To make the port public, open the"
    echo "   PORTS tab → right-click 8000 → Port Visibility → Public.)"
    echo ""
    echo "  Server logs: tail -f /tmp/fraud-detection-api.log"
    echo "  Stop server: pkill -f 'uvicorn fraud_detection'"
    echo ""
    exit 0
  fi
  sleep 1
done

echo "⚠ Server did not respond within 8 seconds. Last log lines:"
tail -30 /tmp/fraud-detection-api.log 2>/dev/null || true
