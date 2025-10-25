"""
Dropdown Data Provider

Provides static data for dropdown menus including bands, modes, countries, states, and frequencies.
"""

from typing import Dict, List, Tuple


class DropdownData:
    """Provides data for all dropdown menus in the application"""

    # HAM RADIO BANDS (in MHz)
    BANDS = [
        ("160M", 1.8),
        ("80M", 3.5),
        ("60M", 5.3),
        ("40M", 7.0),
        ("30M", 10.1),
        ("20M", 14.0),
        ("17M", 18.0),
        ("15M", 21.0),
        ("12M", 24.9),
        ("10M", 28.0),
        ("6M", 50.0),
        ("2M", 144.0),
        ("70cm", 432.0),
        ("33cm", 902.0),
        ("23cm", 1240.0),
    ]

    # OPERATING MODES
    MODES = [
        "CW",
        "SSB",
        "FM",
        "AM",
        "RTTY",
        "PSK31",
        "PSK63",
        "PSKFSK8",
        "MFSK",
        "OLIVIA",
        "HELL",
        "JT65",
        "JT9",
        "JT4",
        "ISCAT",
        "MSK144",
        "WSPR",
        "FSK441",
        "4A",
        "8FSK",
        "AFSK1200",
        "ATV",
        "C4FM",
        "DSTAR",
        "DIGI",
        "DIGITALVOICE",
        "DCN",
        "ARDOP",
        "DOMINO",
        "PAX",
        "PAC",
        "PACKET",
        "AMTOR",
        "ASCI",
        "PACTOR",
        "MT63",
    ]

    # US STATES
    US_STATES = [
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    ]

    # COUNTRIES (DXCC Entities - Common ones)
    COUNTRIES = [
        "United States",
        "Canada",
        "Mexico",
        "Bahamas",
        "Bermuda",
        "Puerto Rico",
        "Virgin Islands",
        "Cayman Islands",
        "Jamaica",
        "Turks and Caicos Islands",
        "Belize",
        "Costa Rica",
        "El Salvador",
        "Guatemala",
        "Honduras",
        "Nicaragua",
        "Panama",
        "Argentina",
        "Bolivia",
        "Brazil",
        "Chile",
        "Colombia",
        "Ecuador",
        "Guyana",
        "Paraguay",
        "Peru",
        "Suriname",
        "Uruguay",
        "Venezuela",
        "United Kingdom",
        "Ireland",
        "France",
        "Spain",
        "Portugal",
        "Germany",
        "Netherlands",
        "Belgium",
        "Luxembourg",
        "Switzerland",
        "Austria",
        "Italy",
        "Greece",
        "Poland",
        "Czechia",
        "Slovakia",
        "Hungary",
        "Romania",
        "Bulgaria",
        "Croatia",
        "Serbia",
        "Bosnia and Herzegovina",
        "Slovenia",
        "Ukraine",
        "Russia",
        "Belarus",
        "Lithuania",
        "Latvia",
        "Estonia",
        "Finland",
        "Sweden",
        "Norway",
        "Denmark",
        "Iceland",
        "Turkey",
        "Israel",
        "Egypt",
        "Libya",
        "Tunisia",
        "Algeria",
        "Morocco",
        "South Africa",
        "Zimbabwe",
        "Kenya",
        "Tanzania",
        "Uganda",
        "Nigeria",
        "Ghana",
        "Cameroon",
        "Zambia",
        "Malawi",
        "Madagascar",
        "Mauritius",
        "India",
        "Pakistan",
        "Bangladesh",
        "Nepal",
        "Sri Lanka",
        "Thailand",
        "Malaysia",
        "Singapore",
        "Indonesia",
        "Philippines",
        "Vietnam",
        "Cambodia",
        "Laos",
        "Myanmar",
        "China",
        "Hong Kong",
        "Taiwan",
        "Japan",
        "South Korea",
        "North Korea",
        "Mongolia",
        "Australia",
        "New Zealand",
        "Fiji",
        "Papua New Guinea",
        "Samoa",
        "Kiribati",
        "Tonga",
        "Nauru",
        "Tuvalu",
        "Marshall Islands",
        "Micronesia",
        "Palau",
    ]

    # FREQUENCY RANGES FOR EACH BAND (MHz)
    BAND_FREQUENCIES: Dict[str, Tuple[float, float]] = {
        "160M": (1.8, 2.0),
        "80M": (3.5, 4.0),
        "60M": (5.3, 5.4),
        "40M": (7.0, 7.3),
        "30M": (10.1, 10.15),
        "20M": (14.0, 14.35),
        "17M": (18.0, 18.168),
        "15M": (21.0, 21.45),
        "12M": (24.89, 24.99),
        "10M": (28.0, 29.7),
        "6M": (50.0, 54.0),
        "2M": (144.0, 148.0),
        "70cm": (432.0, 450.0),
        "33cm": (902.0, 928.0),
        "23cm": (1240.0, 1300.0),
    }

    @classmethod
    def get_bands(cls) -> List[str]:
        """Get list of band names"""
        return [band[0] for band in cls.BANDS]

    @classmethod
    def get_band_center_frequency(cls, band: str) -> float:
        """Get center frequency for a band in MHz"""
        for band_name, freq in cls.BANDS:
            if band_name == band:
                return freq
        return 0.0

    @classmethod
    def get_band_range(cls, band: str) -> Tuple[float, float]:
        """Get frequency range for a band in MHz"""
        return cls.BAND_FREQUENCIES.get(band, (0.0, 0.0))

    @classmethod
    def get_modes(cls) -> List[str]:
        """Get list of operating modes"""
        return sorted(cls.MODES)

    @classmethod
    def get_us_states(cls) -> List[str]:
        """Get list of US states"""
        return cls.US_STATES

    @classmethod
    def get_countries(cls) -> List[str]:
        """Get list of countries"""
        return sorted(cls.COUNTRIES)

    @classmethod
    def get_frequencies_for_band(cls, band: str) -> List[float]:
        """Get common frequencies for a band"""
        if band not in cls.BAND_FREQUENCIES:
            return []

        min_freq, max_freq = cls.BAND_FREQUENCIES[band]

        # Generate frequencies at 0.1 MHz intervals
        frequencies = []
        freq = min_freq
        while freq <= max_freq:
            frequencies.append(round(freq, 2))
            freq += 0.1

        return frequencies
