#!/usr/bin/env bash
# Stops FinAlly via docker compose (macOS/Linux). Does not remove ./db — data persists.
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose down

echo "FinAlly stopped. Your data in ./db is preserved."
