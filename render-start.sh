#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

uv run --locked python manage.py migrate --noinput
uv run --locked python manage.py loaddata siteapp/fixtures/local_demo.json
exec uv run --locked python -m gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-10000}"
