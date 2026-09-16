# FlyCast Backend Production Dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR=/data \
    PORT=8000

WORKDIR /app

# Install runtime system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies with layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and scripts
COPY app/ ./app/
COPY scripts/ ./scripts/
RUN chmod +x ./scripts/start.sh

# Persistent volume directory for connectome and experiments
RUN mkdir -p /data/brain /data/experiments /data/demos

EXPOSE 8000

CMD ["./scripts/start.sh"]
