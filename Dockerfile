# Backend Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (Docker cache optimization)
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code (baked into image)
COPY . .

# Make the entrypoint executable
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

# Entrypoint handles first-run initialization
ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]