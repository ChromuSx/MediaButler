FROM python:3.11-slim

WORKDIR /app

# Installa dipendenze sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements per cache Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia TUTTA la struttura modulare
COPY main.py .
COPY core ./core
COPY handlers ./handlers
COPY models ./models
COPY utils ./utils

# Crea directory necessarie
RUN mkdir -p /app/session /media/movies /media/tv /media/temp

# Crea utente non-root
RUN useradd -m -u 1000 mediabutler && \
    chown -R mediabutler:mediabutler /app /media

USER mediabutler

CMD ["python", "-u", "main.py"]