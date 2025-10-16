# ----------------------------
# Base Image
# ----------------------------
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y gcc curl && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire app
COPY . .

# Create non-root user
RUN useradd -m -r newsagent && chown -R newsagent /app
USER newsagent

# Expose FastAPI port (for web service)
EXPOSE 8000

# Default command (Render overrides this anyway)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
