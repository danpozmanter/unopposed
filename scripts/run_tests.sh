#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

echo "=== Python tests ==="
(cd scraper && uv run pytest "$@")

echo ""
echo "=== TypeScript tests ==="
pnpm test
