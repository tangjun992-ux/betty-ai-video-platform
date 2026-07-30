FROM python:3.12-slim AS base

WORKDIR /app

# System dependencies. ffmpeg is REQUIRED for timeline compose, subtitle burn,
# poster/thumbnail generation and audio muxing — missing it silently breaks the
# video/timeline features in production.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Create storage directory
RUN mkdir -p /app/storage

# Migration-aware entrypoint (runs `alembic upgrade head` when RUN_MIGRATIONS=1)
RUN chmod +x /app/entrypoint.sh

ENV PYTHONUNBUFFERED=1
ENV ENV=production

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
