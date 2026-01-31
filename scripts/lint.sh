#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

echo "Formatting Python..."
(cd scraper && uv run black . && uv run ruff check --fix .)

echo ""
echo "Linting TypeScript/Svelte..."
pnpm exec eslint --fix .

echo ""
echo "Done!"
