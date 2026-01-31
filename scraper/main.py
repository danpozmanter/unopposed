import argparse
import sys
from datetime import datetime

from data import STATE_NAMES, deduplicate
from sources import ballotpedia
from output import render


def main():
    args = _parse_args()
    state = args.state.upper()
    if state not in STATE_NAMES:
        sys.exit(f"Unknown state code: {state}")

    print(f"Checking {STATE_NAMES[state]} ({args.year})...", file=sys.stderr)

    results = ballotpedia.scrape(state, args.year)
    results = deduplicate(results)

    render(results, state, args.year, args.json)


def _parse_args():
    p = argparse.ArgumentParser(description="Find unopposed candidates in US elections")
    p.add_argument("state", help="Two-letter state code (e.g. CA, TX, NY)")
    p.add_argument(
        "year",
        nargs="?",
        type=int,
        default=datetime.now().year,
        help="Election year in YYYY format (default: current year)",
    )
    p.add_argument("--json", action="store_true", help="Output as JSON")
    return p.parse_args()


if __name__ == "__main__":
    main()
