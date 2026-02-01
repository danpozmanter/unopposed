import json
import os


def test_ma_2026_counts():
    json_path = os.path.join(
        os.path.dirname(__file__), "../../election_data/massachusetts_2026.json"
    )
    with open(json_path) as f:
        data = json.load(f)

    assert data["total"] == 22, f"Expected 22 total unopposed, got {data['total']}"
    assert (
        data["total_races"] == 211
    ), f"Expected 211 total races, got {data['total_races']}"
    assert (
        len(data["unopposed_candidates"]) == 22
    ), f"Expected 22 candidates, got {len(data['unopposed_candidates'])}"


if __name__ == "__main__":
    test_ma_2026_counts()
    print("MA test passed: 22 unopposed / 211 races")
