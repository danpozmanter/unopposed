from bs4 import BeautifulSoup
from sources.ballotpedia import (
    _extract_district,
    _extract_party_from_header,
    _extract_names_from_cell,
    _urls,
)


def test_extract_district_statewide():
    assert _extract_district("anything", "US Senate") == "Statewide"
    assert _extract_district("anything", "Governor") == "Statewide"


def test_extract_district_numbered():
    assert _extract_district("District 5", "US House") == "District 5"
    assert _extract_district("District 12", "State House") == "District 12"
    assert _extract_district("district 3", "US House") == "District 3"


def test_extract_district_at_large():
    assert _extract_district("At-Large", "US House") == "At-Large"
    assert _extract_district("at large", "US House") == "At-Large"
    assert _extract_district("At Large", "US House") == "At-Large"


def test_extract_district_bare_number():
    assert _extract_district("5", "State House") == "District 5"
    assert _extract_district(" 12 ", "State House") == "District 12"


def test_extract_district_invalid():
    assert _extract_district("Something else", "US House") is None
    assert _extract_district("", "US House") is None


def test_extract_party_from_header():
    assert _extract_party_from_header("Democratic primary") == "Democrat"
    assert _extract_party_from_header("Republican Primary Election") == "Republican"
    assert _extract_party_from_header("Libertarian candidates") == "Libertarian"
    assert _extract_party_from_header("Green party primary") == "Green/Rainbow"
    assert _extract_party_from_header("Some other heading") is None


def test_extract_names_from_cell():
    html = '<td><a href="/John_Doe">John Doe</a></td>'
    cell = BeautifulSoup(html, "lxml").find("td")
    names = _extract_names_from_cell(cell)
    assert names == ["John Doe"]


def test_extract_names_from_cell_multiple():
    html = '<td><a href="/John_Doe">John Doe</a>, <a href="/Jane_Smith">Jane Smith</a></td>'
    cell = BeautifulSoup(html, "lxml").find("td")
    names = _extract_names_from_cell(cell)
    assert "John Doe" in names
    assert "Jane Smith" in names


def test_extract_names_from_cell_filters_bad_names():
    html = '<td><a href="/d">X</a><a href="/District_5">District 5</a><a href="/John_Doe">John Doe</a></td>'
    cell = BeautifulSoup(html, "lxml").find("td")
    names = _extract_names_from_cell(cell)
    assert names == ["John Doe"]


def test_extract_names_from_cell_cleans_incumbent():
    html = '<td><a href="/John_Doe">John Doe (i)</a></td>'
    cell = BeautifulSoup(html, "lxml").find("td")
    names = _extract_names_from_cell(cell)
    assert names == ["John Doe"]


def test_urls_includes_standard_offices():
    urls = _urls("California", "CA", 2026)
    assert "US Senate" in urls
    assert "US House" in urls
    assert "Governor" in urls
    assert "State Senate" in urls
    assert "State House" in urls


def test_urls_nebraska_unicameral():
    urls = _urls("Nebraska", "NE", 2026)
    assert "State Senate" not in urls
    assert "State House" not in urls


def test_urls_custom_lower_chamber():
    urls = _urls("California", "CA", 2026)
    assert "State_Assembly" in urls["State House"]

    urls = _urls("Virginia", "VA", 2026)
    assert "House_of_Delegates" in urls["State House"]
