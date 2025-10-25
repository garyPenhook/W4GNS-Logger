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
- Any band(s) allowed
- Contacts valid on or after March 1, 2007
- Each call sign counts only once (per category)
"""

from typing import Dict, List, Any
from datetime import datetime
from sqlalchemy.orm import Session

from src.awards.base import AwardProgram


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
        self.tribune_effective_date = "20070301"  # March 1, 2007 - YYYYMMDD

    def validate(self, contact: Dict[str, Any]) -> bool:
        """
        Check if a contact qualifies for Tribune award

        Requirements:
        - CW mode only
        - SKCC number present
        - Contact date on or after March 1, 2007
        - Remote station must be Tribune/Senator (checked via list)

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

        # Check contact date (must be on/after March 1, 2007)
        qso_date = contact.get('qso_date', '')
        if qso_date and qso_date < self.tribune_effective_date:
            return False

        # Remote station must be Tribune or higher
        # Check if contacted station is on Tribune/Senator list
        from src.services.tribune_fetcher import TribuneFetcher
        try:
            if not TribuneFetcher.is_tribune_member(self.db, contact.get('skcc_number', '')):
                return False
        except:
            # If we can't check, require manual verification
            pass

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
                    base_number = skcc_num.split()[0]
                    if base_number and base_number[-1] in 'CTS':
                        base_number = base_number[:-1]
                    if base_number and 'x' in base_number:
                        base_number = base_number.split('x')[0]
                    if base_number and base_number.isdigit():
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
                    # Extract base number
                    base_number = skcc_number.split()[0]
                    if base_number and base_number[-1] in 'CTS':
                        base_number = base_number[:-1]
                    if base_number and 'x' in base_number:
                        base_number = base_number.split('x')[0]
                    # Only add if it's a valid number
                    if base_number and base_number.isdigit():
                        unique_members.add(base_number)

        current_count = len(unique_members)
        required_count = 50

        # Determine endorsement level
        endorsement_level = self._get_endorsement_level(current_count)

        return {
            'current': current_count,
            'required': required_count,
            'achieved': is_centurion and current_count >= required_count,
            'progress_pct': min(100.0, (current_count / required_count) * 100),
            'endorsement': endorsement_level,
            'unique_members': unique_members,
            'next_level_count': self._get_next_endorsement_level(current_count),
            'is_centurion': is_centurion,
            'centurion_count': len(unique_centurions) if centurion_count > 0 else 0
        }

    def _get_endorsement_level(self, count: int) -> str:
        """
        Calculate endorsement level based on Tribune contact count

        Levels:
        - Base: 50 (Tribune)
        - Endorsements: 100 (Tx2), 150 (Tx3), ... 500 (Tx10)
        - Higher: 750 (Tx15), 1000 (Tx20), etc.

        Args:
            count: Number of unique Tribune members contacted

        Returns:
            Endorsement level string (e.g., "Tribune", "Tx2", "Tx10")
        """
        if count < 50:
            return "Not Yet"
        elif count < 100:
            return "Tribune"
        elif count < 150:
            return "Tribune x2"
        elif count < 200:
            return "Tribune x3"
        elif count < 250:
            return "Tribune x4"
        elif count < 300:
            return "Tribune x5"
        elif count < 350:
            return "Tribune x6"
        elif count < 400:
            return "Tribune x7"
        elif count < 450:
            return "Tribune x8"
        elif count < 500:
            return "Tribune x9"
        elif count < 550:
            return "Tribune x10"
        elif count < 750:
            return "Tribune x10+"
        elif count < 1000:
            return "Tribune x15"
        elif count < 1250:
            return "Tribune x20"
        elif count < 1500:
            return "Tribune x25"
        elif count < 1750:
            return "Tribune x30"
        else:
            return "Tribune x30+"

    def _get_next_endorsement_level(self, count: int) -> int:
        """
        Calculate count needed for next endorsement level

        Args:
            count: Current contact count

        Returns:
            Contact count needed for next level
        """
        if count < 50:
            return 50
        elif count < 100:
            return 100
        elif count < 150:
            return 150
        elif count < 200:
            return 200
        elif count < 250:
            return 250
        elif count < 300:
            return 300
        elif count < 350:
            return 350
        elif count < 400:
            return 400
        elif count < 450:
            return 450
        elif count < 500:
            return 500
        elif count < 550:
            return 550
        elif count < 750:
            return 750
        elif count < 1000:
            return 1000
        elif count < 1250:
            return 1250
        elif count < 1500:
            return 1500
        elif count < 1750:
            return 1750
        else:
            return count + 250  # 250-contact increments

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
