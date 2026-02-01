import json
import subprocess
import sys
import os

SCRAPER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_error_on_low_race_count():
    result = subprocess.run(
        [sys.executable, "main.py", "DC", "2099", "--json"],
        cwd=SCRAPER_DIR,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1, f"Expected exit code 1, got {result.returncode}"

    output = json.loads(result.stdout)
    assert output.get("error") is True, "Expected error field to be True"
    assert "message" in output, "Expected message field in error output"
    assert output.get("state") == "DC", f"Expected state DC, got {output.get('state')}"
    assert output.get("year") == 2099, f"Expected year 2099, got {output.get('year')}"


def test_success_on_valid_state():
    result = subprocess.run(
        [sys.executable, "main.py", "MA", "2026", "--json"],
        cwd=SCRAPER_DIR,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Expected exit code 0, got {result.returncode}"

    output = json.loads(result.stdout)
    assert "error" not in output, "Should not have error field on success"
    assert output.get("total_races", 0) >= 10, "Should have at least 10 races"


if __name__ == "__main__":
    test_error_on_low_race_count()
    print("Error fallback test passed")
    test_success_on_valid_state()
    print("Success test passed")
