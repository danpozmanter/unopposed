import json
import random
from pathlib import Path

import pytest

ELECTION_DATA_DIR = Path(__file__).parent.parent.parent / "election_data"


def get_election_files():
    """Get all election JSON files."""
    return [f for f in ELECTION_DATA_DIR.glob("*.json") if f.name != "manifest.json"]


def load_election_data(filepath):
    """Load election data, returning None for error files."""
    data = json.loads(filepath.read_text())
    if "error" in data:
        return None
    return data


@pytest.fixture(scope="module")
def sample_files():
    """Sample 20 random files for testing."""
    files = get_election_files()
    return random.sample(files, min(20, len(files)))


def test_general_unopposed_never_exceeds_total(sample_files):
    """general.total_unopposed <= general.total_races for sampled files."""
    for filepath in sample_files:
        data = load_election_data(filepath)
        if not data or "general" not in data:
            continue

        general = data["general"]
        total_unopposed = general.get("total_unopposed", 0)
        total_races = general.get("total_races", 0)

        assert total_unopposed <= total_races, (
            f"{filepath.name}: general.total_unopposed ({total_unopposed}) "
            f"exceeds general.total_races ({total_races})"
        )


def test_primary_unopposed_never_exceeds_total_by_party(sample_files):
    """primary.unopposed_by_party[p] <= primary.total_races_by_party[p] for sampled files."""
    for filepath in sample_files:
        data = load_election_data(filepath)
        if not data or "primary" not in data:
            continue

        primary = data["primary"]
        unopposed_by_party = primary.get("unopposed_by_party", {})
        total_by_party = primary.get("total_races_by_party", {})

        for party, unopposed_count in unopposed_by_party.items():
            total_count = total_by_party.get(party, 0)
            assert unopposed_count <= total_count, (
                f"{filepath.name}: {party} primary has {unopposed_count} unopposed "
                f"but only {total_count} total races"
            )


def test_total_field_equals_candidate_count(sample_files):
    """total field equals len(unopposed_candidates) for sampled files."""
    for filepath in sample_files:
        data = load_election_data(filepath)
        if not data:
            continue

        total = data.get("total", 0)
        candidates = data.get("unopposed_candidates", [])

        assert total == len(
            candidates
        ), f"{filepath.name}: total ({total}) != candidate count ({len(candidates)})"
