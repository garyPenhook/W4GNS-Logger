"""
SKCC PFX Award - Contact SKCC Members with Unique Callsign Prefixes

The PFX Award is earned by accumulating points through contacts with SKCC members
having unique prefixes. Points are calculated as the sum of SKCC numbers for each
unique prefix. Multiple stations sharing a prefix contribute only their highest
SKCC number.

Award Start Date: January 1, 2013 (20130101)
Base Award (Px1): Sum of SKCC numbers > 500,000
Endorsements: Every additional 500,000 points (Px2 at 1,000,000, etc.)
Extended: Beyond Px10 (5,000,000), increment by 5 (Px15, Px20, Px25, etc.)

Rules:
- Both operators must hold SKCC membership at time of contact
- CW mode exclusively
- Mechanical key policy: straight key, bug, or side swiper only
- Club calls and special-event calls do not qualify
- Only contacts made on or after January 1, 2013
- Prefix = letters and numbers up to and including last number on left of callsign
- Prefixes/suffixes separated by "/" are ignored
- Duplicate SKCC number/callsign pairs do not count
- When multiple stations share a prefix, only the highest SKCC number counts
- Contact must appear in membership list as callsign or 'other callsign'
"""

import logging
import re
from typing import Dict, List, Any, Set, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from src.awards.base import AwardProgram

logger = logging.getLogger(__name__)


class PFXAward(AwardProgram):
    """SKCC PFX Award - Prefix-based Point Accumulation"""

    def __init__(self, db: Session):
        """
        Initialize PFX award

        Args:
            db: SQLAlchemy database session
        """
        super().__init__(name="PFX Award", program_id="SKCC_PFX")
        self.db = db
        # PFX effective date: January 1, 2013
        self.pfx_effective_date = datetime(2013, 1, 1)
        self.pfx_effective_date_str = "20130101"

        # Constants for points and endorsements
        self.base_points = 500000  # 500,000 points for base award
        self.endorsement_increment = 500000  # Each additional 500,000 points

        # Club calls and special event calls
        self.special_event_calls: Set[str] = {"K9SKC", "K3Y"}

    def validate(self, contact: Dict[str, Any]) -> bool:
        """
        Check if a contact qualifies for PFX award

        Requirements:
        - CW mode only
        - SKCC number present
        - Mechanical key required (STRAIGHT, BUG, or SIDESWIPER)
        - Contact date on or after January 1, 2013
        - Not a club call or special-event call
        - Callsign has extractable prefix

        Args:
            contact: Contact record dictionary

        Returns:
            True if contact qualifies for PFX award
        """
        # Must be CW mode
        if contact.get('mode', '').upper() != 'CW':
            logger.debug("Contact not in CW mode for PFX")
            return False

        # Must have SKCC number
        if not contact.get('skcc_number'):
            logger.debug("Contact missing SKCC number for PFX")
            return False

        # CRITICAL RULE: SKCC Mechanical Key Policy
        key_type = contact.get('key_type', '').upper()
        if key_type and key_type not in ['STRAIGHT', 'BUG', 'SIDESWIPER']:
            logger.debug(f"Invalid key type for PFX: {key_type}")
            return False

        # Get contact date for date-based validations
        qso_date = contact.get('qso_date', '')

        # Check contact date (must be on/after January 1, 2013)
        if qso_date and qso_date < self.pfx_effective_date_str:
            logger.debug(f"Contact before PFX effective date: {qso_date}")
            return False

        # CRITICAL RULE: Club calls and special-event calls don't qualify
        callsign = contact.get('callsign', '').upper().strip()
        base_call = callsign.split('/')[0] if '/' in callsign else callsign

        if base_call in self.special_event_calls:
            logger.debug(f"Special-event call filtered for PFX: {callsign}")
            return False

        # Callsign must be extractable
        prefix = self._extract_prefix(callsign)
        if not prefix:
            logger.debug(f"No valid prefix extractable from callsign: {callsign}")
            return False

        return True

    def _extract_prefix(self, callsign: str) -> str:
        """
        Extract prefix from callsign

        Prefix = letters and numbers up to and including the last number on the left side.
        Prefixes/suffixes separated by "/" are ignored.

        Examples:
        - AC2C → AC2
        - N6WK → N6
        - DU3/W5LFA → W5 (ignore DU3, use W5)
        - 2D0YLX → 2D0
        - S51AF → S51
        - K5ZMD/7 → K5 (ignore /7)

        Args:
            callsign: Callsign string

        Returns:
            Extracted prefix or empty string if invalid
        """
        if not callsign:
            return ""

        # Uppercase and clean
        callsign = callsign.upper().strip()

        # Handle "/" notation - take the part with numbers (usually the main call)
        if "/" in callsign:
            parts = callsign.split("/")
            # Find the part that has both letters and numbers (the actual call)
            for part in parts:
                if re.search(r'[A-Z0-9]*[0-9][A-Z0-9]*', part):
                    callsign = part
                    break

        # Extract: letters and numbers up to and including the last number on the left
        # Match letters/numbers, find the last digit position
        match = re.match(r'^([A-Z0-9]*[0-9])', callsign)
        if match:
            return match.group(1)

        # No numbers found in callsign
        return ""

    def calculate_progress(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate PFX award progress

        Accumulates points based on sum of SKCC numbers per unique prefix.
        When multiple stations share a prefix, only the highest SKCC number counts.

        Args:
            contacts: List of contact records

        Returns:
            {
                'current': int,              # Total accumulated points
                'required': int,             # Required for current level
                'achieved': bool,            # True if base award achieved
                'progress_pct': float,       # Percentage toward base award
                'level': str,                # Px1, Px2, etc.
                'total_points': int,         # Total points accumulated
                'unique_prefixes': int,      # Number of unique prefixes worked
                'prefix_points': dict,       # Points per prefix
                'skcc_per_prefix': dict,     # SKCC numbers per prefix (highest)
            }
        """
        # Track prefixes and their SKCC numbers
        prefix_skcc_numbers: Dict[str, List[int]] = {}
        prefix_contacts_count: Dict[str, int] = {}

        for contact in contacts:
            if self.validate(contact):
                callsign = contact.get('callsign', '').upper().strip()
                skcc_num_str = contact.get('skcc_number', '').strip()

                if not skcc_num_str:
                    continue

                # Extract prefix
                prefix = self._extract_prefix(callsign)
                if not prefix:
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

                # Initialize prefix tracking if needed
                if prefix not in prefix_skcc_numbers:
                    prefix_skcc_numbers[prefix] = []
                    prefix_contacts_count[prefix] = 0

                # CRITICAL RULE: Track SKCC number for this prefix
                # Only count unique SKCC numbers per prefix (no duplicates)
                if skcc_number_int not in prefix_skcc_numbers[prefix]:
                    prefix_skcc_numbers[prefix].append(skcc_number_int)

                prefix_contacts_count[prefix] += 1

        # Calculate points: sum of highest SKCC numbers per prefix
        # When multiple stations share a prefix, only highest counts
        total_points = 0
        prefix_points: Dict[str, int] = {}
        skcc_per_prefix: Dict[str, int] = {}

        for prefix, skcc_numbers in prefix_skcc_numbers.items():
            # Only the highest SKCC number per prefix counts for points
            highest_skcc = max(skcc_numbers) if skcc_numbers else 0
            points_for_prefix = highest_skcc

            prefix_points[prefix] = points_for_prefix
            skcc_per_prefix[prefix] = highest_skcc
            total_points += points_for_prefix

        # Determine level based on total points
        level_name, required_points = self._get_endorsement_level(total_points)

        return {
            'current': total_points,
            'required': required_points,
            'achieved': total_points >= self.base_points,
            'progress_pct': min(100.0, (total_points / self.base_points) * 100),
            'level': level_name,
            'total_points': total_points,
            'unique_prefixes': len(prefix_skcc_numbers),
            'prefix_points': prefix_points,
            'skcc_per_prefix': skcc_per_prefix,
            'total_contacts': sum(prefix_contacts_count.values()),
            'contacts_per_prefix': prefix_contacts_count,
        }

    def _get_endorsement_level(self, points: int) -> Tuple[str, int]:
        """
        Calculate endorsement level based on accumulated points

        Base: 500,000 points (Px1)
        Px2: 1,000,000 points
        Px3: 1,500,000 points
        ...
        Px10: 5,000,000 points
        Beyond Px10: Increment by 5 (Px15, Px20, Px25, etc.)

        Args:
            points: Total accumulated points

        Returns:
            Tuple of (level_name, required_points_for_current_level)
        """
        if points < self.base_points:
            return "Not Yet", self.base_points

        # Calculate base levels (Px1 through Px10)
        base_multiplier = (points // self.base_points)

        if base_multiplier <= 10:
            if base_multiplier == 1:
                return "PFX", self.base_points
            else:
                level_name = f"PFX x{base_multiplier}"
                required = base_multiplier * self.base_points
                return level_name, required

        # After Px10 (5,000,000 points), calculate with 5-point increments
        # Px15 = 7,500,000 (5 additional endorsements × 500,000)
        # Px20 = 10,000,000 (10 additional endorsements × 500,000)
        # Each increment = 500,000 points (or 5 endorsement levels)

        points_beyond_px10 = points - (10 * self.base_points)  # points beyond 5,000,000
        additional_endorsements = points_beyond_px10 // self.base_points  # Each 500,000 = 1 level
        total_multiplier = 10 + (additional_endorsements * 5)  # In increments of 5

        level_name = f"PFX x{total_multiplier}"
        required = points

        return level_name, required

    def get_requirements(self) -> Dict[str, Any]:
        """
        Return PFX award requirements

        Returns:
            Award requirements dictionary
        """
        return {
            'name': 'SKCC PFX Award',
            'description': 'Contact SKCC members with unique callsign prefixes',
            'base_requirement': '500,000 points (sum of unique prefix SKCC numbers)',
            'modes': ['CW'],
            'bands': ['All'],
            'effective_date': 'January 1, 2013 or later',
            'validity_rule': 'Both operators must hold SKCC membership at time of contact',
            'mechanical_key': True,
            'endorsements': {
                'px1': '500,000 points',
                'px2': '1,000,000 points',
                'px3': '1,500,000 points',
                'px5': '2,500,000 points',
                'px10': '5,000,000 points',
                'px15': '7,500,000 points (5-point increments after Px10)',
                'px20': '10,000,000 points',
                'beyond_px10': 'Every 500,000 points (5-endorsement increments)'
            },
            'special_rules': [
                'Prefix = letters and numbers up to and including last number on left side',
                'Prefixes/suffixes separated by "/" are ignored',
                'Duplicate SKCC number/callsign pairs do not count',
                'When multiple stations share prefix, only highest SKCC number counts',
                'Club calls (K9SKC) and special-event calls ineligible',
                'Points calculated as sum of SKCC numbers per unique prefix',
                'Only the highest SKCC number per prefix contributes to points'
            ]
        }
