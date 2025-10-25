"""
Database constants for SKCC and ham radio logging
"""

# SKCC Key Types (mechanical only)
KEY_TYPES = {
    "STRAIGHT": "Straight Key",
    "BUG": "Semi-Automatic Key (Bug)",
    "SIDESWIPER": "Sideswiper (Cootie)",
}

# Ordered list for dropdowns
KEY_TYPE_CHOICES = [
    ("STRAIGHT", "Straight Key"),
    ("BUG", "Semi-Automatic Key (Bug)"),
    ("SIDESWIPER", "Sideswiper (Cootie)"),
]

# Default key type
DEFAULT_KEY_TYPE = "STRAIGHT"

# Key type descriptions for tooltips/help
KEY_TYPE_DESCRIPTIONS = {
    "STRAIGHT": (
        "Traditional mechanical key with spring return. "
        "Requires manual creation of both dots and dashes. "
        "Most skill required, most authentic SKCC experience."
    ),
    "BUG": (
        "Semi-automatic key (bug) with automatic dot generation. "
        "Horizontal paddle creates dots via mechanical oscillation. "
        "Manual dashes via normal lever motion. "
        "Intermediate skill level, popular for SKCC."
    ),
    "SIDESWIPER": (
        "Horizontal lever key (cootie) used primarily by experienced operators. "
        "Creates dots and dashes through side-to-side lever motion. "
        "Advanced technique, requires practice but very efficient."
    ),
}

# Valid modes for SKCC
SKCC_MODES = ["CW"]

# Operating modes
OPERATING_MODES = [
    "CW",      # Morse code (SKCC only uses this)
    "SSB",     # Single-sideband (voice)
    "FM",      # Frequency modulation
    "RTTY",    # Radio teletype
    "PSK",     # Phase-shift keying
    "FT8",     # Digital mode
    "DIGI",    # Digital (generic)
]

# SKCC Award Types (from handbook)
SKCC_AWARDS = {
    # Tiered Endorsements
    "CENTURION": {
        "name": "Centurion",
        "abbreviation": "C",
        "requirement": "Work 100 other SKCC members",
        "type": "endorsement",
        "base_contacts": 100,
    },
    "TRIBUNE": {
        "name": "Tribune",
        "abbreviation": "T",
        "requirement": "Work 50 other C, T, or S members",
        "type": "endorsement",
        "prerequisite": "CENTURION",
        "base_contacts": 50,
    },
    "SENATOR": {
        "name": "Senator",
        "abbreviation": "S",
        "requirement": "Work 200 additional Tribune or Senator members",
        "type": "endorsement",
        "prerequisite": "TRIBUNE_TX8",
        "base_contacts": 200,
        "total_contacts": 600,
    },
    # Geographic Awards
    "WAS": {
        "name": "Worked All States",
        "abbreviation": "WAS",
        "requirement": "Work SKCC members in all 50 US states",
        "type": "geographic",
    },
    "WAC": {
        "name": "Worked All Continents",
        "abbreviation": "WAC",
        "requirement": "Work SKCC members in 6 continental regions",
        "type": "geographic",
    },
    "CANADIAN_MAPLE": {
        "name": "Canadian Maple",
        "abbreviation": "CM",
        "requirement": "Work SKCC members in 10 Canadian provinces/territories",
        "type": "geographic",
    },
    "DXC": {
        "name": "DX Contacts",
        "abbreviation": "DXC",
        "requirement": "Work SKCC members in other countries (multiples of 25)",
        "type": "geographic",
    },
    # Operating Skill Awards
    "QRP": {
        "name": "QRP",
        "abbreviation": "QRP",
        "requirement": "Low power SKCC contacts (1-5 watts)",
        "type": "skill",
    },
    "QRP_MPW": {
        "name": "QRP Miles Per Watt",
        "abbreviation": "MPW",
        "requirement": "Contacts attaining 1,000 miles-per-watt and multiples",
        "type": "skill",
    },
    "TRIPLE_KEY": {
        "name": "Triple Key",
        "abbreviation": "TK",
        "requirement": "300 QSOs demonstrating proficiency with 3 SKCC key types",
        "type": "skill",
        "contacts_required": 300,
        "key_types_required": 3,
    },
    "PFX": {
        "name": "Call Sign Prefix",
        "abbreviation": "PFX",
        "requirement": "Points system award for unique call sign prefixes",
        "type": "skill",
    },
    # Duration Awards
    "RAGCHEW": {
        "name": "Ragchew",
        "abbreviation": "RC",
        "requirement": "QSOs with SKCC members of 30+ minutes duration",
        "type": "duration",
        "min_duration_minutes": 30,
    },
    "MARATHON": {
        "name": "Marathon",
        "abbreviation": "MAR",
        "requirement": "100 QSOs, each of 60+ minutes duration",
        "type": "duration",
        "contacts_required": 100,
        "min_duration_minutes": 60,
    },
}

# Band definitions
BANDS = [
    ("160M", "160 Meters"),
    ("80M", "80 Meters"),
    ("60M", "60 Meters"),
    ("40M", "40 Meters"),
    ("30M", "30 Meters"),
    ("20M", "20 Meters"),
    ("17M", "17 Meters"),
    ("15M", "15 Meters"),
    ("12M", "12 Meters"),
    ("10M", "10 Meters"),
    ("6M", "6 Meters"),
    ("4M", "4 Meters"),
    ("2M", "2 Meters"),
    ("1.25M", "1.25 Meters"),
    ("70CM", "70 Centimeters"),
    ("33CM", "33 Centimeters"),
    ("23CM", "23 Centimeters"),
]
