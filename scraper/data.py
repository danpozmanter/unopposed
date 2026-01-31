from dataclasses import dataclass, asdict

STATE_NAMES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",
}

UPPER_CHAMBERS = {"NE"}

LOWER_CHAMBERS = {
    "CA": "State_Assembly",
    "MD": "House_of_Delegates",
    "NE": None,
    "NJ": "General_Assembly",
    "NV": "State_Assembly",
    "NY": "State_Assembly",
    "VA": "House_of_Delegates",
    "WI": "State_Assembly",
    "WV": "House_of_Delegates",
}


@dataclass
class Race:
    state: str
    office: str
    district: str
    candidate: str
    party: str
    unopposed_in: str
    source: str

    def key(self):
        return (self.state, self.office, self.district, self.candidate)

    def to_dict(self):
        return asdict(self)


_PARTY_MAP = {
    "democratic": "Democrat",
    "democrat": "Democrat",
    "dem": "Democrat",
    "republican": "Republican",
    "rep": "Republican",
    "gop": "Republican",
    "libertarian": "Libertarian",
    "lib": "Libertarian",
    "green": "Green/Rainbow",
    "green/rainbow": "Green/Rainbow",
    "independent": "Independent",
    "ind": "Independent",
}


def normalize_party(party):
    return _PARTY_MAP.get(party.strip().lower(), party.strip())


def _merge_unopposed(existing, new):
    stages = set(existing.split(" & ")) | set(new.split(" & "))
    return " & ".join(s for s in ("Primary", "General") if s in stages)


def deduplicate(results):
    seen = {}
    out = []
    for r in results:
        k = r.key()
        if k in seen:
            merged = _merge_unopposed(seen[k].unopposed_in, r.unopposed_in)
            if merged:
                seen[k].unopposed_in = merged
        else:
            seen[k] = r
            out.append(r)
    return out
