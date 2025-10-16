# ----------------------------
# Base Image
# ----------------------------
FROM python:3.11-slim

WORKDIR /app

# ----------------------------
# Install system deps + Ollama
# ----------------------------
RUN apt-get update && apt-get install -y \
    curl git ca-certificates \
    && curl -fsSL https://ollama.com/install.sh | bash \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------
# Copy dependencies
# ----------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt

# ----------------------------
# Copy project
# ----------------------------
COPY . .

# ----------------------------
# Create non-root user
# ----------------------------
RUN useradd -m -r newsagent && chown -R newsagent /app
USER newsagent

# Expose Ollama port (for API if needed)
EXPOSE 11434

# ----------------------------
# Default Command — API (Render overrides this per service)
# ----------------------------
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
