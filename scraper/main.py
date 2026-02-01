import argparse
import json
import sys
from datetime import datetime, timezone

from data import STATE_NAMES, deduplicate
from sources import ballotpedia
from output import render

MIN_EXPECTED_RACES = 10


def main():
    args = _parse_args()
    state = args.state.upper()
    if state not in STATE_NAMES:
        sys.exit(f"Unknown state code: {state}")

    print(f"Checking {STATE_NAMES[state]} ({args.year})...", file=sys.stderr)

    results, stats = ballotpedia.scrape(state, args.year)

    if stats.total_races < MIN_EXPECTED_RACES:
        print(
            f"ERROR: Only found {stats.total_races} races for {state}, expected at least {MIN_EXPECTED_RACES}",
            file=sys.stderr,
        )
        if args.json:
            error_data = {
                "error": True,
                "message": f"Scraping failed: only found {stats.total_races} races",
                "state": state,
                "state_name": STATE_NAMES.get(state, state),
                "year": args.year,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }
            json.dump(error_data, sys.stdout, indent=2)
            print()
        sys.exit(1)

    results = deduplicate(results)
    render(results, stats, state, args.year, args.json)


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
