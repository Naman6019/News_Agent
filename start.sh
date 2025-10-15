#!/bin/sh

# Start Ollama server in the background
echo "Starting Ollama server..."
ollama serve &

# Wait a few seconds to ensure Ollama is ready
sleep 5

# Pull Gemma3 model if not already present
if ! ollama list | grep -q "gemma3:1b"; then
    echo "Pulling Gemma3 model..."
    ollama pull gemma3:1b
fi

# Start FastAPI app
echo "Starting FastAPI app..."
uvicorn app.main:app --host 0.0.0.0 --port 8000
