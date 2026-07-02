FROM python:3.12-slim AS base

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Create storage directory
RUN mkdir -p /app/storage

ENV PYTHONUNBUFFERED=1
ENV ENV=production

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
