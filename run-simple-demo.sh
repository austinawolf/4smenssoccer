#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

export UV_CACHE_DIR="${UV_CACHE_DIR:-$PROJECT_DIR/.uv-cache}"
export DJANGO_SQLITE_PATH="$PROJECT_DIR/.simple-demo.sqlite3"
export DJANGO_MEDIA_ROOT="$PROJECT_DIR/.simple-demo-media"
BIND_ADDRESS="${DJANGO_BIND_ADDRESS:-127.0.0.1:8001}"

# This demo database is disposable and reset from its own fixture on each start.
rm -f -- "$DJANGO_SQLITE_PATH" "$DJANGO_SQLITE_PATH-journal" "$DJANGO_SQLITE_PATH-wal" "$DJANGO_SQLITE_PATH-shm"
uv run --locked python manage.py migrate
uv run --locked python manage.py loaddata siteapp/fixtures/local_demo_simple.json
exec uv run --locked python manage.py runserver "$BIND_ADDRESS"
