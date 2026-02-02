from data import (
    Race,
    RaceStats,
    normalize_party,
    deduplicate,
    _merge_unopposed,
    STATE_NAMES,
)


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


def test_race_stats_add_race():
    stats = RaceStats()
    stats.add_race(["Democrat", "Republican"])
    assert stats.total_races == 1
    assert stats.races_by_party["Democrat"] == 1
    assert stats.races_by_party["Republican"] == 1


def test_race_stats_add_parties_without_incrementing_total():
    stats = RaceStats()
    stats.add_race(["Democrat"])
    stats.add_parties(["Republican"])
    assert stats.total_races == 1
    assert stats.races_by_party["Democrat"] == 1
    assert stats.races_by_party["Republican"] == 1


def test_race_stats_merge():
    stats1 = RaceStats()
    stats1.add_race(["Democrat"])
    stats2 = RaceStats()
    stats2.add_race(["Republican"])
    stats1.merge(stats2)
    assert stats1.total_races == 2
    assert stats1.races_by_party["Democrat"] == 1
    assert stats1.races_by_party["Republican"] == 1


def test_race_stats_accumulates_party_counts():
    stats = RaceStats()
    stats.add_race(["Democrat"])
    stats.add_race(["Democrat", "Republican"])
    stats.add_parties(["Democrat"])
    assert stats.total_races == 2
    assert stats.races_by_party["Democrat"] == 3
    assert stats.races_by_party["Republican"] == 1


def test_race_stats_add_general_race():
    stats = RaceStats()
    stats.add_general_race(["Democrat", "Republican"])
    assert stats.general_total_races == 1
    assert stats.primary_races_by_party["Democrat"] == 1
    assert stats.primary_races_by_party["Republican"] == 1


def test_race_stats_add_primary_race():
    stats = RaceStats()
    stats.add_primary_race("Democrat")
    stats.add_primary_race("Democrat")
    stats.add_primary_race("Republican")
    assert stats.primary_races_by_party["Democrat"] == 2
    assert stats.primary_races_by_party["Republican"] == 1


def test_race_stats_merge_new_fields():
    stats1 = RaceStats()
    stats1.general_total_races = 5
    stats1.general_unopposed_by_party = {"Democrat": 3}
    stats1.primary_races_by_party = {"Democrat": 10}
    stats1.primary_unopposed_by_party = {"Democrat": 2}

    stats2 = RaceStats()
    stats2.general_total_races = 3
    stats2.general_unopposed_by_party = {"Democrat": 1, "Republican": 2}
    stats2.primary_races_by_party = {"Republican": 8}
    stats2.primary_unopposed_by_party = {"Republican": 1}

    stats1.merge(stats2)

    assert stats1.general_total_races == 8
    assert stats1.general_unopposed_by_party["Democrat"] == 4
    assert stats1.general_unopposed_by_party["Republican"] == 2
    assert stats1.primary_races_by_party["Democrat"] == 10
    assert stats1.primary_races_by_party["Republican"] == 8
    assert stats1.primary_unopposed_by_party["Democrat"] == 2
    assert stats1.primary_unopposed_by_party["Republican"] == 1
