# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install OS dependencies
RUN apt-get update && apt-get install -y curl unzip git && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Install Ollama CLI
RUN curl -fsSL https://ollama.com/install.sh | bash


# Copy startup script and make it executable
COPY start.sh /start.sh
RUN chmod +x /start.sh


# Expose FastAPI port
EXPOSE 8000

# Start Ollama and FastAPI
CMD ["./start.sh"]

# Install system SSL certificates
RUN apt-get update && apt-get install -y ca-certificates && update-ca-certificates
