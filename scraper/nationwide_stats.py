#!/usr/bin/env python3
"""
Generate nationwide statistics from state election data files.
Reads all state JSON files and computes aggregated statistics per year.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path


def load_state_data(election_data_dir: Path) -> dict[str, list[dict]]:
    """Load all state JSON files grouped by year."""
    data_by_year: dict[str, list[dict]] = {}

    for filepath in election_data_dir.glob("*.json"):
        if filepath.name == "manifest.json":
            continue

        match = re.search(r"_(\d{4})\.json$", filepath.name)
        if not match:
            continue

        year = match.group(1)

        try:
            with open(filepath) as f:
                state_data = json.load(f)
                if "error" in state_data:
                    continue
                if year not in data_by_year:
                    data_by_year[year] = []
                data_by_year[year].append(state_data)
        except (json.JSONDecodeError, IOError):
            continue

    return data_by_year


def compute_state_stats(state_data: dict) -> dict:
    """Compute general/primary stats from a single state's data."""
    candidates = state_data.get("unopposed_candidates", [])
    total_races = state_data.get("total_races", 0)
    total_races_by_party = state_data.get("total_races_by_party", {})

    # Track unique races for general election
    general_races = set()
    general_by_party = {}

    # Track unique races per party for primaries
    primary_races_by_party: dict[str, set] = {}
    primary_unopposed_by_party = {}

    for c in candidates:
        party = c.get("party", "Unknown")
        race_key = (c.get("office"), c.get("district"))
        unopposed_in = c.get("unopposed_in", "")

        if "General" in unopposed_in:
            general_races.add(race_key)
            general_by_party[party] = general_by_party.get(party, 0) + 1

        if "Primary" in unopposed_in:
            if party not in primary_races_by_party:
                primary_races_by_party[party] = set()
            primary_races_by_party[party].add(race_key)
            primary_unopposed_by_party[party] = (
                primary_unopposed_by_party.get(party, 0) + 1
            )

    return {
        "general": {
            "total_unopposed": len(general_races),
            "total_races": total_races,
            "unopposed_by_party": general_by_party,
        },
        "primary": {
            "total_unopposed": sum(
                len(races) for races in primary_races_by_party.values()
            ),
            "total_races_by_party": total_races_by_party,
            "unopposed_by_party": primary_unopposed_by_party,
        },
    }


def compute_nationwide_stats(states_data: list[dict]) -> dict:
    """Compute nationwide stats from a list of state data for a single year."""
    general = {
        "total_unopposed": 0,
        "total_races": 0,
        "unopposed_by_party": {},
    }
    primary = {
        "total_unopposed": 0,
        "total_races_by_party": {},
        "unopposed_by_party": {},
    }

    for state_data in states_data:
        state_stats = compute_state_stats(state_data)

        # Aggregate general stats
        g = state_stats["general"]
        general["total_unopposed"] += g["total_unopposed"]
        general["total_races"] += g["total_races"]
        for party, count in g["unopposed_by_party"].items():
            general["unopposed_by_party"][party] = (
                general["unopposed_by_party"].get(party, 0) + count
            )

        # Aggregate primary stats
        p = state_stats["primary"]
        primary["total_unopposed"] += p["total_unopposed"]
        for party, count in p["total_races_by_party"].items():
            primary["total_races_by_party"][party] = (
                primary["total_races_by_party"].get(party, 0) + count
            )
        for party, count in p["unopposed_by_party"].items():
            primary["unopposed_by_party"][party] = (
                primary["unopposed_by_party"].get(party, 0) + count
            )

    return {"general": general, "primary": primary}


def generate_manifest(election_data_dir: Path) -> dict:
    """Generate the manifest with nationwide statistics."""
    data_by_year = load_state_data(election_data_dir)

    years = sorted(data_by_year.keys(), reverse=True)
    nationwide = {}

    for year in years:
        nationwide[year] = compute_nationwide_stats(data_by_year[year])

    return {
        "years": [int(y) for y in years],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "nationwide": nationwide,
    }


def main():
    script_dir = Path(__file__).parent
    election_data_dir = script_dir.parent / "election_data"

    if not election_data_dir.exists():
        print(f"Error: election_data directory not found at {election_data_dir}")
        return 1

    manifest = generate_manifest(election_data_dir)

    manifest_path = election_data_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Manifest written to {manifest_path}")
    print(f"Years: {manifest['years']}")
    return 0


if __name__ == "__main__":
    exit(main())
