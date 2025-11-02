# ==============================================================================
# Stage 1: Build Frontend
# ==============================================================================
FROM node:18-alpine AS frontend-builder

WORKDIR /frontend

# Copy package files
COPY web/frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy frontend source
COPY web/frontend/ ./

# Build frontend for production
RUN npm run build

# ==============================================================================
# Stage 2: Python Application
# ==============================================================================
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements for Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire modular structure
COPY main.py .
COPY core ./core
COPY handlers ./handlers
COPY models ./models
COPY utils ./utils
COPY web ./web

# Copy built frontend from stage 1
COPY --from=frontend-builder /frontend/dist ./web/frontend/dist

# Create necessary directories
RUN mkdir -p /app/session /app/data /media/movies /media/tv /media/temp

# Create non-root user
RUN useradd -m -u 1000 mediabutler && \
    chown -R mediabutler:mediabutler /app /media

USER mediabutler

# Default command (Telegram bot)
# Can be overridden in docker compose
CMD ["python", "-u", "main.py"]