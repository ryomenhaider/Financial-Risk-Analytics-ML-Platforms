# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install PyTorch CPU-only wheel first (large, separate layer for better caching)
RUN pip install --user --no-cache-dir \
        torch==2.1.0 \
        --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Pre-download FinBERT weights into the image so the container starts cold-fast
ENV HF_HOME=/build/hf_cache
RUN python - <<'EOF'
from transformers import AutoTokenizer, AutoModelForSequenceClassification
AutoTokenizer.from_pretrained("ProsusAI/finbert")
AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
print("FinBERT cached successfully")
EOF

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pip-installed packages and FinBERT weights from builder
COPY --from=builder /root/.local           /root/.local
COPY --from=builder /build/hf_cache        /app/hf_cache

ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    HF_HOME=/app/hf_cache \
    TRANSFORMERS_CACHE=/app/hf_cache

COPY . .

RUN mkdir -p /app/logs /app/mlartifacts

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7860/api/health || exit 1

# Single process: uvicorn serves both FastAPI routes and the Dash WSGI app
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]