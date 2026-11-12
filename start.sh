#!/usr/bin/env bash
set -euo pipefail

# Start the regular local website. Use start-simple-demo.sh for the isolated
# two-team demo instead.
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "$PROJECT_DIR/run-local.sh" "$@"
