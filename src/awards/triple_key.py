"""
SKCC Triple Key Award - Contacts Using Three Key Types

The Triple Key Award promotes the use of all three SKCC accepted key types:
- Straight Key (SK)
- Semi-automatic/Bug (BUG)
- Sideswiper (SS)

Requirements:
- 100 different SKCC members contacted using a straight key
- 100 different SKCC members contacted using a bug
- 100 different SKCC members contacted using a sideswiper
- Total: 300 different SKCC members across all three key types

Rules:
- Both operators must hold SKCC membership at time of contact
- Exchanges must include key type (or abbreviations: SK, BUG, SS)
- QSOs must be CW mode only
- Contacts must be made on or after November 10, 2018
- Each SKCC member counted once per key type (no duplicate SKCC numbers for same key type)
- Remote stations don't need to be participating in the award
"""

import logging
from typing import Dict, List, Any, Set, Tuple
from sqlalchemy.orm import Session

from src.awards.base import AwardProgram

logger = logging.getLogger(__name__)


class TripleKeyAward(AwardProgram):
    """SKCC Triple Key Award - Contacts using all three mechanical key types"""

    def __init__(self, db: Session):
        """
        Initialize Triple Key award

        Args:
            db: SQLAlchemy database session
        """
        super().__init__(name="Triple Key Award", program_id="SKCC_TRIPLE_KEY")
        self.db = db
        # Triple Key effective date: November 10, 2018
        self.triple_key_effective_date_str = "20181110"

        # Constants for award
        self.members_per_key_type = 100  # 100 unique members per key type
        self.total_members_required = 300  # 300 total unique members

    def validate(self, contact: Dict[str, Any]) -> bool:
        """
        Check if a contact qualifies for Triple Key award

        Requirements:
        - CW mode only
        - SKCC number present on both sides
        - Mechanical key required (STRAIGHT, BUG, or SIDESWIPER)
        - Contact date on or after November 10, 2018
        - Valid key type must be specified

        Args:
            contact: Contact record dictionary

        Returns:
            True if contact qualifies for Triple Key award
        """
        # Must be CW mode
        if contact.get('mode', '').upper() != 'CW':
            logger.debug("Contact not in CW mode for Triple Key")
            return False

        # Must have SKCC number
        if not contact.get('skcc_number'):
            logger.debug("Contact missing SKCC number for Triple Key")
            return False

        # CRITICAL RULE: Must have valid mechanical key type (STRAIGHT, BUG, or SIDESWIPER)
        key_type = contact.get('key_type', '').upper()
        if key_type not in ['STRAIGHT', 'BUG', 'SIDESWIPER']:
            logger.debug(f"Invalid or missing key type for Triple Key: {key_type}")
            return False

        # Get contact date for date-based validations
        qso_date = contact.get('qso_date', '')

        # Check contact date (must be on/after November 10, 2018)
        if qso_date and qso_date < self.triple_key_effective_date_str:
            logger.debug(f"Contact before Triple Key effective date: {qso_date}")
            return False

        return True

    def calculate_progress(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate Triple Key award progress

        Tracks unique SKCC members contacted with each key type:
        - Straight Key members
        - Bug members
        - Sideswiper members

        Args:
            contacts: List of contact records

        Returns:
            {
                'current': int,              # Total unique members across all key types
                'required': int,             # 300 total unique members
                'achieved': bool,            # True if all three key types reach 100
                'progress_pct': float,       # Percentage (0-100)
                'level': str,                # "Triple Key" or "Not Yet"
                'straight_key_members': int, # Unique members with straight key
                'bug_members': int,          # Unique members with bug
                'sideswiper_members': int,   # Unique members with sideswiper
                'total_unique_members': int, # Total unique members (union)
                'straight_key_progress_pct': float,  # Percent toward 100
                'bug_progress_pct': float,           # Percent toward 100
                'sideswiper_progress_pct': float,    # Percent toward 100
            }
        """
        # Track unique SKCC members for each key type
        straight_key_members: Set[int] = set()
        bug_members: Set[int] = set()
        sideswiper_members: Set[int] = set()

        for contact in contacts:
            if self.validate(contact):
                skcc_num_str = contact.get('skcc_number', '').strip()
                key_type = contact.get('key_type', '').upper()

                if not skcc_num_str or not key_type:
                    continue

                # Extract numeric SKCC number (remove C/T/S/x suffixes)
                base_number = skcc_num_str.split()[0]
                if base_number and base_number[-1] in 'CTS':
                    base_number = base_number[:-1]
                if base_number and 'x' in base_number:
                    base_number = base_number.split('x')[0]

                if not base_number or not base_number.isdigit():
                    continue

                skcc_number_int = int(base_number)

                # Track this member for their key type
                # CRITICAL RULE: Each SKCC member counted only once per key type
                if key_type == 'STRAIGHT':
                    straight_key_members.add(skcc_number_int)
                elif key_type == 'BUG':
                    bug_members.add(skcc_number_int)
                elif key_type == 'SIDESWIPER':
                    sideswiper_members.add(skcc_number_int)

        # Calculate totals
        straight_count = len(straight_key_members)
        bug_count = len(bug_members)
        sideswiper_count = len(sideswiper_members)

        # Total unique members (union of all three sets)
        all_members = straight_key_members | bug_members | sideswiper_members
        total_unique = len(all_members)

        # Determine if award is achieved (all three key types must have 100+ members)
        achieved = (
            straight_count >= self.members_per_key_type
            and bug_count >= self.members_per_key_type
            and sideswiper_count >= self.members_per_key_type
        )

        # Calculate level and required points
        if achieved:
            level_name = "Triple Key"
            required = self.total_members_required
        else:
            level_name = "Not Yet"
            required = self.total_members_required

        return {
            'current': total_unique,
            'required': required,
            'achieved': achieved,
            'progress_pct': min(100.0, (total_unique / self.total_members_required) * 100),
            'level': level_name,
            'straight_key_members': straight_count,
            'bug_members': bug_count,
            'sideswiper_members': sideswiper_count,
            'total_unique_members': total_unique,
            'straight_key_progress_pct': min(100.0, (straight_count / self.members_per_key_type) * 100),
            'bug_progress_pct': min(100.0, (bug_count / self.members_per_key_type) * 100),
            'sideswiper_progress_pct': min(100.0, (sideswiper_count / self.members_per_key_type) * 100),
        }

    def get_requirements(self) -> Dict[str, Any]:
        """
        Return Triple Key award requirements

        Returns:
            Award requirements dictionary
        """
        return {
            'name': 'SKCC Triple Key Award',
            'description': 'Contact 100 unique SKCC members with each of three key types',
            'base_requirement': '100 members per key type; 300 total unique members',
            'modes': ['CW'],
            'bands': ['All'],
            'effective_date': 'November 10, 2018 or later',
            'validity_rule': 'Both operators must hold SKCC membership at time of contact',
            'mechanical_key': True,
            'key_types_required': ['STRAIGHT', 'BUG', 'SIDESWIPER'],
            'special_rules': [
                'Straight Key: 100 different SKCC members',
                'Bug (Semi-automatic): 100 different SKCC members',
                'Sideswiper: 100 different SKCC members',
                'Total: 300 different SKCC members across all three key types',
                'Each SKCC member counted once per key type',
                'Members can be worked with multiple key types',
                'Remote stations do not need to be participating in award',
                'Exchanges should include key type (SK, BUG, or SS acceptable)'
            ]
        }
