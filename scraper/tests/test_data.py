from data import Race, normalize_party, deduplicate, _merge_unopposed, STATE_NAMES


def test_state_names_has_all_states():
    assert len(STATE_NAMES) == 51
    assert "CA" in STATE_NAMES
    assert "DC" in STATE_NAMES
    assert STATE_NAMES["NY"] == "New York"


def test_normalize_party_democratic():
    assert normalize_party("Democratic") == "Democrat"
    assert normalize_party("democrat") == "Democrat"
    assert normalize_party("dem") == "Democrat"


def test_normalize_party_republican():
    assert normalize_party("Republican") == "Republican"
    assert normalize_party("rep") == "Republican"
    assert normalize_party("GOP") == "Republican"


def test_normalize_party_other():
    assert normalize_party("Libertarian") == "Libertarian"
    assert normalize_party("green") == "Green/Rainbow"
    assert normalize_party("independent") == "Independent"


def test_normalize_party_unknown():
    assert normalize_party("Some Other Party") == "Some Other Party"
    assert normalize_party("  spaced  ") == "spaced"


def test_race_key():
    r = Race(
        "CA", "US House", "District 1", "John Doe", "Democrat", "Primary", "Ballotpedia"
    )
    assert r.key() == ("CA", "US House", "District 1", "John Doe")


def test_race_to_dict():
    r = Race(
        "CA", "US House", "District 1", "John Doe", "Democrat", "Primary", "Ballotpedia"
    )
    d = r.to_dict()
    assert d["state"] == "CA"
    assert d["candidate"] == "John Doe"
    assert d["party"] == "Democrat"


def test_merge_unopposed_primary_only():
    assert _merge_unopposed("Primary", "Primary") == "Primary"


def test_merge_unopposed_general_only():
    assert _merge_unopposed("General", "General") == "General"


def test_merge_unopposed_both():
    assert _merge_unopposed("Primary", "General") == "Primary & General"
    assert _merge_unopposed("General", "Primary") == "Primary & General"


def test_merge_unopposed_already_merged():
    assert _merge_unopposed("Primary & General", "Primary") == "Primary & General"


def test_deduplicate_no_duplicates():
    races = [
        Race(
            "CA",
            "US House",
            "District 1",
            "John Doe",
            "Democrat",
            "Primary",
            "Ballotpedia",
        ),
        Race(
            "CA",
            "US House",
            "District 2",
            "Jane Doe",
            "Republican",
            "General",
            "Ballotpedia",
        ),
    ]
    result = deduplicate(races)
    assert len(result) == 2


def test_deduplicate_merges_same_candidate():
    races = [
        Race(
            "CA",
            "US House",
            "District 1",
            "John Doe",
            "Democrat",
            "Primary",
            "Ballotpedia",
        ),
        Race(
            "CA",
            "US House",
            "District 1",
            "John Doe",
            "Democrat",
            "General",
            "Ballotpedia",
        ),
    ]
    result = deduplicate(races)
    assert len(result) == 1
    assert result[0].unopposed_in == "Primary & General"


def test_deduplicate_keeps_different_candidates():
    races = [
        Race(
            "CA",
            "US House",
            "District 1",
            "John Doe",
            "Democrat",
            "Primary",
            "Ballotpedia",
        ),
        Race(
            "CA",
            "US House",
            "District 1",
            "Jane Doe",
            "Republican",
            "Primary",
            "Ballotpedia",
        ),
    ]
    result = deduplicate(races)
    assert len(result) == 2
