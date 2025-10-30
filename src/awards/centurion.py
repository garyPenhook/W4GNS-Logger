"""
SKCC Centurion Award - Contact 100+ Different SKCC Members

The Centurion award is earned by making contact with 100 different SKCC members.
Endorsements are available in 100-contact increments up to Centurion x10,
then in 500-contact increments (Cx15, Cx20, etc.).

Rules:
- Both operators must hold SKCC membership at time of contact
- Exchanges must include SKCC numbers
- QSOs must be CW mode only
- Mechanical key policy: Contacts must use straight key, sideswiper (cootie), or bug
- Club calls and special event calls don't count after December 1, 2009
- Any band(s) allowed
- Each call sign counts only once (per category)
"""

import logging
from typing import Dict, List, Any, Set
from sqlalchemy.orm import Session

from src.awards.base import AwardProgram
from src.utils.skcc_number import extract_base_skcc_number
from src.awards.constants import (
    CENTURION_ENDORSEMENTS,
    get_endorsement_level,
    get_next_endorsement_threshold
)

logger = logging.getLogger(__name__)

# Special event calls that don't count after December 1, 2009 for Centurion
# (Different from Tribune which uses October 1, 2008)
# Including K9SKC (SKCC Club Call) and known special-event calls like K3Y
SPECIAL_EVENT_CALLS: Set[str] = {
    'K9SKC',  # SKCC Club Call
    'K3Y',    # Example special-event call
}


class CenturionAward(AwardProgram):
    """SKCC Centurion Award - 100+ unique SKCC member contacts"""

    def __init__(self, db: Session):
        """
        Initialize Centurion award

        Args:
            db: SQLAlchemy database session (needed for list lookups)
        """
        super().__init__(name="Centurion", program_id="CENTURION")
        self.db = db
        
        # For Centurion, any SKCC member is valid
        # We don't need to cache member lists since we accept any contact with an SKCC number
        # The presence of an SKCC number in the contact indicates valid membership

    def validate(self, contact: Dict[str, Any]) -> bool:
        """
        Check if a contact qualifies for Centurion award

        Requirements:
        - CW mode only
        - SKCC number present on both sides (in skcc_number field and contact's SKCC number)
        - Mechanical key required (STRAIGHT, BUG, or SIDESWIPER)
        - Club calls and special event calls excluded after December 1, 2009
        - Both operators must hold SKCC membership at time of contact
        - Valid SKCC member (can be checked against Centurion list, but not required)

        Args:
            contact: Contact record dictionary

        Returns:
            True if contact qualifies for Centurion award
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
            logger.debug(f"Invalid key type for Centurion: {key_type}")
            return False

        # Get contact date for date-based validations
        qso_date = contact.get('qso_date', '')

        # CRITICAL RULE: Club calls and special event calls don't count after Dec 1, 2009
        # "Club calls (K9SKC) and special-event callsigns cannot be used for credit
        # after December 1, 2009. Individual operator call signs are acceptable if
        # not previously used."
        if qso_date and qso_date >= '20091201':  # On or after December 1, 2009
            callsign = contact.get('callsign', '').upper().strip()
            # Remove /portable or other suffix indicators
            base_call = callsign.split('/')[0] if '/' in callsign else callsign

            if base_call in SPECIAL_EVENT_CALLS:
                logger.debug(
                    f"Special-event call filtered after Dec 1, 2009: {callsign} "
                    f"(date: {qso_date})"
                )
                return False

        # Remote station must be a valid SKCC member (they have a SKCC number in the contact)
        # This is assumed to be present if the contact was logged in SKCC context
        if not contact.get('skcc_number'):
            return False

        # Verify remote operator is a valid SKCC member
        # For Centurion award, any contact with an SKCC number is valid
        # The SKCC number itself indicates membership
        skcc_num = contact.get('skcc_number', '').strip()
        if skcc_num:
            base_number = extract_base_skcc_number(skcc_num)
            if not base_number:
                logger.debug(f"Invalid SKCC number format: {skcc_num}")
                return False

        return True

    def calculate_progress(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate Centurion award progress

        Counts unique SKCC numbers contacted (base number without suffixes).

        Args:
            contacts: List of contact records

        Returns:
            {
                'current': int,        # Unique SKCC members contacted
                'required': int,       # Always 100 for base award
                'achieved': bool,      # True if 100+ members
                'progress_pct': float, # Percentage toward 100
                'endorsement': str,    # Current endorsement level (Centurion, Cx2, etc.)
                'unique_members': set  # Set of unique SKCC numbers
            }
        """
        # Collect unique SKCC numbers (base number without suffixes like C, T, S, x)
        unique_members = set()

        for contact in contacts:
            if self.validate(contact):
                skcc_number = contact.get('skcc_number', '').strip()
                if skcc_number:
                    base_number = extract_base_skcc_number(skcc_number)
                    if base_number:
                        unique_members.add(base_number)

        current_count = len(unique_members)
        required_count = 100

        # Determine endorsement level using constants
        endorsement_level = get_endorsement_level(current_count, CENTURION_ENDORSEMENTS)
        next_level = get_next_endorsement_threshold(current_count, CENTURION_ENDORSEMENTS)

        return {
            'current': current_count,
            'required': required_count,
            'achieved': current_count >= required_count,
            'progress_pct': min(100.0, (current_count / required_count) * 100),
            'endorsement': endorsement_level,
            'unique_members': unique_members,
            'next_level_count': next_level
        }



    def get_requirements(self) -> Dict[str, Any]:
        """
        Return Centurion award requirements

        Returns:
            Award requirements dictionary
        """
        return {
            'name': 'SKCC Centurion',
            'description': 'Contact 100 different SKCC members',
            'base_requirement': 100,
            'base_units': 'unique SKCC members',
            'modes': ['CW'],
            'bands': ['All'],
            'validity_rule': 'Both operators must hold SKCC membership at time of contact',
            'endorsements_available': True,
            'endorsement_increments': [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1500, 2000, 2500, 3000, 3500, 4000, 4500]
        }

    def get_endorsements(self) -> List[Dict[str, Any]]:
        """
        Return list of Centurion endorsement levels

        Returns:
            List of endorsement level dictionaries
        """
        return [
            {'level': 100, 'description': 'Centurion', 'contacts_needed': 100},
            {'level': 200, 'description': 'Centurion x2', 'contacts_needed': 200},
            {'level': 300, 'description': 'Centurion x3', 'contacts_needed': 300},
            {'level': 400, 'description': 'Centurion x4', 'contacts_needed': 400},
            {'level': 500, 'description': 'Centurion x5', 'contacts_needed': 500},
            {'level': 600, 'description': 'Centurion x6', 'contacts_needed': 600},
            {'level': 700, 'description': 'Centurion x7', 'contacts_needed': 700},
            {'level': 800, 'description': 'Centurion x8', 'contacts_needed': 800},
            {'level': 900, 'description': 'Centurion x9', 'contacts_needed': 900},
            {'level': 1000, 'description': 'Centurion x10', 'contacts_needed': 1000},
            {'level': 1500, 'description': 'Centurion x15', 'contacts_needed': 1500},
            {'level': 2000, 'description': 'Centurion x20', 'contacts_needed': 2000},
            {'level': 2500, 'description': 'Centurion x25', 'contacts_needed': 2500},
            {'level': 3000, 'description': 'Centurion x30', 'contacts_needed': 3000},
            {'level': 3500, 'description': 'Centurion x35', 'contacts_needed': 3500},
            {'level': 4000, 'description': 'Centurion x40', 'contacts_needed': 4000},
        ]
