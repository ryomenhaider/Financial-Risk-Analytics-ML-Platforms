FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# FIX: Install torch CPU separately first (large index)
RUN pip install --user --no-cache-dir \
        torch==2.1.0 \
        --index-url https://download.pytorch.org/whl/cpu

RUN pip install --user --no-cache-dir -r requirements.txt

# FIX: DO NOT pre-download FinBERT at build time.
# Koyeb free tier has 512 MB RAM — baking a 1.3 GB model into the image causes
# OOM kills on startup before uvicorn ever binds to the port.
# FinBERT is now loaded lazily on first /sentiment request (see ml/sentiment_analyzer.py).

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    # HF_HOME points to a writable directory inside the container at runtime
    HF_HOME=/app/hf_cache \
    TRANSFORMERS_CACHE=/app/hf_cache \
    DASH_URL_BASE_PATHNAME=/dashboard/ \
    # FIX: set API_BASE_URL so Dash callbacks hit the correct internal address
    API_BASE_URL=http://localhost:7860

COPY . .

RUN mkdir -p /app/logs /app/mlartifacts /app/hf_cache

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7860/api/health || exit 1

# Single process: FastAPI serves both the REST API and Dash via WSGIMiddleware
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]