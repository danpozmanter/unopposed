# Scraper

Fetches unopposed candidate data from Ballotpedia.

## Setup

```bash
uv sync
```

## Usage

```bash
uv run python main.py STATE [YEAR] [--json]
```

## Examples

```bash
uv run python main.py CA
uv run python main.py TX 2026
uv run python main.py NY 2026 --json
```

## Tests

```bash
uv run pytest
```

## Offices Checked

- US Senate
- US House
- Governor
- State Senate
- State House
