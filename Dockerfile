# --- Image de base ---
FROM python:3.12-slim

# --- Dépendances système ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-fra \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# --- Répertoire de travail dans le conteneur ---
WORKDIR /app

# --- Installation des dépendances Python ---
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=100 --retries=10 -r requirements.txt


# --- Copie du code source de l'application ---
COPY src/ ./src/
COPY main_ingestion.py main_rag.py ./

# --- Port exposé ---
EXPOSE 8000

# --- Commande de démarrage du conteneur ---
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]