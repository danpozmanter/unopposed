import re
import sys
import requests
from bs4 import BeautifulSoup
from data import (
    Race,
    RaceStats,
    STATE_NAMES,
    LOWER_CHAMBERS,
    UPPER_CHAMBERS,
    normalize_party,
)

BASE = "https://ballotpedia.org"
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_DISTRICT_RE = re.compile(r"District\s+(\d+)", re.I)
_CANCELED_RE = re.compile(r"primary\s+was\s+canceled", re.I)
_NAME_CLEAN_RE = re.compile(r"[\s*]+$|\s*\(i\)")
_PARTY_IN_TEXT_RE = re.compile(r"\((\w+(?:\s+\w+)?)\s+Party\)")


def scrape(state_code, year):
    state = STATE_NAMES.get(state_code)
    if not state:
        return [], RaceStats()
    session = requests.Session()
    session.headers["User-Agent"] = UA
    results = []
    stats = RaceStats()
    for office, url in _urls(state, state_code, year).items():
        print(f"  Fetching {office} from Ballotpedia...", file=sys.stderr)
        html = _fetch(session, url)
        if html:
            unopposed, office_stats = _parse(html, office, state_code)
            results.extend(unopposed)
            stats.merge(office_stats)
    return results, stats


def _urls(state, sc, year):
    s = state.replace(" ", "_")
    urls = {
        "US Senate": f"{BASE}/United_States_Senate_election_in_{s},_{year}",
        "US House": f"{BASE}/United_States_House_of_Representatives_elections_in_{s},_{year}",
        "Governor": f"{BASE}/{s}_gubernatorial_election,_{year}",
    }
    if sc not in UPPER_CHAMBERS:
        urls["State Senate"] = f"{BASE}/{s}_State_Senate_elections,_{year}"
    lower = LOWER_CHAMBERS.get(sc, "House_of_Representatives")
    if lower:
        urls["State House"] = f"{BASE}/{s}_{lower}_elections,_{year}"
    return urls


def _fetch(session, url):
    try:
        r = session.get(url, timeout=20)
        if r.status_code == 200:
            return r.text
        print(
            f"    {r.status_code} (may not be an election year for this office)",
            file=sys.stderr,
        )
        return None
    except requests.RequestException as e:
        print(f"    Network error: {e}", file=sys.stderr)
        return None


def _parse(html, office, state_code):
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    content = soup.find("div", class_="mw-parser-output") or soup
    results = []
    stats = RaceStats()
    table_results, table_stats = _parse_partisan_tables(content, office, state_code)
    results.extend(table_results)
    stats.merge(table_stats)
    section_results, section_stats = _parse_district_sections(
        content, office, state_code
    )
    results.extend(section_results)
    stats.merge(section_stats)
    return results, stats


# --- Strategy 1: candidateListTablePartisan tables (state legislature pages) ---


def _parse_partisan_tables(content, office, state_code):
    results = []
    stats = RaceStats()
    for table in content.find_all("table", class_="candidateListTablePartisan"):
        table_results, table_stats = _process_table(table, office, state_code)
        results.extend(table_results)
        stats.merge(table_stats)
    return results, stats


def _process_table(table, office, state_code):
    rows = table.find_all("tr")
    header_idx, party_cols = _find_header_row(rows)
    if header_idx is None or not party_cols:
        return [], RaceStats()

    title = rows[0].get_text(" ", strip=True).lower() if rows else ""
    is_general = "general" in title
    is_primary = "primary" in title and "runoff" not in title

    results = []
    stats = RaceStats()
    for row in rows[header_idx + 1 :]:
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        district = _extract_district(cells[0].get_text(strip=True), office)
        if not district:
            continue
        row_results, row_stats = _analyze_table_row(
            cells, party_cols, district, office, state_code, is_general, is_primary
        )
        results.extend(row_results)
        stats.merge(row_stats)
    return results, stats


def _find_header_row(rows):
    for i, row in enumerate(rows):
        cells = row.find_all(["th", "td"])
        texts = [c.get_text(strip=True).lower() for c in cells]
        if any(t in ("office", "district") for t in texts):
            party_cols = {}
            for j, t in enumerate(texts):
                if "democrat" in t:
                    party_cols["Democrat"] = j
                elif "republican" in t:
                    party_cols["Republican"] = j
                elif "libertarian" in t:
                    party_cols["Libertarian"] = j
                elif "green" in t:
                    party_cols["Green/Rainbow"] = j
                elif "other" in t or "independent" in t:
                    party_cols["Other"] = j
            return i, party_cols
    return None, {}


def _analyze_table_row(
    cells, party_cols, district, office, state_code, is_general, is_primary
):
    results = []
    stats = RaceStats()
    candidates_by_party = {}

    for party, col_idx in party_cols.items():
        if col_idx >= len(cells):
            continue
        cell = cells[col_idx]
        cell_text = cell.get_text(" ", strip=True)
        if _CANCELED_RE.search(cell_text):
            continue
        names = _extract_names_from_cell(cell)
        if names:
            candidates_by_party[party] = names

    all_candidates = [(n, p) for p, ns in candidates_by_party.items() for n in ns]

    if is_general:
        stats.add_race(list(candidates_by_party.keys()) if candidates_by_party else [])
        if len(all_candidates) == 1:
            name, party = all_candidates[0]
            results.append(
                _new_race(state_code, office, district, name, party, "General")
            )

    if is_primary:
        for party, names in candidates_by_party.items():
            if len(names) == 1:
                results.append(
                    _new_race(state_code, office, district, names[0], party, "Primary")
                )
    return results, stats


def _extract_names_from_cell(cell):
    names = []
    for link in cell.find_all("a"):
        text = link.get_text(strip=True)
        cleaned = _NAME_CLEAN_RE.sub("", text).strip()
        if len(cleaned) < 3 or " " not in cleaned:
            continue
        if not re.match(r"^[A-Z]", cleaned):
            continue
        skip = (
            "District",
            "United",
            "State",
            "House",
            "Senate",
            "Republican",
            "Democrat",
            "The ",
            "Primary",
            "General",
            "Libertarian",
            "Green",
            "Independent",
        )
        if not any(cleaned.startswith(w) for w in skip):
            names.append(cleaned)
    return names


# --- Strategy 2: heading-based district sections (US House/Senate/Gov pages) ---


def _parse_district_sections(content, office, state_code):
    results = []
    stats = RaceStats()
    sections = _collect_district_sections(content, office)

    for district, elements in sections:
        general_candidates = []
        primary_candidates_by_party = {}
        current_section = None

        for elem in elements:
            text = elem.get_text(" ", strip=True)
            lower_text = text.lower()

            if elem.name in ("h4", "p"):
                new_section = _detect_section(elem, lower_text, text)
                if new_section is not None:
                    current_section = new_section
                    continue

            if current_section in ("skip", "minor", None):
                continue

            if elem.name == "ul":
                _collect_ul_candidates(
                    elem,
                    current_section,
                    general_candidates,
                    primary_candidates_by_party,
                )
            elif elem.name == "div" and "votebox" in " ".join(elem.get("class", [])):
                _collect_votebox_candidates(
                    elem,
                    current_section,
                    general_candidates,
                    primary_candidates_by_party,
                )

        all_primary = [
            (n, p) for p, ns in primary_candidates_by_party.items() for n in ns
        ]

        all_parties = set()
        for _, party in general_candidates:
            all_parties.add(party)
        for party in primary_candidates_by_party.keys():
            all_parties.add(party)

        if all_parties:
            stats.add_race(list(all_parties))

        if len(general_candidates) == 1:
            name, party = general_candidates[0]
            results.append(
                _new_race(state_code, office, district, name, party, "General")
            )

        for party, names in primary_candidates_by_party.items():
            if len(names) == 1:
                results.append(
                    _new_race(state_code, office, district, names[0], party, "Primary")
                )

        if not general_candidates and len(all_primary) == 1:
            name, party = all_primary[0]
            results.append(
                _new_race(state_code, office, district, name, party, "General")
            )

    return results, stats


def _detect_section(elem, lower_text, text):
    if elem.name == "h4":
        if "general election" in lower_text:
            return "general"
        if "primary" in lower_text and "withdrawn" not in lower_text:
            return ("primary", _extract_party_from_header(text))
        if "withdrawn" in lower_text or "disqualified" in lower_text:
            return "skip"
        return None
    if "general election" in lower_text and "candidate" in lower_text:
        return "general"
    if "primary candidate" in lower_text or "primary election candidate" in lower_text:
        return ("primary", _extract_party_from_header(text))
    if "minor party" in lower_text or "convention candidate" in lower_text:
        return "minor"
    if "did not make" in lower_text or "withdrawn" in lower_text:
        return "skip"
    return None


def _collect_ul_candidates(ul, section, general_candidates, primary_by_party):
    for li in ul.find_all("li", recursive=False):
        cand = _parse_candidate_li(li)
        if not cand:
            continue
        name, party = cand
        if section == "general":
            general_candidates.append((name, party))
        elif isinstance(section, tuple) and section[0] == "primary":
            p = section[1] or party
            primary_by_party.setdefault(p, []).append(name)


def _collect_votebox_candidates(div, section, general_candidates, primary_by_party):
    for row in div.find_all("tr"):
        row_text = row.get_text(" ", strip=True).lower()
        if "write-in" in row_text or "total" in row_text:
            continue
        if "incumbent" in row_text and "bolded" in row_text:
            continue
        if "candidate" in row_text and "%" in row_text and "votes" in row_text:
            continue
        cells = row.find_all("td")
        if len(cells) < 1:
            continue
        link = row.find("a")
        if not link:
            continue
        href = link.get("href", "")
        if href.startswith("mailto:"):
            continue
        if "ballotpedia.org" not in href and "/wiki/" not in href:
            continue
        name = _NAME_CLEAN_RE.sub("", link.get_text(strip=True)).strip()
        if len(name) < 3 or " " not in name:
            continue
        full_row_text = row.get_text(" ", strip=True)
        m = _PARTY_IN_TEXT_RE.search(full_row_text)
        party = m.group(1) if m else "Unknown"
        if section == "general":
            general_candidates.append((name, normalize_party(party)))
        elif isinstance(section, tuple) and section[0] == "primary":
            p = section[1] or normalize_party(party)
            primary_by_party.setdefault(p, []).append(name)


def _collect_district_sections(content, office):
    sections = []
    if office in ("US Senate", "Governor"):
        in_candidates_section = False
        elements = []
        for child in content.children:
            tag = getattr(child, "name", None)
            if tag == "h2":
                heading = child.get_text(strip=True).lower()
                if "candidate" in heading and "result" in heading:
                    in_candidates_section = True
                    continue
                if in_candidates_section:
                    break
            if in_candidates_section and tag in ("p", "ul", "div", "dl", "h4"):
                elements.append(child)
        if elements:
            sections.append(("Statewide", elements))
        return sections

    current_district = None
    current_elements = []
    for child in content.children:
        tag = getattr(child, "name", None)
        if tag in ("h3",):
            if current_district and current_elements:
                sections.append((current_district, current_elements))
            heading = child.get_text(strip=True)
            m = _DISTRICT_RE.search(heading)
            current_district = f"District {m.group(1)}" if m else None
            if not current_district and re.search(r"at.?large", heading, re.I):
                current_district = "At-Large"
            current_elements = []
        elif current_district and tag in ("p", "ul", "div", "dl"):
            current_elements.append(child)
    if current_district and current_elements:
        sections.append((current_district, current_elements))
    return sections


def _parse_candidate_li(li):
    link = li.find("a")
    if not link:
        return None
    name = _NAME_CLEAN_RE.sub("", link.get_text(strip=True)).strip()
    if len(name) < 3 or " " not in name:
        return None
    li_text = li.get_text(" ", strip=True)
    m = _PARTY_IN_TEXT_RE.search(li_text)
    party = m.group(1) if m else "Unknown"
    return name, party


def _extract_party_from_header(text):
    if "democrat" in text.lower():
        return "Democrat"
    if "republican" in text.lower():
        return "Republican"
    if "libertarian" in text.lower():
        return "Libertarian"
    if "green" in text.lower():
        return "Green/Rainbow"
    return None


def _extract_district(text, office):
    if office in ("US Senate", "Governor"):
        return "Statewide"
    m = _DISTRICT_RE.search(text)
    if m:
        return f"District {m.group(1)}"
    if re.search(r"at.?large", text, re.I):
        return "At-Large"
    if re.match(r"^\d+$", text.strip()):
        return f"District {text.strip()}"
    m = re.match(r"^(\d+)(?:st|nd|rd|th)\s+", text, re.I)
    if m:
        return text.strip()
    if "district" in text.lower():
        return text.strip()
    return None


def _new_race(state_code, office, district, candidate, party, unopposed_in):
    return Race(
        state=state_code,
        office=office,
        district=district,
        candidate=candidate,
        party=normalize_party(party),
        unopposed_in=unopposed_in,
        source="Ballotpedia",
    )
