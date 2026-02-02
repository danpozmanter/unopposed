import json
import os


def test_ma_2026_data_consistency():
    json_path = os.path.join(
        os.path.dirname(__file__), "../../election_data/massachusetts_2026.json"
    )
    with open(json_path) as f:
        data = json.load(f)

    assert data["total"] == len(
        data["unopposed_candidates"]
    ), "total field should match candidate count"
    assert data["total_races"] > 0, "should have total_races"
    assert (
        data["total"] <= data["total_races"]
    ), "unopposed should not exceed total races"


if __name__ == "__main__":
    test_ma_2026_data_consistency()
    print("MA test passed")
