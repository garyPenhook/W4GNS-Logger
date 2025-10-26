"""
SKCC WAC Award - Worked All Continents

The WAC Award recognizes international two-way amateur radio communication
among SKCC members. Applicants must document contacts with members in all
six continental areas of the world from their own continental location.

Six Continental Areas (IARU standards):
- North America
- South America
- Oceania (Australia, Pacific)
- Asia
- Europe
- Africa

Rules:
- Both operators must hold SKCC membership at time of contact
- CW mode exclusively
- Mechanical key policy: straight key, bug, or side swiper only
- Contacts made on or after October 9, 2011
- Contacts required with members in all 6 continents
- Band endorsements available (per band worked)
- QRP endorsement available (≤5W power)
"""

import logging
from typing import Dict, List, Any, Set
from sqlalchemy.orm import Session

from src.awards.base import AwardProgram

logger = logging.getLogger(__name__)

# DXCC to Continent Mapping
# Maps callsign prefixes and DXCC entities to their continental regions
DXCC_TO_CONTINENT: Dict[str, str] = {
    # North America (NA)
    'VE': 'NA', 'VY': 'NA', 'XE': 'NA', 'K': 'NA', 'W': 'NA', 'N': 'NA',
    'JA': 'NA', 'KP': 'NA', 'KH': 'NA', 'WP': 'NA', 'WL': 'NA',
    'AA': 'NA', 'AB': 'NA', 'AC': 'NA', 'AD': 'NA', 'AE': 'NA', 'AF': 'NA', 'AG': 'NA',

    # South America (SA)
    'PY': 'SA', 'ZY': 'SA', 'PZ': 'SA', 'PJ': 'SA', 'YV': 'SA', 'HJ': 'SA', 'HC': 'SA',
    'OA': 'SA', 'CP': 'SA', 'LU': 'SA', 'CE': 'SA', 'CX': 'SA', 'FY': 'SA', 'SR': 'SA',

    # Europe (EU)
    'PA': 'EU', 'PB': 'EU', 'G': 'EU', 'M': 'EU', 'GW': 'EU', 'GD': 'EU', 'GI': 'EU',
    'EI': 'EU', 'IS': 'EU', 'LA': 'EU', 'LB': 'EU', 'OZ': 'EU', 'SM': 'EU', 'SF': 'EU',
    'OH': 'EU', 'SN': 'EU', 'SP': 'EU', 'OK': 'EU', 'OM': 'EU', 'HA': 'EU', 'HV': 'EU',
    'I': 'EU', 'IA': 'EU', 'IB': 'EU', 'IC': 'EU', 'ID': 'EU',
    'F': 'EU', 'FA': 'EU', 'FB': 'EU', 'FC': 'EU', 'FD': 'EU', 'FE': 'EU', 'FF': 'EU',
    'HB': 'EU', 'HB9': 'EU', 'HE': 'EU', 'DL': 'EU', 'DA': 'EU', 'DB': 'EU', 'DC': 'EU', 'DD': 'EU', 'DE': 'EU', 'DF': 'EU',
    'EA': 'EU', 'EB': 'EU', 'EC': 'EU', 'ED': 'EU', 'EE': 'EU', 'EF': 'EU',
    'CT': 'EU', 'CU': 'EU', 'LX': 'EU', 'ON': 'EU', 'OA': 'EU',
    'YU': 'EU', 'YZ': 'EU', 'Z3': 'EU', 'S5': 'EU', 'S9': 'EU', 'TA': 'EU', 'TC': 'EU', 'TD': 'EU',
    'SV': 'EU', 'SX': 'EU', 'J4': 'EU', 'YO': 'EU', 'YR': 'EU', 'UR': 'EU', 'US': 'EU',
    'RA': 'EU', 'RB': 'EU', 'RC': 'EU', 'RD': 'EU', 'RE': 'EU', 'RF': 'EU', 'RG': 'EU', 'RH': 'EU',
    'RI': 'EU', 'RJ': 'EU', 'RK': 'EU', 'RL': 'EU', 'RM': 'EU', 'RN': 'EU', 'RO': 'EU', 'RP': 'EU',
    'RR': 'EU', 'RS': 'EU', 'RT': 'EU', 'RU': 'EU', 'RV': 'EU', 'RW': 'EU',

    # Africa (AF)
    'ZS': 'AF', 'ZT': 'AF', 'ZU': 'AF', 'ZV': 'AF', 'ZW': 'AF', 'ZX': 'AF', 'ZY': 'AF', 'ZZ': 'AF',
    'CN': 'AF', 'D2': 'AF', 'D3': 'AF', 'D4': 'AF', 'D5': 'AF', 'D6': 'AF',
    'EA9': 'AF', 'SU': 'AF', 'SV5': 'AF', 'S0': 'AF', '7O': 'AF',
    '5A': 'AF', '5B': 'AF', '5H': 'AF', '5I': 'AF', '5J': 'AF', '5K': 'AF', '5L': 'AF',
    '5N': 'AF', '5R': 'AF', '5S': 'AF', '5T': 'AF', '5U': 'AF', '5V': 'AF', '5W': 'AF',
    '5X': 'AF', '5Z': 'AF', '6O': 'AF', '6W': 'AF', '6Y': 'AF', '7A': 'AF',
    '8Q': 'AF', '9G': 'AF', '9H': 'AF', '9J': 'AF', '9K': 'AF', '9L': 'AF', '9M': 'AF',
    '9U': 'AF', '9X': 'AF',

    # Asia (AS)
    'JA': 'AS', 'JE': 'AS', 'JF': 'AS', 'JG': 'AS', 'JH': 'AS', 'JI': 'AS', 'JJ': 'AS', 'JK': 'AS',
    'JL': 'AS', 'JM': 'AS', 'JN': 'AS', 'JO': 'AS', 'JP': 'AS', 'JQ': 'AS', 'JR': 'AS', 'JS': 'AS',
    'JT': 'AS', 'JU': 'AS', 'JV': 'AS', 'JW': 'AS', 'JX': 'AS', 'JY': 'AS', 'JZ': 'AS',
    'BA': 'AS', 'BY': 'AS', 'BZ': 'AS', 'AB': 'AS', 'AC': 'AS', 'BS': 'AS',
    'BD': 'AS', 'BE': 'AS', 'BF': 'AS', 'BG': 'AS', 'BH': 'AS', 'BI': 'AS', 'BJ': 'AS', 'BK': 'AS',
    'BL': 'AS', 'BM': 'AS', 'BN': 'AS', 'BP': 'AS', 'BQ': 'AS', 'BR': 'AS', 'BT': 'AS', 'BU': 'AS',
    'BV': 'AS', 'BW': 'AS',
    'XS': 'AS', 'XV': 'AS', 'XW': 'AS', 'XX': 'AS', 'XZ': 'AS',
    'HS': 'AS', 'HZ': 'AS', '9K': 'AS', 'A4': 'AS', 'A6': 'AS', 'A7': 'AS', 'A9': 'AS',
    'VU': 'AS', 'VT': 'AS', 'S2': 'AS', 'S3': 'AS', 'S6': 'AS', 'S7': 'AS', 'S8': 'AS', 'S9': 'AS',
    '4S': 'AS', '4W': 'AS', 'BV': 'AS', 'BX': 'AS', 'BY': 'AS',
    'AP': 'AS', 'AQ': 'AS', 'AR': 'AS', 'AS': 'AS', 'AT': 'AS', 'AU': 'AS',
    '3V': 'AS', '3W': 'AS', '3X': 'AS', 'HL': 'AS', 'P2': 'AS', 'P3': 'AS', 'P4': 'AS', 'P5': 'AS',
    'RP': 'AS', 'R2': 'AS', 'R3': 'AS', 'R4': 'AS', 'R5': 'AS', 'R6': 'AS', 'R7': 'AS', 'R8': 'AS', 'R9': 'AS',
    '4K': 'AS', '4L': 'AS', '4M': 'AS', '4N': 'AS', '4O': 'AS', '4P': 'AS',

    # Oceania (OC)
    'VK': 'OC', 'VH': 'OC', 'VI': 'OC', 'VJ': 'OC', 'VL': 'OC', 'VM': 'OC', 'VN': 'OC', 'VO': 'OC', 'VP': 'OC',
    'VQ': 'OC', 'VR': 'OC', 'VS': 'OC', 'VT': 'OC', 'VU': 'OC', 'VV': 'OC', 'VW': 'OC', 'VX': 'OC', 'VY': 'OC', 'VZ': 'OC',
    'ZK': 'OC', 'ZL': 'OC', 'ZM': 'OC', 'P2': 'OC', 'P3': 'OC', 'P4': 'OC', 'P5': 'OC',
    '3D': 'OC', '3Y': 'OC', 'FK': 'OC', 'FO': 'OC', 'FP': 'OC', 'FR': 'OC', 'FT': 'OC', 'FW': 'OC', 'FX': 'OC',
    'H4': 'OC', 'KH0': 'OC', 'KH1': 'OC', 'KH2': 'OC', 'KH3': 'OC', 'KH4': 'OC', 'KH5': 'OC', 'KH6': 'OC', 'KH7': 'OC', 'KH8': 'OC', 'KH9': 'OC',
    'WP': 'OC', 'WH': 'OC', 'C2': 'OC', 'DU': 'OC', 'DX': 'OC', 'A2': 'OC', 'A3': 'OC', 'A5': 'OC',
    'JD': 'OC', 'JE': 'OC', 'JF': 'OC', 'JG': 'OC', 'JI': 'OC',
    'N0': 'OC', 'P9': 'OC', 'T2': 'OC', 'T3': 'OC', 'T4': 'OC', 'T5': 'OC', 'T6': 'OC', 'T7': 'OC', 'T8': 'OC', 'T9': 'OC',
    'T32': 'OC', 'T33': 'OC', 'T34': 'OC', 'T35': 'OC',
    'V2': 'OC', 'V3': 'OC', 'V4': 'OC', 'V5': 'OC', 'V6': 'OC', 'V7': 'OC',
    'XF': 'OC', 'XG': 'OC', 'XH': 'OC',
    'YB': 'OC', 'YC': 'OC',
}


class WACAward(AwardProgram):
    """SKCC WAC Award - Worked All Continents"""

    def __init__(self, db: Session):
        """
        Initialize WAC award

        Args:
            db: SQLAlchemy database session
        """
        super().__init__(name="WAC Award", program_id="SKCC_WAC")
        self.db = db
        # WAC effective date: October 9, 2011
        self.wac_effective_date_str = "20111009"

        # Continental regions
        self.continents = {
            'NA': 'North America',
            'SA': 'South America',
            'EU': 'Europe',
            'AF': 'Africa',
            'AS': 'Asia',
            'OC': 'Oceania',
        }

    def validate(self, contact: Dict[str, Any]) -> bool:
        """
        Check if a contact qualifies for WAC award

        Requirements:
        - CW mode only
        - SKCC number present on both sides
        - Mechanical key required (STRAIGHT, BUG, or SIDESWIPER)
        - Contact date on or after October 9, 2011
        - Remote station must have valid callsign with continent mapping
        - Both operators must be SKCC members

        Args:
            contact: Contact record dictionary

        Returns:
            True if contact qualifies for WAC award
        """
        # Must be CW mode
        if contact.get('mode', '').upper() != 'CW':
            logger.debug("Contact not in CW mode for WAC")
            return False

        # Must have SKCC number
        if not contact.get('skcc_number'):
            logger.debug("Contact missing SKCC number for WAC")
            return False

        # CRITICAL RULE: Must have valid mechanical key type (STRAIGHT, BUG, or SIDESWIPER)
        key_type = contact.get('key_type', '').upper()
        if key_type not in ['STRAIGHT', 'BUG', 'SIDESWIPER']:
            logger.debug(f"Invalid or missing key type for WAC: {key_type}")
            return False

        # Get contact date for date-based validations
        qso_date = contact.get('qso_date', '')

        # Check contact date (must be on/after October 9, 2011)
        if qso_date and qso_date < self.wac_effective_date_str:
            logger.debug(f"Contact before WAC effective date: {qso_date}")
            return False

        # Must have extractable continent from callsign
        callsign = contact.get('callsign', '').upper().strip()
        continent = self._get_continent_from_callsign(callsign)
        if not continent:
            logger.debug(f"Cannot determine continent for callsign: {callsign}")
            return False

        return True

    def _get_continent_from_callsign(self, callsign: str) -> str:
        """
        Get continent from callsign using DXCC prefix mapping

        Args:
            callsign: Callsign string

        Returns:
            Continent code (NA, SA, EU, AF, AS, OC) or empty string if unmapped
        """
        if not callsign:
            return ""

        callsign = callsign.upper().strip()

        # Handle "/" notation - extract the main part with numbers
        if "/" in callsign:
            parts = callsign.split("/")
            # Find the part that looks like a callsign (has numbers)
            for part in parts:
                if any(c.isdigit() for c in part):
                    callsign = part
                    break

        # Extract prefix (letters and first numbers)
        prefix = ""
        for char in callsign:
            if char.isalnum():
                prefix += char
            else:
                break

        # Try to match exact prefix first, then partial
        if prefix in DXCC_TO_CONTINENT:
            return DXCC_TO_CONTINENT[prefix]

        # Try 2-letter prefix
        if len(prefix) >= 2:
            prefix_2 = prefix[:2]
            if prefix_2 in DXCC_TO_CONTINENT:
                return DXCC_TO_CONTINENT[prefix_2]

        # Try 3-letter prefix (for some special cases like KH0, KH1, etc.)
        if len(prefix) >= 3:
            prefix_3 = prefix[:3]
            if prefix_3 in DXCC_TO_CONTINENT:
                return DXCC_TO_CONTINENT[prefix_3]

        return ""

    def calculate_progress(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate WAC award progress

        Tracks which continents have been worked via contacts with SKCC members
        from each continent.

        Args:
            contacts: List of contact records

        Returns:
            {
                'current': int,              # Number of continents worked
                'required': int,             # 6 (all continents)
                'achieved': bool,            # True if all 6 continents worked
                'progress_pct': float,       # Percentage (0-100)
                'level': str,                # "WAC" or "Not Yet"
                'continents_worked': list,   # List of worked continent codes
                'continent_details': dict,   # Per-continent contact counts
                'band_details': dict,        # Contacts per band per continent
            }
        """
        # Track continents worked and contact details
        continents_worked: Set[str] = set()
        continent_details: Dict[str, int] = {code: 0 for code in self.continents.keys()}
        band_details: Dict[str, Dict[str, int]] = {
            code: {} for code in self.continents.keys()
        }

        for contact in contacts:
            if self.validate(contact):
                callsign = contact.get('callsign', '').upper().strip()
                continent = self._get_continent_from_callsign(callsign)

                if continent in self.continents:
                    continents_worked.add(continent)
                    continent_details[continent] += 1

                    # Track by band
                    band = contact.get('band', 'Unknown').upper()
                    if band not in band_details[continent]:
                        band_details[continent][band] = 0
                    band_details[continent][band] += 1

        # Determine if award is achieved (all 6 continents worked)
        achieved = len(continents_worked) >= 6
        current_count = len(continents_worked)

        # Calculate level and required
        if achieved:
            level_name = "WAC"
            required = 6
        else:
            level_name = "Not Yet"
            required = 6

        return {
            'current': current_count,
            'required': required,
            'achieved': achieved,
            'progress_pct': min(100.0, (current_count / 6) * 100),
            'level': level_name,
            'continents_worked': sorted(list(continents_worked)),
            'continent_details': continent_details,
            'band_details': band_details,
        }

    def get_requirements(self) -> Dict[str, Any]:
        """
        Return WAC award requirements

        Returns:
            Award requirements dictionary
        """
        return {
            'name': 'SKCC WAC Award',
            'description': 'Contact SKCC members in all six continental areas',
            'base_requirement': 'Contacts with members in all 6 continents',
            'modes': ['CW'],
            'bands': ['All'],
            'effective_date': 'October 9, 2011 or later',
            'validity_rule': 'Both operators must hold SKCC membership at time of contact',
            'mechanical_key': True,
            'continents_required': list(self.continents.keys()),
            'special_rules': [
                'Six continental areas: North America, South America, Europe, Africa, Asia, Oceania',
                'Boundary definitions follow IARU standards',
                'Band endorsements available (specify band in application)',
                'QRP endorsement available (≤5W power for all contacts)',
                'Contacts required with members in all 6 continents',
                'Remote stations do not need to be participating in the award',
            ]
        }
