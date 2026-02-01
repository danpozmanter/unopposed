import subprocess
import sys
import json
import os

SCRAPER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_scraper(state, year):
    result = subprocess.run(
        [sys.executable, "main.py", state, str(year), "--json"],
        cwd=SCRAPER_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def count_unique_races_by_party(data):
    races_by_party = {}
    for c in data.get("unopposed_candidates", []):
        party = c["party"]
        race_key = (c["office"], c["district"])
        if party not in races_by_party:
            races_by_party[party] = set()
        races_by_party[party].add(race_key)
    return {party: len(races) for party, races in races_by_party.items()}


def test_ma_2026_unopposed_never_exceeds_total_by_party():
    data = run_scraper("MA", 2026)
    assert data is not None, "Scraper failed for MA 2026"

    unopposed_by_party = count_unique_races_by_party(data)
    total_by_party = data.get("total_races_by_party", {})

    for party, unopposed_count in unopposed_by_party.items():
        total_count = total_by_party.get(party, 0)
        assert unopposed_count <= total_count, (
            f"MA 2026: {party} has {unopposed_count} unopposed races "
            f"but only {total_count} total races"
        )


def test_va_2025_unopposed_never_exceeds_total_by_party():
    data = run_scraper("VA", 2025)
    assert data is not None, "Scraper failed for VA 2025"

    unopposed_by_party = count_unique_races_by_party(data)
    total_by_party = data.get("total_races_by_party", {})

    for party, unopposed_count in unopposed_by_party.items():
        total_count = total_by_party.get(party, 0)
        assert unopposed_count <= total_count, (
            f"VA 2025: {party} has {unopposed_count} unopposed races "
            f"but only {total_count} total races"
        )


def test_total_unopposed_races_never_exceeds_total_races_ma_2026():
    data = run_scraper("MA", 2026)
    assert data is not None, "Scraper failed for MA 2026"

    all_races = set()
    for c in data.get("unopposed_candidates", []):
        all_races.add((c["office"], c["district"]))

    total_unopposed_races = len(all_races)
    total_races = data.get("total_races", 0)

    assert total_unopposed_races <= total_races, (
        f"MA 2026: {total_unopposed_races} unique unopposed races "
        f"exceeds {total_races} total races"
    )
