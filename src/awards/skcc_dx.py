"""
SKCC DX Award - Contact DX Stations (DXCC Entities) Using SKCC Members

The DX Award is earned by making contact with SKCC members in different DXCC entities.
Two variants available:
- DXQ: QSO-based (each SKCC member per country counts separately, levels: 10, 25, 50+)
- DXC: Country-based (each country counts only once, levels: 10, 25, 50+)

Rules:
- Both operators must hold SKCC membership at time of contact
- Must contact DX entities (outside own DXCC entity)
- Maritime-mobile within 12-mile territorial limit counts; beyond does not
- Mechanical key policy: Contacts must use straight key, bug, or side swiper
- SKCC numbers and names must be exchanged
- DXQ: Contacts valid on or after June 14, 2009
- DXC: Contacts valid on or after December 19, 2009
- Any band(s) allowed
"""

import logging
from typing import Dict, List, Any, Set
from datetime import datetime
from sqlalchemy.orm import Session

from src.awards.base import AwardProgram

logger = logging.getLogger(__name__)


class DXQAward(AwardProgram):
    """SKCC DX Award (QSO-based) - Each SKCC member per country counts separately"""

    def __init__(self, db: Session):
        """
        Initialize DXQ award

        Args:
            db: SQLAlchemy database session
        """
        super().__init__(name="DX Award (QSO)", program_id="SKCC_DXQ")
        self.db = db
        # DXQ effective date: June 14, 2009
        self.dxq_effective_date = datetime(2009, 6, 14)
        self.dxq_effective_date_str = "20090614"

    def validate(self, contact: Dict[str, Any]) -> bool:
        """
        Check if a contact qualifies for DXQ award

        Requirements:
        - CW mode only
        - SKCC number present
        - Mechanical key required (STRAIGHT, BUG, or SIDESWIPER)
        - Contact date on or after June 14, 2009
        - Must be DX (DXCC entity outside own country)
        - Maritime-mobile within 12-mile limit counts; beyond doesn't
        - Remote station must be SKCC member

        Args:
            contact: Contact record dictionary

        Returns:
            True if contact qualifies for DXQ award
        """
        # Must be CW mode
        if contact.get('mode', '').upper() != 'CW':
            return False

        # Must have SKCC number
        if not contact.get('skcc_number'):
            return False

        # CRITICAL RULE: SKCC Mechanical Key Policy
        # Contact must use mechanical key (STRAIGHT, BUG, or SIDESWIPER)
        key_type = contact.get('key_type', '').upper()
        if key_type and key_type not in ['STRAIGHT', 'BUG', 'SIDESWIPER']:
            logger.debug(f"Invalid key type for DXQ: {key_type}")
            return False

        # Get contact date for date-based validations
        qso_date = contact.get('qso_date', '')

        # Check contact date (must be on/after June 14, 2009)
        if qso_date and qso_date < self.dxq_effective_date_str:
            return False

        # Must be DX (outside own country)
        # Assume local operator's DXCC is USA (291) unless configured otherwise
        local_dxcc = 291  # USA - can be made configurable
        remote_dxcc = contact.get('dxcc')

        if not remote_dxcc or remote_dxcc == local_dxcc:
            logger.debug(f"Contact not DX or in own country: {remote_dxcc}")
            return False

        # CRITICAL RULE: Maritime-Mobile Validation
        # "Maritime-mobile stations within 12-mile territorial limits qualify;
        # those beyond this limit do not."
        callsign = contact.get('callsign', '').upper().strip()

        # Check if maritime-mobile (indicated by /MM suffix)
        if '/MM' in callsign:
            # Maritime-mobile stations must have verified distance within 12 nautical miles
            distance = contact.get('distance')

            if distance is None:
                # No distance data - cannot verify 12-mile limit, reject to ensure compliance
                logger.debug(
                    f"Maritime-mobile contact {callsign} lacks distance data "
                    f"(12-mile limit cannot be verified)"
                )
                return False

            # Validate distance is within 12 nautical miles
            try:
                distance_nm = float(distance)
                if distance_nm > 12.0:
                    logger.debug(
                        f"Maritime-mobile contact {callsign} exceeds 12-nautical-mile limit: {distance_nm}nm"
                    )
                    return False
            except (ValueError, TypeError):
                # Cannot parse distance, reject to ensure compliance
                logger.debug(
                    f"Maritime-mobile contact {callsign} has invalid distance data: {distance}"
                )
                return False

        return True

    def calculate_progress(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate DXQ award progress

        Counts unique (SKCC member + DXCC entity) combinations.
        Each SKCC member in different countries counts separately.

        Args:
            contacts: List of contact records

        Returns:
            {
                'current': int,        # Unique SKCC member per country combinations
                'required': int,       # Required for current level
                'achieved': bool,      # True if level achieved
                'progress_pct': float, # Percentage toward requirement
                'level': str,          # DXQ-10, DXQ-25, DXQ-50+
                'countries': dict,     # DXCC code -> list of contacted SKCC members
            }
        """
        # Collect unique (SKCC member + DXCC) combinations
        dxq_contacts = set()
        country_members: Dict[int, Set[str]] = {}

        for contact in contacts:
            if self.validate(contact):
                skcc_num = contact.get('skcc_number', '').strip()
                dxcc = contact.get('dxcc')

                if skcc_num and dxcc:
                    # Extract base SKCC number (remove C/T/S/x suffixes)
                    base_number = skcc_num.split()[0]
                    if base_number and base_number[-1] in 'CTS':
                        base_number = base_number[:-1]
                    if base_number and 'x' in base_number:
                        base_number = base_number.split('x')[0]

                    if base_number and base_number.isdigit():
                        # Create tuple of (DXCC, SKCC member)
                        combo = (dxcc, base_number)
                        dxq_contacts.add(combo)

                        # Track country members
                        if dxcc not in country_members:
                            country_members[dxcc] = set()
                        country_members[dxcc].add(base_number)

        current_count = len(dxq_contacts)

        # Determine level based on count
        if current_count >= 50:
            level_name = "DXQ-50+"
            required = 50
        elif current_count >= 25:
            level_name = "DXQ-25"
            required = 25
        elif current_count >= 10:
            level_name = "DXQ-10"
            required = 10
        else:
            level_name = "Not Yet"
            required = 10

        return {
            'current': current_count,
            'required': required,
            'achieved': current_count >= 10,  # Base level is 10
            'progress_pct': min(100.0, (current_count / 10) * 100),
            'level': level_name,
            'countries': {dxcc: len(members) for dxcc, members in sorted(country_members.items())},
            'total_countries': len(country_members),
            'dxq_contacts': dxq_contacts
        }

    def get_requirements(self) -> Dict[str, Any]:
        """
        Return DXQ award requirements

        Returns:
            Award requirements dictionary
        """
        return {
            'name': 'SKCC DX Award (QSO)',
            'description': 'Contact SKCC members in different DXCC entities',
            'variant': 'DXQ - QSO-based (each SKCC member per country counts separately)',
            'levels': ['DXQ-10', 'DXQ-25', 'DXQ-50+'],
            'requirements': {
                'DXQ-10': 10,
                'DXQ-25': 25,
                'DXQ-50+': '50+'
            },
            'modes': ['CW'],
            'bands': ['All'],
            'effective_date': 'June 14, 2009 or later',
            'validity_rule': 'Both operators must hold SKCC membership at time of contact',
            'mechanical_key': True,
            'dxcc_entity_required': True
        }

    def get_endorsements(self) -> List[Dict[str, Any]]:
        """Return DXQ endorsement levels"""
        return [
            {'level': 'DXQ-10', 'countries': 10, 'description': '10 DXCC entities'},
            {'level': 'DXQ-25', 'countries': 25, 'description': '25 DXCC entities'},
            {'level': 'DXQ-50', 'countries': 50, 'description': '50 DXCC entities'},
            {'level': 'DXQ-100', 'countries': 100, 'description': '100 DXCC entities'},
        ]


class DXCAward(AwardProgram):
    """SKCC DX Award (Country-based) - Each country counts only once"""

    def __init__(self, db: Session):
        """
        Initialize DXC award

        Args:
            db: SQLAlchemy database session
        """
        super().__init__(name="DX Award (Country)", program_id="SKCC_DXC")
        self.db = db
        # DXC effective date: December 19, 2009
        self.dxc_effective_date = datetime(2009, 12, 19)
        self.dxc_effective_date_str = "20091219"

    def validate(self, contact: Dict[str, Any]) -> bool:
        """
        Check if a contact qualifies for DXC award

        Requirements:
        - CW mode only
        - SKCC number present
        - Mechanical key required (STRAIGHT, BUG, or SIDESWIPER)
        - Contact date on or after December 19, 2009
        - Must be DX (DXCC entity outside own country)
        - Maritime-mobile within 12-mile limit counts; beyond doesn't
        - Remote station must be SKCC member

        Args:
            contact: Contact record dictionary

        Returns:
            True if contact qualifies for DXC award
        """
        # Must be CW mode
        if contact.get('mode', '').upper() != 'CW':
            return False

        # Must have SKCC number
        if not contact.get('skcc_number'):
            return False

        # CRITICAL RULE: SKCC Mechanical Key Policy
        # Contact must use mechanical key (STRAIGHT, BUG, or SIDESWIPER)
        key_type = contact.get('key_type', '').upper()
        if key_type and key_type not in ['STRAIGHT', 'BUG', 'SIDESWIPER']:
            logger.debug(f"Invalid key type for DXC: {key_type}")
            return False

        # Get contact date for date-based validations
        qso_date = contact.get('qso_date', '')

        # Check contact date (must be on/after December 19, 2009)
        if qso_date and qso_date < self.dxc_effective_date_str:
            return False

        # Must be DX (outside own country)
        # Assume local operator's DXCC is USA (291) unless configured otherwise
        local_dxcc = 291  # USA - can be made configurable
        remote_dxcc = contact.get('dxcc')

        if not remote_dxcc or remote_dxcc == local_dxcc:
            logger.debug(f"Contact not DX or in own country: {remote_dxcc}")
            return False

        # CRITICAL RULE: Maritime-Mobile Validation
        # "Maritime-mobile stations within 12-mile territorial limits qualify;
        # those beyond this limit do not."
        callsign = contact.get('callsign', '').upper().strip()

        # Check if maritime-mobile (indicated by /MM suffix)
        if '/MM' in callsign:
            # Maritime-mobile stations must have verified distance within 12 nautical miles
            distance = contact.get('distance')

            if distance is None:
                # No distance data - cannot verify 12-mile limit, reject to ensure compliance
                logger.debug(
                    f"Maritime-mobile contact {callsign} lacks distance data "
                    f"(12-mile limit cannot be verified)"
                )
                return False

            # Validate distance is within 12 nautical miles
            try:
                distance_nm = float(distance)
                if distance_nm > 12.0:
                    logger.debug(
                        f"Maritime-mobile contact {callsign} exceeds 12-nautical-mile limit: {distance_nm}nm"
                    )
                    return False
            except (ValueError, TypeError):
                # Cannot parse distance, reject to ensure compliance
                logger.debug(
                    f"Maritime-mobile contact {callsign} has invalid distance data: {distance}"
                )
                return False

        return True

    def calculate_progress(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate DXC award progress

        Counts unique DXCC entities. Each country counts only once
        regardless of how many SKCC members contacted.

        Args:
            contacts: List of contact records

        Returns:
            {
                'current': int,        # Unique DXCC entities
                'required': int,       # Required for current level
                'achieved': bool,      # True if level achieved
                'progress_pct': float, # Percentage toward requirement
                'level': str,          # DXC-10, DXC-25, DXC-50+
                'countries': list,     # List of DXCC codes contacted
            }
        """
        # Collect unique DXCC entities
        dxc_countries = set()

        for contact in contacts:
            if self.validate(contact):
                dxcc = contact.get('dxcc')

                if dxcc:
                    dxc_countries.add(dxcc)

        current_count = len(dxc_countries)

        # Determine level based on count
        if current_count >= 50:
            level_name = "DXC-50+"
            required = 50
        elif current_count >= 25:
            level_name = "DXC-25"
            required = 25
        elif current_count >= 10:
            level_name = "DXC-10"
            required = 10
        else:
            level_name = "Not Yet"
            required = 10

        return {
            'current': current_count,
            'required': required,
            'achieved': current_count >= 10,  # Base level is 10
            'progress_pct': min(100.0, (current_count / 10) * 100),
            'level': level_name,
            'countries': sorted(list(dxc_countries)),
            'total_countries': current_count
        }

    def get_requirements(self) -> Dict[str, Any]:
        """
        Return DXC award requirements

        Returns:
            Award requirements dictionary
        """
        return {
            'name': 'SKCC DX Award (Country)',
            'description': 'Contact SKCC members in different DXCC entities',
            'variant': 'DXC - Country-based (each country counts only once)',
            'levels': ['DXC-10', 'DXC-25', 'DXC-50+'],
            'requirements': {
                'DXC-10': 10,
                'DXC-25': 25,
                'DXC-50+': '50+'
            },
            'modes': ['CW'],
            'bands': ['All'],
            'effective_date': 'December 19, 2009 or later',
            'validity_rule': 'Both operators must hold SKCC membership at time of contact',
            'mechanical_key': True,
            'dxcc_entity_required': True
        }

    def get_endorsements(self) -> List[Dict[str, Any]]:
        """Return DXC endorsement levels"""
        return [
            {'level': 'DXC-10', 'countries': 10, 'description': '10 DXCC entities'},
            {'level': 'DXC-25', 'countries': 25, 'description': '25 DXCC entities'},
            {'level': 'DXC-50', 'countries': 50, 'description': '50 DXCC entities'},
            {'level': 'DXC-100', 'countries': 100, 'description': '100 DXCC entities'},
        ]
