FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-fra \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copier le requirements.txt
COPY requirements.txt .

# SUPPRIMER LES HACHAGES (solution définitive)
RUN sed -i 's/ --hash=sha256:[a-f0-9]*//g' requirements.txt && \
    # Supprimer aussi pywin32 (package Windows uniquement)
    sed -i '/pywin32/d' requirements.txt

# 1. Installe torch CPU-only
RUN pip install --no-cache-dir --default-timeout=100 --retries=10 \
    torch==2.13.0+cpu --index-url https://download.pytorch.org/whl/cpu --no-deps

# 2. Installer les dépendances principales
RUN pip install --no-cache-dir --default-timeout=100 --retries=10 -r requirements.txt

# 3. DÉSINSTALLER ET RÉINSTALLER le package problématique
RUN pip uninstall -y prometheus-fastapi-instrumentator prometheus-client starlette anyio || true
RUN pip install --no-cache-dir prometheus-fastapi-instrumentator==8.0.2

# 4. Vérifier l'import
RUN python -c "from prometheus_fastapi_instrumentator import Instrumentator; print('✅ prometheus-fastapi-instrumentator OK')"

COPY src/ ./src/
COPY main_ingestion.py main_rag.py ./

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]