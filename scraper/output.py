import json
import re
import sys
from datetime import datetime, timezone
from data import STATE_NAMES

OFFICES = ["US Senate", "US House", "Governor", "State Senate", "State House"]


def render(results, stats, state, year, as_json):
    if as_json:
        _json_output(results, stats, state, year)
    else:
        _text_output(results, stats, state, year)


def _json_output(results, stats, state, year):
    data = {
        "state": state,
        "state_name": STATE_NAMES.get(state, state),
        "year": year,
        "total": len(results),
        "total_races": stats.total_races,
        "total_races_by_party": stats.races_by_party,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "unopposed_candidates": [r.to_dict() for r in results],
    }
    json.dump(data, sys.stdout, indent=2)
    print()


def _text_output(results, stats, state, year):
    name = STATE_NAMES.get(state, state)
    print(f"\nUnopposed Candidates — {name} ({year})")
    print("=" * 50)
    if stats.total_races > 0:
        pct = len(results) / stats.total_races * 100
        print(f"\n{len(results)} of {stats.total_races} races unopposed ({pct:.1f}%)")

    if not results:
        print("\nNo unopposed candidates found.")
        print(_footer())
        return

    by_office = {}
    for r in results:
        by_office.setdefault(r.office, []).append(r)

    for office in OFFICES:
        races = by_office.pop(office, [])
        _print_office(office, races)

    for office in sorted(by_office):
        _print_office(office, by_office[office])

    print(_footer())


def _print_office(office, races):
    print(f"\n  {office}")
    if not races:
        print("    (none found)")
        return
    for r in sorted(races, key=lambda x: _district_sort_key(x.district)):
        print(f"    {r.district}: {r.candidate} ({r.party})")
        print(f"      Unopposed in: {r.unopposed_in}  |  Source: {r.source}")


def _district_sort_key(district):
    m = re.search(r"(\d+)", district)
    return (int(m.group(1)),) if m else (999999, district)


def _footer():
    return (
        "\n--------------------------------------------------\n"
        "Source: Ballotpedia\n"
        "Note: Results depend on data availability at time of query.\n"
    )
