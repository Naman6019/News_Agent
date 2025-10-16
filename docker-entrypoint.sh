#!/usr/bin/env bash
set -euo pipefail

MODEL_NAME="${OLLAMA_MODEL:=gemma3:1b}"
OLLAMA_HEALTH_URL="http://127.0.0.1:11434/api/tags"
PY_SCRIPT_PATH="${DIGEST_SCRIPT_PATH:-/app/send_digest.py}"
MAX_HEALTH_RETRIES=30
HEALTH_SLEEP=2

echo "===> Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to respond
echo "===> Waiting for Ollama to become ready..."
i=0
until curl -fsSL "$OLLAMA_HEALTH_URL" >/dev/null 2>&1; do
  i=$((i+1))
  if [ $i -ge $MAX_HEALTH_RETRIES ]; then
    echo "❌ Ollama not responding after $((MAX_HEALTH_RETRIES*HEALTH_SLEEP))s"
    wait "$OLLAMA_PID" || true
    exit 1
  fi
  sleep $HEALTH_SLEEP
done
echo "✅ Ollama API is up."

echo "===> Pulling model ${MODEL_NAME}..."
ollama pull "${MODEL_NAME}" || echo "⚠️ Model pull failed (continuing anyway)"

# Run digest worker
if [ -f "${PY_SCRIPT_PATH}" ]; then
  echo "===> Launching News Digest worker (${PY_SCRIPT_PATH})..."
  python "${PY_SCRIPT_PATH}" &
  PY_PID=$!
else
  echo "⚠️ Digest script not found at ${PY_SCRIPT_PATH}"
  PY_PID=""
fi

# Keep container alive
echo "===> Worker running. Monitoring processes..."
while true; do
  sleep 15
  if ! kill -0 "$OLLAMA_PID" 2>/dev/null; then
    echo "❌ Ollama crashed — exiting for restart"
    exit 2
  fi
  if [ -n "${PY_PID:-}" ] && ! kill -0 "$PY_PID" 2>/dev/null; then
    echo "⚠️ Digest script exited; keeping container alive for inspection"
    ps -ef | grep python
  fi
done
