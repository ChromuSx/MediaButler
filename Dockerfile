FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY mediabutler.py .

# Create necessary directories
RUN mkdir -p /app/session /media/movies /media/tv /media/temp

# Create non-root user
RUN useradd -m -u 1000 mediabutler && \
    chown -R mediabutler:mediabutler /app /media

# Switch to non-root user
USER mediabutler

# Run the bot
CMD ["python", "mediabutler.py"]