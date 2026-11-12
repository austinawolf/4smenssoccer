#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Keep uv's cache inside the project in this managed workspace.
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PROJECT_DIR/.uv-cache}"
BIND_ADDRESS="${DJANGO_BIND_ADDRESS:-127.0.0.1:8000}"

uv run --locked python manage.py migrate
exec uv run --locked python manage.py runserver "$BIND_ADDRESS"
