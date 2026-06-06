# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir "fastapi>=0.115.0" "uvicorn[standard]>=0.30.0"

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY src/ ./src/
COPY pyproject.toml .

# Non-root user — required by Azure Container Apps security policy
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# Azure Container Apps expects the app on port 8000 (configurable)
EXPOSE 8000

# Liveness probe path: GET /health
# Azure Container Apps will restart the container if this returns non-2xx
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "capital_market_risk_review.api:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1"]

