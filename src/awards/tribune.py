"""
SKCC Tribune Award - Contact 50+ Centurions/Tribunes/Senators

The Tribune award is earned by making contact with 50+ different SKCC members
who are Centurions, Tribunes, or Senators.

Rules:
- Must be a Centurion first (100+ unique SKCC members)
- Contact 50+ Tribunes/Senators (from official list)
- Both operators must hold Centurion status at time of contact
- Exchanges must include SKCC numbers
- QSOs must be CW mode only
- Mechanical key policy: Contact must use mechanical key (STRAIGHT, BUG, or SIDESWIPER)
- Club calls and special event calls don't count after October 1, 2008
- Any band(s) allowed
- Contacts valid on or after March 1, 2007
- Each call sign counts only once (per category)
"""

import logging
from typing import Dict, List, Any, Set
from datetime import datetime
from sqlalchemy.orm import Session

from src.awards.base import AwardProgram
from src.utils.skcc_number import extract_base_skcc_number
from src.awards.constants import (
    TRIBUNE_ENDORSEMENTS,
    get_endorsement_level,
    get_next_endorsement_threshold,
    TRIBUNE_EFFECTIVE_DATE,
    TRIBUNE_SPECIAL_EVENT_CUTOFF,
    SPECIAL_EVENT_CALLS
)

logger = logging.getLogger(__name__)


class TribuneAward(AwardProgram):
    """SKCC Tribune Award - 50+ unique Tribune/Senator contacts"""

    def __init__(self, db: Session):
        """
        Initialize Tribune award

        Args:
            db: SQLAlchemy database session (needed for list lookups)
        """
        super().__init__(name="Tribune", program_id="TRIBUNE")
        self.db = db
        # Effective date for Tribune award: March 1, 2007
        self.tribune_effective_date = datetime(2007, 3, 1)
        self.tribune_effective_date_str = TRIBUNE_EFFECTIVE_DATE
        
        # Cache member lists and Centurion dates for efficient validation
        from src.database.models import TribuneeMember, SenatorMember, CenturionMember
        self._tribune_numbers = {m.skcc_number for m in db.query(TribuneeMember.skcc_number).all()}
        self._senator_numbers = {m.skcc_number for m in db.query(SenatorMember.skcc_number).all()}
        self._centurion_numbers = {m.skcc_number for m in db.query(CenturionMember.skcc_number).all()}
        self._all_valid_members = self._tribune_numbers | self._senator_numbers | self._centurion_numbers
        
        # Cache Centurion achievement dates
        self._centurion_dates = {}
        for member in db.query(CenturionMember.skcc_number, CenturionMember.centurion_date).all():
            if member.centurion_date:
                self._centurion_dates[member.skcc_number] = member.centurion_date
        
        # Get user's Centurion date
        from src.config.settings import get_config_manager
        config_manager = get_config_manager()
        user_callsign = config_manager.get("operator_callsign", "").upper()
        
        self._user_centurion_date = None
        if user_callsign:
            user_entry = db.query(CenturionMember).filter(
                CenturionMember.callsign == user_callsign
            ).first()
            if user_entry and user_entry.centurion_date:
                self._user_centurion_date = user_entry.centurion_date
        
        # Fallback to config or earliest QSO
        if not self._user_centurion_date:
            self._user_centurion_date = config_manager.get('awards', {}).get('centurion_date', '')
            if not self._user_centurion_date:
                from src.database.models import Contact
                earliest_qso = db.query(Contact).filter(
                    Contact.mode == "CW",
                    Contact.skcc_number.isnot(None)
                ).order_by(Contact.qso_date.asc()).first()
                if earliest_qso:
                    self._user_centurion_date = earliest_qso.qso_date

    def validate(self, contact: Dict[str, Any]) -> bool:
        """
        Check if a contact qualifies for Tribune award

        Requirements:
        - CW mode only
        - SKCC number present
        - Contact date on or after March 1, 2007
        - Mechanical key required (STRAIGHT, BUG, or SIDESWIPER)
        - Club calls and special event calls excluded after October 1, 2008
        - Remote station must be Tribune/Senator (checked via list)
        - Both operators must hold appropriate SKCC membership at time of contact

        Args:
            contact: Contact record dictionary

        Returns:
            True if contact qualifies for Tribune award
        """
        # Must be CW mode
        if contact.get('mode', '').upper() != 'CW':
            return False

        # Must have SKCC number
        if not contact.get('skcc_number'):
            return False

        # Get contact date once for multiple date-based validations
        qso_date = contact.get('qso_date', '')

        # Check contact date (must be on/after March 1, 2007)
        # Date comparison using YYYYMMDD string format (lexicographic comparison works correctly)
        if qso_date and qso_date < self.tribune_effective_date_str:
            return False

        # CRITICAL RULE: SKCC Mechanical Key Policy
        # Contact must use mechanical key (STRAIGHT, BUG, or SIDESWIPER)
        key_type = contact.get('key_type', '').upper()
        if key_type and key_type not in ['STRAIGHT', 'BUG', 'SIDESWIPER']:
            logger.debug(f"Invalid key type for Tribune: {key_type}")
            return False

        # CRITICAL RULE: Club calls and special event calls don't count after Oct 1, 2008
        # "Neither the SKCC Club Call (K9SKC) nor any special-event call sign
        # (such as K3Y) will be accepted for credit for contacts logged on or
        # after 1 October 2008."
        if qso_date and qso_date >= TRIBUNE_SPECIAL_EVENT_CUTOFF:  # On or after October 1, 2008
            callsign = contact.get('callsign', '').upper().strip()
            # Remove /portable or other suffix indicators
            base_call = callsign.split('/')[0] if '/' in callsign else callsign

            if base_call in SPECIAL_EVENT_CALLS:
                logger.debug(
                    f"Special-event call filtered after Oct 1, 2008: {callsign} "
                    f"(date: {qso_date})"
                )
                return False

        # Remote station must be Tribune/Centurion/Senator (from cached member lists)
        skcc_num = contact.get('skcc_number', '')
        base_number = extract_base_skcc_number(skcc_num)
        
        if not base_number or base_number not in self._all_valid_members:
            return False
        
        # SKCC Rule: QSO must be on or after BOTH operators' Centurion dates
        # Check user's Centurion date
        if self._user_centurion_date and qso_date < self._user_centurion_date:
            return False
        
        # Check contacted station's Centurion date
        contact_centurion_date = self._centurion_dates.get(base_number)
        if contact_centurion_date and qso_date < contact_centurion_date:
            return False

        return True

    def calculate_progress(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate Tribune award progress

        Counts unique Tribune/Senator SKCC numbers contacted.

        Args:
            contacts: List of contact records

        Returns:
            {
                'current': int,        # Unique Tribune members contacted
                'required': int,       # Always 50 for base award
                'achieved': bool,      # True if 50+ members
                'progress_pct': float, # Percentage toward 50
                'endorsement': str,    # Current endorsement level (Tribune, Tx2, etc.)
                'unique_members': set  # Set of unique SKCC numbers
            }
        """
        # First, check if user is a Centurion (prerequisite)
        from src.database.models import Contact as ContactModel
        session = self.db

        centurion_count = session.query(ContactModel).filter(
            ContactModel.mode == "CW",
            ContactModel.skcc_number.isnot(None)
        ).count()

        # Get unique SKCC members for Centurion check
        if centurion_count > 0:
            centurion_contacts = session.query(ContactModel).filter(
                ContactModel.mode == "CW",
                ContactModel.skcc_number.isnot(None)
            ).all()

            unique_centurions = set()
            for contact in centurion_contacts:
                skcc_num = contact.skcc_number.strip()
                if skcc_num:
                    base_number = extract_base_skcc_number(skcc_num)
                    if base_number:
                        unique_centurions.add(base_number)

            is_centurion = len(unique_centurions) >= 100
        else:
            is_centurion = False

        # Collect unique Tribune members
        unique_members = set()

        for contact in contacts:
            if self.validate(contact):
                skcc_number = contact.get('skcc_number', '').strip()
                if skcc_number:
                    base_number = extract_base_skcc_number(skcc_number)
                    if base_number:
                        unique_members.add(base_number)

        current_count = len(unique_members)
        required_count = 50

        # Determine endorsement level using constants
        endorsement_level = get_endorsement_level(current_count, TRIBUNE_ENDORSEMENTS)
        next_level = get_next_endorsement_threshold(current_count, TRIBUNE_ENDORSEMENTS)

        return {
            'current': current_count,
            'required': required_count,
            'achieved': is_centurion and current_count >= required_count,
            'progress_pct': min(100.0, (current_count / required_count) * 100),
            'endorsement': endorsement_level,
            'unique_members': unique_members,
            'next_level_count': next_level,
            'is_centurion': is_centurion,
            'centurion_count': len(unique_centurions) if centurion_count > 0 else 0
        }

    def get_requirements(self) -> Dict[str, Any]:
        """
        Return Tribune award requirements

        Returns:
            Award requirements dictionary
        """
        return {
            'name': 'SKCC Tribune',
            'description': 'Contact 50+ Centurions/Tribunes/Senators (must be Centurion first)',
            'base_requirement': 50,
            'base_units': 'unique Tribune/Senator members',
            'prerequisite': 'Must achieve Centurion first (100+ SKCC members)',
            'prerequisite_requirement': 100,
            'modes': ['CW'],
            'bands': ['All'],
            'effective_date': 'March 1, 2007 or later',
            'validity_rule': 'Both operators must hold Centurion status at time of contact',
            'endorsements_available': True,
            'endorsement_increments': [50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 750, 1000, 1250, 1500, 1750]
        }

    def get_endorsements(self) -> List[Dict[str, Any]]:
        """
        Return list of Tribune endorsement levels

        Returns:
            List of endorsement level dictionaries
        """
        return [
            {'level': 50, 'description': 'Tribune', 'contacts_needed': 50},
            {'level': 100, 'description': 'Tribune x2', 'contacts_needed': 100},
            {'level': 150, 'description': 'Tribune x3', 'contacts_needed': 150},
            {'level': 200, 'description': 'Tribune x4', 'contacts_needed': 200},
            {'level': 250, 'description': 'Tribune x5', 'contacts_needed': 250},
            {'level': 300, 'description': 'Tribune x6', 'contacts_needed': 300},
            {'level': 350, 'description': 'Tribune x7', 'contacts_needed': 350},
            {'level': 400, 'description': 'Tribune x8', 'contacts_needed': 400},
            {'level': 450, 'description': 'Tribune x9', 'contacts_needed': 450},
            {'level': 500, 'description': 'Tribune x10', 'contacts_needed': 500},
            {'level': 750, 'description': 'Tribune x15', 'contacts_needed': 750},
            {'level': 1000, 'description': 'Tribune x20', 'contacts_needed': 1000},
            {'level': 1250, 'description': 'Tribune x25', 'contacts_needed': 1250},
            {'level': 1500, 'description': 'Tribune x30', 'contacts_needed': 1500},
        ]
