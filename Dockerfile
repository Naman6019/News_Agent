# ----------------------------
# Base Image
# ----------------------------
FROM python:3.11-slim

WORKDIR /app

# ----------------------------
# Install system dependencies and Ollama
# ----------------------------
RUN apt-get update && apt-get install -y \
    gcc curl git ca-certificates \
    && curl -fsSL https://ollama.com/install.sh | bash \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------
# Copy dependencies
# ----------------------------
COPY requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt

# ----------------------------
# Copy project files
# ----------------------------
COPY . .

# ----------------------------
# Create non-root user
# ----------------------------
RUN useradd -m -r newsagent && chown -R newsagent /app
USER newsagent

EXPOSE 8000

# ----------------------------
# Default command (Render overrides this per service)
# ----------------------------
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
