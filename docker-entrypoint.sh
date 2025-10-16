#!/bin/bash
set -e

echo "=== Starting AI News Digest Worker ==="

# Start Ollama in background
ollama serve &
sleep 5

# Wait for Ollama API to be ready
until curl -s http://localhost:11434/api/tags > /dev/null; do
  echo "⏳ Waiting for Ollama API to start..."
  sleep 2
done
echo "✅ Ollama API is up."

# Run the digest worker
if [ -f "/app/app/send_digest.py" ]; then
  echo "✅ Found send_digest.py, starting digest worker..."
  python app/send_digest.py
else
  echo "⚠️ Digest script not found at /app/app/send_digest.py"
  echo "Listing /app contents for debugging:"
  ls -al /app
  echo "=== > Worker idle ==="
  tail -f /dev/null
fi
