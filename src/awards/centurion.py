"""
SKCC Centurion Award - Contact 100+ Different SKCC Members

The Centurion award is earned by making contact with 100 different SKCC members.
Endorsements are available in 100-contact increments up to Centurion x10,
then in 500-contact increments (Cx15, Cx20, etc.).

Rules:
- Both operators must hold SKCC membership
- Exchanges must include SKCC numbers
- QSOs must be CW mode only
- Any band(s) allowed
- Each call sign counts only once (per category)
"""

from typing import Dict, List, Any
from sqlalchemy.orm import Session

from src.awards.base import AwardProgram


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

    def validate(self, contact: Dict[str, Any]) -> bool:
        """
        Check if a contact qualifies for Centurion award

        Requirements:
        - CW mode only
        - SKCC number present on both sides (in skcc_number field and contact's SKCC number)
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

        # Remote station must be a valid SKCC member (they have a SKCC number in the contact)
        # This is assumed to be present if the contact was logged in SKCC context
        if not contact.get('skcc_number'):
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
                    # Extract base number (remove suffix like C, T, S, x10, etc.)
                    base_number = skcc_number.split()[0].rstrip('CTSx0123456789')
                    if base_number:
                        unique_members.add(base_number)

        current_count = len(unique_members)
        required_count = 100

        # Determine endorsement level
        endorsement_level = self._get_endorsement_level(current_count)

        return {
            'current': current_count,
            'required': required_count,
            'achieved': current_count >= required_count,
            'progress_pct': min(100.0, (current_count / required_count) * 100),
            'endorsement': endorsement_level,
            'unique_members': unique_members,
            'next_level_count': self._get_next_endorsement_level(current_count)
        }

    def _get_endorsement_level(self, count: int) -> str:
        """
        Calculate endorsement level based on contact count

        Levels:
        - Base: 100 (Centurion)
        - Endorsements: 200 (Cx2), 300 (Cx3), ... 1000 (Cx10)
        - Higher: 1500 (Cx15), 2000 (Cx20), etc.

        Args:
            count: Number of unique SKCC members contacted

        Returns:
            Endorsement level string (e.g., "Centurion", "Cx2", "Cx10")
        """
        if count < 100:
            return "Not Yet"
        elif count < 200:
            return "Centurion"
        elif count < 300:
            return "Centurion x2"
        elif count < 400:
            return "Centurion x3"
        elif count < 500:
            return "Centurion x4"
        elif count < 600:
            return "Centurion x5"
        elif count < 700:
            return "Centurion x6"
        elif count < 800:
            return "Centurion x7"
        elif count < 900:
            return "Centurion x8"
        elif count < 1000:
            return "Centurion x9"
        elif count < 1100:
            return "Centurion x10"
        elif count < 1500:
            return "Centurion x10+"
        elif count < 2000:
            return "Centurion x15"
        elif count < 2500:
            return "Centurion x20"
        elif count < 3000:
            return "Centurion x25"
        elif count < 3500:
            return "Centurion x30"
        elif count < 4000:
            return "Centurion x35"
        elif count < 4500:
            return "Centurion x40"
        else:
            return "Centurion x40+"

    def _get_next_endorsement_level(self, count: int) -> int:
        """
        Calculate count needed for next endorsement level

        Args:
            count: Current contact count

        Returns:
            Contact count needed for next level
        """
        if count < 100:
            return 100
        elif count < 200:
            return 200
        elif count < 300:
            return 300
        elif count < 400:
            return 400
        elif count < 500:
            return 500
        elif count < 600:
            return 600
        elif count < 700:
            return 700
        elif count < 800:
            return 800
        elif count < 900:
            return 900
        elif count < 1000:
            return 1000
        elif count < 1100:
            return 1100
        elif count < 1500:
            return 1500
        elif count < 2000:
            return 2000
        elif count < 2500:
            return 2500
        elif count < 3000:
            return 3000
        elif count < 3500:
            return 3500
        elif count < 4000:
            return 4000
        elif count < 4500:
            return 4500
        else:
            return count + 500  # 500-contact increments

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
