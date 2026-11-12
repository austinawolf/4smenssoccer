#!/usr/bin/env bash
set -euo pipefail

# Start the isolated two-team staff-workflow demo.
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "$PROJECT_DIR/run-simple-demo.sh" "$@"
