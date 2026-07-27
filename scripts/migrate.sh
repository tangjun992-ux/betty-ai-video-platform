#!/bin/bash
# Database migration runner
set -e

cd "$(dirname "$0")/../backend"

source .venv/bin/activate

echo "Running database migrations..."
alembic upgrade head

echo "Migration complete."
