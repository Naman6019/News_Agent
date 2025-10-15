# Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Install Ollama CLI
RUN curl -fsSL https://ollama.com/install.sh | bash

# Pull Gemma3:1B model
RUN ollama pull gemma3:1b

# Default environment variables (overridden by env_file in docker-compose)
ENV OLLAMA_BASE_URL=http://localhost:11434
ENV OLLAMA_MODEL=gemma3:1b
ENV OLLAMA_MAX_TOKENS=500
ENV OLLAMA_TEMPERATURE=0.3

# Start Ollama server + FastAPI
CMD ["sh", "-c", "ollama serve & uvicorn app.main:app --host 0.0.0.0 --port 8000"]
