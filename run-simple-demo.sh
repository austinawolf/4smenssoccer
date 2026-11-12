#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

export UV_CACHE_DIR="${UV_CACHE_DIR:-$PROJECT_DIR/.uv-cache}"
export DJANGO_SQLITE_PATH="$PROJECT_DIR/.simple-demo.sqlite3"
export DJANGO_MEDIA_ROOT="$PROJECT_DIR/.simple-demo-media"
if [[ -n "${RENDER:-}" || -n "${PORT:-}" ]]; then
  BIND_ADDRESS="${DJANGO_BIND_ADDRESS:-0.0.0.0:${PORT:-8001}}"
else
  BIND_ADDRESS="${DJANGO_BIND_ADDRESS:-127.0.0.1:8001}"
fi
DEMO_PORT="${BIND_ADDRESS##*:}"

# Restart an existing instance of this demo before replacing its SQLite file.
# Refuse to disturb another service that happens to use the same port.
LISTENING_PIDS="$(ss -ltnp "sport = :$DEMO_PORT" 2>/dev/null | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' | sort -u)"
for PID in $LISTENING_PIDS; do
  PROCESS_CWD="$(readlink -f "/proc/$PID/cwd" 2>/dev/null || true)"
  PROCESS_CMD="$(tr '\0' ' ' <"/proc/$PID/cmdline" 2>/dev/null || true)"
  if [[ "$PROCESS_CWD" == "$PROJECT_DIR" && "$PROCESS_CMD" == *"manage.py runserver"* ]]; then
    kill -TERM "$PID"
    for _ in {1..50}; do
      kill -0 "$PID" 2>/dev/null || break
      sleep 0.1
    done
    if kill -0 "$PID" 2>/dev/null; then
      echo "Existing demo server (PID $PID) did not stop; leaving its database untouched." >&2
      exit 1
    fi
  else
    echo "Port $DEMO_PORT is occupied by another process (PID $PID); leaving it and the demo database untouched." >&2
    exit 1
  fi
done

# This demo database and its uploads are disposable and reset from its fixture on each start.
rm -f -- "$DJANGO_SQLITE_PATH" "$DJANGO_SQLITE_PATH-journal" "$DJANGO_SQLITE_PATH-wal" "$DJANGO_SQLITE_PATH-shm"
rm -rf -- "$DJANGO_MEDIA_ROOT"
uv run --locked python manage.py migrate
uv run --locked python manage.py loaddata siteapp/fixtures/local_demo_simple.json
uv run --locked python manage.py shell -c 'from siteapp.models import ScoreReview; assert ScoreReview.objects.filter(status=ScoreReview.Status.PENDING).exists(), "The simple demo fixture must include a pending result review."'
exec uv run --locked python manage.py runserver "$BIND_ADDRESS"
