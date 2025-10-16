#!/bin/bash
set -e

echo "=== Starting AI News Digest Worker ==="

# --- 1️⃣ Start Ollama in the background ---
ollama serve &

# --- 2️⃣ Wait for Ollama to be ready ---
until curl -s http://localhost:11434/api/tags > /dev/null; do
  echo "⏳ Waiting for Ollama to start..."
  sleep 2
done
echo "✅ Ollama API is up."
# Wait extra to ensure model weights fully loaded
echo "🕐 Waiting for model load stabilization..."
sleep 20
# Allow Ollama a few extra seconds to finish loading model into memory
sleep 10
echo "🔥 Preloading Gemma model..."
curl -s -X POST http://localhost:11434/api/generate -d '{"model": "gemma3:1b", "prompt": "ping"}' > /dev/null || true
echo "✅ Gemma model warm-up complete."

# --- 3️⃣ Set timezone to Asia/Kolkata (IST) ---
export TZ="Asia/Kolkata"
echo "🕓 Timezone set to: $TZ"
date

# --- 4️⃣ Function to calculate next run delay (8 AM and 6 PM IST) ---
next_run_delay() {
  now_epoch=$(date +%s)
  now_hour=$(date +%H)
  now_minute=$(date +%M)

  # Define the next scheduled times (in 24h format)
  morning_hour=8
  evening_hour=18

  if (( now_hour < morning_hour )); then
      # Before 8 AM → next run at 8 AM today
      next_run=$(date -d "today $morning_hour:00:00" +%s)
  elif (( now_hour < evening_hour )); then
      # Between 8 AM and 6 PM → next run at 6 PM today
      next_run=$(date -d "today $evening_hour:00:00" +%s)
  else
      # After 6 PM → next run tomorrow 8 AM
      next_run=$(date -d "tomorrow $morning_hour:00:00" +%s)
  fi

  delay=$(( next_run - now_epoch ))
  echo $delay
}

# --- 5️⃣ Main loop: run only at 8 AM and 6 PM IST ---
if [ -f "/app/app/send_digest.py" ]; then
  echo "✅ Found send_digest.py, starting scheduled digest cycles..."

  while true; do
    current_time=$(date +"%Y-%m-%d %H:%M:%S")
    echo "🕒 Current time: $current_time (IST)"
    echo "🚀 Running AI News Digest..."
    python -m app.send_digest

    echo "✅ Digest cycle complete."

    # Calculate time until next 8 AM or 6 PM
    delay=$(next_run_delay)
    hrs=$((delay / 3600))
    mins=$(( (delay % 3600) / 60 ))
    echo "⏰ Next run in ${hrs}h ${mins}m at $(date -d "+$delay seconds" +"%H:%M %p") IST"
    sleep $delay
  done
else
  echo "⚠️ Digest script not found at /app/app/send_digest.py"
  tail -f /dev/null
fi