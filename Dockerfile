FROM python:3.11-slim as builder

WORKDIR /build
    
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --user --no-cache-dir \
    torch==2.10.0 \
    --index-url https://download.pytorch.org/whl/cpu

RUN pip install --user --no-cache-dir -r requirements.txt

ENV HF_HOME=/build/hf_cache

RUN python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; AutoTokenizer.from_pretrained('ProsusAI/finbert'); AutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert'); print('FinBERT downloaded successfully')"

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
COPY --from=builder /build/hf_cache /app/hf_cache

ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:$PYTHONPATH \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/hf_cache \
    TRANSFORMERS_CACHE=/app/hf_cache

COPY . .

RUN mkdir -p /app/logs /app/mlartifacts

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7860/api/health || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]