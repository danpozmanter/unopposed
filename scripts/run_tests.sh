#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../scraper"

uv run pytest "$@"
