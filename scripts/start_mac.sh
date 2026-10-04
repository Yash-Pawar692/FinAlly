#!/usr/bin/env bash
# Starts FinAlly via docker compose (macOS/Linux). Safe to run multiple times.
set -euo pipefail
cd "$(dirname "$0")/.."

BUILD_FLAG=""
for arg in "$@"; do
  if [ "$arg" = "--build" ]; then
    BUILD_FLAG="--build"
  fi
done

if [ -n "$BUILD_FLAG" ]; then
  docker compose up -d --build
else
  docker compose up -d
fi

echo ""
echo "FinAlly is starting at http://localhost:8000"
echo "Run 'docker compose logs -f' to follow logs, or scripts/stop_mac.sh to stop."

if command -v open >/dev/null 2>&1; then
  open "http://localhost:8000" 2>/dev/null || true
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://localhost:8000" 2>/dev/null || true
fi
