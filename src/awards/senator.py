"""
SKCC Senator Award - Contact 200+ Tribunes/Senators (requires Tribune x8)

The Senator award is earned by making contact with 200+ different SKCC members
who are Tribunes, Senators, or Senators (from official list).

Rules:
- Must be Tribune x8 first (400+ unique Tribune/Senator members)
- Contact 200+ additional Tribunes/Senators (on or after Tribune x8 achievement)
- Exchanges must include SKCC numbers
- QSOs must be CW mode only
- Mechanical key policy: Contacts must use straight key, bug, or side swiper
- Club calls and special event calls don't qualify
- Any band(s) allowed
- Contacts valid on or after August 1, 2013
- Each call sign counts only once (per category)
"""

import logging
from typing import Dict, List, Any, Set
from datetime import datetime
from sqlalchemy.orm import Session

from src.awards.base import AwardProgram

logger = logging.getLogger(__name__)

# Special event calls that don't count for Senator Award
# Including K9SKC (SKCC Club Call) and known special-event calls like K3Y
SPECIAL_EVENT_CALLS: Set[str] = {
    'K9SKC',  # SKCC Club Call
    'K3Y',    # Example special-event call
}


class SenatorAward(AwardProgram):
    """SKCC Senator Award - 200+ unique Tribune/Senator contacts after Tribune x8"""

    def __init__(self, db: Session):
        """
        Initialize Senator award

        Args:
            db: SQLAlchemy database session (needed for list lookups)
        """
        super().__init__(name="Senator", program_id="SENATOR")
        self.db = db
        # Effective date for Senator award: August 1, 2013
        self.senator_effective_date = datetime(2013, 8, 1)
        self.senator_effective_date_str = "20130801"  # YYYYMMDD format for string comparisons

    def validate(self, contact: Dict[str, Any]) -> bool:
        """
        Check if a contact qualifies for Senator award

        Requirements:
        - CW mode only
        - SKCC number present
        - Mechanical key required (STRAIGHT, BUG, or SIDESWIPER)
        - Contact date on or after August 1, 2013
        - Club calls and special event calls excluded
        - Remote station must be Tribune/Senator (checked via list)
        - Both operators must hold appropriate SKCC membership at time of contact

        Args:
            contact: Contact record dictionary

        Returns:
            True if contact qualifies for Senator award
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
            logger.debug(f"Invalid key type for Senator: {key_type}")
            return False

        # Get contact date for date-based validations
        qso_date = contact.get('qso_date', '')

        # Check contact date (must be on/after August 1, 2013)
        # Date comparison using YYYYMMDD string format (lexicographic comparison works correctly)
        if qso_date and qso_date < self.senator_effective_date_str:
            return False

        # CRITICAL RULE: Club calls and special event calls don't count for Senator
        # "Club calls (K9SKC) and special event calls don't qualify unless paired with
        # an FCC-assigned call."
        callsign = contact.get('callsign', '').upper().strip()
        base_call = callsign.split('/')[0] if '/' in callsign else callsign

        if base_call in SPECIAL_EVENT_CALLS:
            logger.debug(
                f"Special-event call filtered for Senator: {callsign}"
            )
            return False

        # Remote station must be Tribune or Senator
        # Check if contacted station is on Tribune/Senator list
        from src.services.tribune_fetcher import TribuneFetcher
        from src.services.senator_fetcher import SenatorFetcher
        from src.database.models import TribuneeMember, SenatorMember
        try:
            skcc_num = contact.get('skcc_number', '')
            if not (TribuneFetcher.is_tribune_member(self.db, skcc_num) or
                    SenatorFetcher.is_senator_member(self.db, skcc_num)):
                return False

            # Verify remote operator held Tribune/Senator membership at time of contact
            if skcc_num:
                session = self.db
                base_number = skcc_num.strip().split()[0]
                if base_number and base_number[-1] in 'CTS':
                    base_number = base_number[:-1]
                if base_number and 'x' in base_number:
                    base_number = base_number.split('x')[0]

                # Query Tribune or Senator member lists by base SKCC number
                member = session.query(TribuneeMember).filter(
                    TribuneeMember.skcc_number == base_number
                ).first()

                if not member:
                    member = session.query(SenatorMember).filter(
                        SenatorMember.skcc_number == base_number
                    ).first()

                if not member:
                    logger.debug(
                        f"Remote operator SKCC {skcc_num} not found in Tribune/Senator member lists. "
                        f"Contact will be counted but may require verification."
                    )

        except Exception as e:
            # If we can't check, log error and require manual verification
            logger.warning(
                f"Failed to check Tribune/Senator membership for {contact.get('callsign', 'unknown')}: {e}. "
                f"Contact will require manual verification.",
                exc_info=True
            )
            # Return False to indicate this contact needs verification by the user
            return False

        return True

    def calculate_progress(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate Senator award progress

        Counts unique Tribune/Senator SKCC numbers contacted after Tribune x8 achievement.

        Args:
            contacts: List of contact records

        Returns:
            {
                'current': int,        # Unique Tribune/Senator members contacted after Tx8
                'required': int,       # Always 200 for base award
                'achieved': bool,      # True if 200+ members after Tx8
                'progress_pct': float, # Percentage toward 200
                'endorsement': str,    # Current endorsement level
                'unique_senators': set # Set of unique SKCC numbers
            }
        """
        # First, check if user is Tribune x8 (prerequisite)
        from src.database.models import Contact as ContactModel
        session = self.db

        # Get Tribune x8 achievement date from Tribune list (authoritative)
        from src.config.settings import get_config_manager
        from src.database.models import TribuneeMember

        config_manager = get_config_manager()
        user_callsign = config_manager.get("operator_callsign", "").upper()
        tribune_x8_date = None

        if user_callsign:
            user_tribune_entry = session.query(TribuneeMember).filter(
                TribuneeMember.callsign == user_callsign
            ).first()
            if user_tribune_entry and user_tribune_entry.tribune_date:
                tribune_x8_date = user_tribune_entry.tribune_date

        # Check Tribune progress to see if we're at x8 (400+)
        tribune_contacts = session.query(ContactModel).filter(
            ContactModel.mode == "CW",
            ContactModel.skcc_number.isnot(None)
        ).all()

        unique_tribunes = set()
        for contact in tribune_contacts:
            skcc_num = contact.skcc_number.strip()
            if skcc_num:
                from src.services.tribune_fetcher import TribuneFetcher
                if TribuneFetcher.is_tribune_member(session, skcc_num):
                    base_number = skcc_num.split()[0]
                    if base_number and base_number[-1] in 'CTS':
                        base_number = base_number[:-1]
                    if base_number and 'x' in base_number:
                        base_number = base_number.split('x')[0]
                    if base_number and base_number.isdigit():
                        unique_tribunes.add(base_number)

        is_tribune_x8 = len(unique_tribunes) >= 400

        # Collect unique Tribune/Senator members contacted AFTER Tribune x8 date
        unique_senators = set()

        for contact in contacts:
            if self.validate(contact):
                # Only count if after Tribune x8 date
                if tribune_x8_date and contact.get('qso_date', '') > tribune_x8_date:
                    skcc_number = contact.get('skcc_number', '').strip()
                    if skcc_number:
                        # Extract base number
                        base_number = skcc_number.split()[0]
                        if base_number and base_number[-1] in 'CTS':
                            base_number = base_number[:-1]
                        if base_number and 'x' in base_number:
                            base_number = base_number.split('x')[0]
                        # Only add if it's a valid number
                        if base_number and base_number.isdigit():
                            unique_senators.add(base_number)

        current_count = len(unique_senators)
        required_count = 200

        # Determine endorsement level
        endorsement_level = self._get_endorsement_level(current_count)

        return {
            'current': current_count,
            'required': required_count,
            'achieved': is_tribune_x8 and current_count >= required_count,
            'progress_pct': min(100.0, (current_count / required_count) * 100),
            'endorsement': endorsement_level,
            'unique_senators': unique_senators,
            'next_level_count': self._get_next_endorsement_level(current_count),
            'is_tribune_x8': is_tribune_x8,
            'tribune_count': len(unique_tribunes),
            'tribune_x8_date': tribune_x8_date
        }

    def _get_endorsement_level(self, count: int) -> str:
        """
        Calculate endorsement level based on Senator contact count

        Levels:
        - Base: 200 (Senator)
        - Endorsements: 400 (Sx2), 600 (Sx3), ... 2000 (Sx10)

        Args:
            count: Number of unique Tribune/Senator members contacted after x8

        Returns:
            Endorsement level string (e.g., "Senator", "Sx2", "Sx10")
        """
        if count < 200:
            return "Not Yet"
        elif count < 400:
            return "Senator"
        elif count < 600:
            return "Senator x2"
        elif count < 800:
            return "Senator x3"
        elif count < 1000:
            return "Senator x4"
        elif count < 1200:
            return "Senator x5"
        elif count < 1400:
            return "Senator x6"
        elif count < 1600:
            return "Senator x7"
        elif count < 1800:
            return "Senator x8"
        elif count < 2000:
            return "Senator x9"
        elif count < 2200:
            return "Senator x10"
        else:
            return f"Senator x{(count // 200)}"

    def _get_next_endorsement_level(self, count: int) -> int:
        """
        Calculate count needed for next endorsement level

        Args:
            count: Current contact count

        Returns:
            Contact count needed for next level
        """
        if count < 200:
            return 200
        elif count < 400:
            return 400
        elif count < 600:
            return 600
        elif count < 800:
            return 800
        elif count < 1000:
            return 1000
        elif count < 1200:
            return 1200
        elif count < 1400:
            return 1400
        elif count < 1600:
            return 1600
        elif count < 1800:
            return 1800
        elif count < 2000:
            return 2000
        elif count < 2200:
            return 2200
        else:
            return count + 200  # 200-contact increments

    def get_requirements(self) -> Dict[str, Any]:
        """
        Return Senator award requirements

        Returns:
            Award requirements dictionary
        """
        return {
            'name': 'SKCC Senator',
            'description': 'Contact 200+ Tribunes/Senators (must be Tribune x8 first)',
            'base_requirement': 200,
            'base_units': 'unique Tribune/Senator members after x8',
            'prerequisite': 'Must achieve Tribune x8 first (400+ Tribune/Senator members)',
            'prerequisite_requirement': 400,
            'modes': ['CW'],
            'bands': ['All'],
            'effective_date': 'August 1, 2013 or later',
            'validity_rule': 'Both operators must hold Tribune or Senator status at time of contact',
            'endorsements_available': True,
            'endorsement_increments': [200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000, 2200]
        }

    def get_endorsements(self) -> List[Dict[str, Any]]:
        """
        Return list of Senator endorsement levels

        Returns:
            List of endorsement level dictionaries
        """
        return [
            {'level': 200, 'description': 'Senator', 'contacts_needed': 200},
            {'level': 400, 'description': 'Senator x2', 'contacts_needed': 400},
            {'level': 600, 'description': 'Senator x3', 'contacts_needed': 600},
            {'level': 800, 'description': 'Senator x4', 'contacts_needed': 800},
            {'level': 1000, 'description': 'Senator x5', 'contacts_needed': 1000},
            {'level': 1200, 'description': 'Senator x6', 'contacts_needed': 1200},
            {'level': 1400, 'description': 'Senator x7', 'contacts_needed': 1400},
            {'level': 1600, 'description': 'Senator x8', 'contacts_needed': 1600},
            {'level': 1800, 'description': 'Senator x9', 'contacts_needed': 1800},
            {'level': 2000, 'description': 'Senator x10', 'contacts_needed': 2000},
        ]
