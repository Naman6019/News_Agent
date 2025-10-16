#!/usr/bin/env bash
set -euo pipefail

# config (tweak model name / python path if needed)
MODEL_NAME="${OLLAMA_MODEL:=gemma3:1b}"
OLLAMA_HEALTH_URL="http://127.0.0.1:11434/api/tags"
PY_SCRIPT_PATH="${DIGEST_SCRIPT_PATH:-/app/send_digest.py}"
MAX_HEALTH_RETRIES=30
HEALTH_SLEEP=2

echo "===> Starting ollama server..."
# start ollama in background (it runs by default on 11434)
ollama serve & 
OLLAMA_PID=$!

# wait for ollama HTTP endpoint to respond
echo "===> Waiting for Ollama HTTP endpoint..."
i=0
while ! curl -sS "${OLLAMA_HEALTH_URL}" >/dev/null 2>&1; do
  i=$((i+1))
  if [ $i -ge $MAX_HEALTH_RETRIES ]; then
    echo "ERROR: Ollama did not respond within $((MAX_HEALTH_RETRIES * HEALTH_SLEEP))s" >&2
    # keep server logs visible then exit non-zero to fail deploy
    wait "${OLLAMA_PID}" || true
    exit 1
  fi
  sleep $HEALTH_SLEEP
done
echo "===> Ollama HTTP API responding."

# pull the model (idempotent)
echo "===> Pulling model ${MODEL_NAME}..."
ollama pull "${MODEL_NAME}" || {
  echo "WARNING: ollama pull failed (continue anyway)"; 
}

# run your digest script. if it exits immediately, we will not let container die:
if [ -f "${PY_SCRIPT_PATH}" ]; then
  echo "===> Launching digest worker: ${PY_SCRIPT_PATH}"
  # use the venv pip-installed python (PATH env already points to it from Dockerfile)
  python "${PY_SCRIPT_PATH}" &
  PY_PID=$!
else
  echo "WARNING: digest script not found at ${PY_SCRIPT_PATH}. Skipping start."
  PY_PID=""
fi

# monitor both processes; if python exits, keep container alive for debugging
echo "===> Processes started. Monitoring (press Ctrl+C to stop)..."
# print a small loop that keeps the container alive but reports statuses
while true; do
  sleep 10
  if ! kill -0 "${OLLAMA_PID}" 2>/dev/null; then
    echo "ERROR: Ollama process died. Exiting container for restart." >&2
    # allow docker to restart (Render will restart the service if configured)
    exit 2
  fi
  if [ -n "${PY_PID:-}" ] && ! kill -0 "${PY_PID}" 2>/dev/null; then
    echo "WARNING: Python worker process has exited. Leaving container running for debug."
    # dump a little status log and continue (so container doesn't exit)
    ps aux | sed -n '1,200p'
    echo "If you want container to restart the worker automatically, modify entrypoint to relaunch it."
  fi
done
