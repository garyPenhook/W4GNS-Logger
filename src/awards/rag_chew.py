"""
SKCC Rag Chew Award - Extended CW Conversations with SKCC Members

A rag chew is defined as an on-the-air CW conversation with another SKCC member
lasting 30 minutes or longer, during which both operators use SKCC approved keying devices.

Award Start Date: July 1, 2013 (20130701)
Base Award: 300 minutes accumulated
Endorsements: Every additional 300 minutes (600, 900, etc.)
Single-band Endorsements: 300 minutes per band per endorsement level

Rules:
- Both operators must hold SKCC membership at time of contact
- Minimum duration: 30 minutes for single station, 40 minutes for multi-station QSOs
- Back-to-back contacts with same member prohibited (different member must intervene)
- Exchange: RST, name, location, SKCC number
- Mechanical key policy: straight key, bug, or side swiper only
- CW mode exclusively
- Any amateur band allowed (including WARC bands)
- Duration must be logged in minutes
- Multiple contacts with same member allowed over time (but not back-to-back)
- Endorsements: x2 (600 min), x3 (900 min), etc.
- After x10 (3000 min): increments by 5-minute steps (x15=4500, x20=6000, etc.)
"""

import logging
from typing import Dict, List, Any, Set, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from src.utils.skcc_number import extract_base_skcc_number

from src.awards.base import AwardProgram

logger = logging.getLogger(__name__)


class RagChewAward(AwardProgram):
    """SKCC Rag Chew Award - Extended CW Conversations"""

    def __init__(self, db: Session):
        """
        Initialize Rag Chew award

        Args:
            db: SQLAlchemy database session
        """
        super().__init__(name="Rag Chew Award", program_id="SKCC_RAG_CHEW")
        self.db = db
        # Rag Chew effective date: July 1, 2013
        self.rag_chew_effective_date = datetime(2013, 7, 1)
        self.rag_chew_effective_date_str = "20130701"

        # Constants for duration and endorsements
        self.base_duration = 300  # 300 minutes for base award
        self.endorsement_increment = 300  # Each additional 300 minutes
        self.min_duration = 30  # Minimum 30 minutes per QSO
        self.min_duration_multi = 40  # Minimum 40 minutes for multi-station

    def validate(self, contact: Dict[str, Any]) -> bool:
        """
        Check if a contact qualifies for Rag Chew award

        Requirements:
        - CW mode only
        - SKCC number present on both ends
        - Mechanical key required (STRAIGHT, BUG, or SIDESWIPER)
        - Contact date on or after July 1, 2013
        - Duration must be logged in minutes
        - Duration minimum: 30 minutes
        - Remote station must be SKCC member

        Args:
            contact: Contact record dictionary

        Returns:
            True if contact qualifies for Rag Chew award
        """
        # Must be CW mode
        if contact.get('mode', '').upper() != 'CW':
            logger.debug("Contact not in CW mode for Rag Chew")
            return False

        # Must have SKCC number
        if not contact.get('skcc_number'):
            logger.debug("Contact missing SKCC number for Rag Chew")
            return False

        # CRITICAL RULE: SKCC Mechanical Key Policy
        # Contact must use mechanical key (STRAIGHT, BUG, or SIDESWIPER)
        key_type = contact.get('key_type', '').upper()
        if key_type and key_type not in ['STRAIGHT', 'BUG', 'SIDESWIPER']:
            logger.debug(f"Invalid key type for Rag Chew: {key_type}")
            return False

        # Get contact date for date-based validations
        qso_date = contact.get('qso_date', '')

        # Check contact date (must be on/after July 1, 2013)
        if qso_date and qso_date < self.rag_chew_effective_date_str:
            logger.debug(f"Contact before Rag Chew effective date: {qso_date}")
            return False

        # CRITICAL RULE: Duration must be logged
        duration = contact.get('duration')
        if duration is None:
            logger.debug("Contact missing duration for Rag Chew")
            return False

        # Validate duration is numeric and >= minimum
        try:
            duration_minutes = float(duration)
            if duration_minutes < self.min_duration:
                logger.debug(f"Contact duration too short: {duration_minutes} minutes (minimum {self.min_duration})")
                return False
        except (ValueError, TypeError):
            logger.debug(f"Invalid duration data: {duration}")
            return False

        return True

    def calculate_progress(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate Rag Chew award progress

        Accumulates total duration from all qualifying contacts.
        Enforces back-to-back contact prevention.
        Tracks single-band endorsement progress separately.

        Args:
            contacts: List of contact records (should be sorted by date and time)

        Returns:
            {
                'current': int,              # Total accumulated minutes
                'required': int,             # Required for current level
                'achieved': bool,            # True if base award achieved
                'progress_pct': float,       # Percentage toward base award
                'level': str,                # Base, x2, x3, ... x10, x15, x20, etc.
                'current_minutes': int,      # Total qualified minutes
                'total_contacts': int,       # Number of qualifying contacts
                'band_progress': dict,       # Single-band progress by band
                'back_to_back_rejected': int # Contacts rejected due to back-to-back rule
            }
        """
        # Sort contacts by date and time for back-to-back checking
        sorted_contacts = sorted(
            contacts,
            key=lambda c: (c.get('qso_date', ''), c.get('qso_time', ''))
        )

        total_minutes: float = 0.0
        back_to_back_rejected = 0
        last_contacted_member = None
        qualified_contacts = []
        band_minutes: Dict[str, float] = {}

        for contact in sorted_contacts:
            if self.validate(contact):
                skcc_num = contact.get('skcc_number', '').strip()
                duration_minutes = float(contact.get('duration', 0))
                band = contact.get('band', 'UNKNOWN').upper()

                if skcc_num:
                    # Extract base SKCC number using utility function
                    base_number = extract_base_skcc_number(skcc_num)

                    # CRITICAL RULE: Back-to-back Prevention
                    # Different member must intervene between contacts with same member
                    if base_number == last_contacted_member:
                        logger.debug(
                            f"Back-to-back contact with {base_number} rejected for Rag Chew"
                        )
                        back_to_back_rejected += 1
                        continue  # Skip this contact

                    # This contact qualifies
                    total_minutes += duration_minutes
                    qualified_contacts.append(contact)
                    last_contacted_member = base_number

                    # Track band-specific minutes
                    if band not in band_minutes:
                        band_minutes[band] = 0
                    band_minutes[band] += float(duration_minutes)

        # Determine level based on total minutes
        level_name, required_minutes = self._get_endorsement_level(int(total_minutes))

        # Calculate single-band endorsement progress
        band_progress = {}
        for band, minutes in sorted(band_minutes.items()):
            band_progress[band] = {
                'current': float(minutes),
                'required': self.base_duration,
                'achieved': float(minutes) >= self.base_duration,
                'level': self._get_band_level(int(minutes))
            }

        return {
            'current': int(total_minutes),
            'required': required_minutes,
            'achieved': int(total_minutes) >= self.base_duration,
            'progress_pct': min(100.0, (float(total_minutes) / self.base_duration) * 100),
            'level': level_name,
            'current_minutes': int(total_minutes),
            'total_contacts': len(qualified_contacts),
            'band_progress': band_progress,
            'back_to_back_rejected': back_to_back_rejected,
            'bands_worked': len(band_minutes),
            'band_breakdown': band_minutes
        }

    def _get_endorsement_level(self, minutes: int) -> Tuple[str, int]:
        """
        Calculate endorsement level based on accumulated minutes

        Base: 300 minutes
        x2: 600 minutes
        x3: 900 minutes
        ...
        x10: 3000 minutes
        x15: 4500 minutes (x10 + 5×300 minutes, but after x10: 5×5 minute increments = 4500)
        x20: 6000 minutes (x10 + 10×5 minute increments)
        etc.

        Args:
            minutes: Total accumulated minutes

        Returns:
            Tuple of (level_name, required_minutes_for_current_level)
        """
        if minutes < self.base_duration:
            return "Not Yet", self.base_duration

        # Calculate base levels (x1 through x10)
        base_multiplier = minutes // self.base_duration  # 1, 2, 3, ... 10

        if base_multiplier <= 10:
            if base_multiplier == 1:
                return "Rag Chew", self.base_duration
            else:
                level_name = f"Rag Chew x{base_multiplier}"
                required = base_multiplier * self.base_duration
                return level_name, required

        # After x10 (3000 minutes), calculate with 5-minute increments
        # x15 = 3000 + 5×300 = 4500 (actually 5 more endorsements = 5 units beyond x10)
        # x20 = 3000 + 10×300 = 6000
        # Each unit above x10 = 300 minutes

        # But the rule says "by 5-minute increments after x10"
        # This means: x11 = 3005, x12 = 3010, x13 = 3015, etc.
        # OR x15 = 4500 (meaning 5 endorsements × 300 = 1500, plus base 3000)
        # The official rule states: "x15=4500 minutes; x20=6000 minutes"
        # x15 = 4500 minutes (5 more standard increments beyond x10)
        # x20 = 6000 minutes (10 more standard increments beyond x10)

        # Additional endorsements beyond x10: calculate by 5-minute increments
        minutes_beyond_x10 = minutes - (10 * self.base_duration)  # minutes beyond 3000
        additional_endorsements = minutes_beyond_x10 // 5  # Each 5 minutes = 1 increment
        total_multiplier = 10 + additional_endorsements

        level_name = f"Rag Chew x{total_multiplier}"
        required = minutes  # Current level = current accumulated minutes

        return level_name, required

    def _get_band_level(self, minutes: int) -> str:
        """
        Get single-band endorsement level

        Args:
            minutes: Minutes accumulated on specific band

        Returns:
            Band level name (e.g., "300m" for base, "600m" for first endorsement)
        """
        if minutes < self.base_duration:
            return f"{minutes}m"

        # For single-band, just show the multiplier
        base_multiplier = minutes // self.base_duration
        if base_multiplier == 1:
            return "Base"
        else:
            return f"x{base_multiplier}"

    def get_requirements(self) -> Dict[str, Any]:
        """
        Return Rag Chew award requirements

        Returns:
            Award requirements dictionary
        """
        return {
            'name': 'SKCC Rag Chew Award',
            'description': 'Extended CW conversations with SKCC members lasting 30+ minutes',
            'base_duration': 300,
            'base_duration_multi': 40,
            'base_requirement': '300 minutes accumulated',
            'modes': ['CW'],
            'bands': ['All (including WARC)'],
            'effective_date': 'July 1, 2013 or later',
            'validity_rule': 'Both operators must hold SKCC membership at time of contact',
            'mechanical_key': True,
            'endorsements': {
                'base': '300 minutes',
                'x2': '600 minutes',
                'x3': '900 minutes',
                'x4': '1200 minutes',
                'x5': '1500 minutes',
                'x6': '1800 minutes',
                'x7': '2100 minutes',
                'x8': '2400 minutes',
                'x9': '2700 minutes',
                'x10': '3000 minutes',
                'x15': '4500 minutes (5-minute increments after x10)',
                'x20': '6000 minutes (5-minute increments after x10)',
                'beyond_x10': 'Every 5-minute increment after x10'
            },
            'special_rules': [
                'Back-to-back contacts with same member prohibited',
                'Different member must intervene between contacts with same member',
                'Single-band endorsements available (300 minutes per band)',
                'Duration must be logged in minutes',
                'RST, name, location, and SKCC number must be exchanged'
            ]
        }

    def get_endorsements(self) -> List[Dict[str, Any]]:
        """Return Rag Chew endorsement levels"""
        return [
            {'level': 'Base', 'minutes': 300, 'description': '300 minutes'},
            {'level': 'x2', 'minutes': 600, 'description': '600 minutes'},
            {'level': 'x3', 'minutes': 900, 'description': '900 minutes'},
            {'level': 'x4', 'minutes': 1200, 'description': '1200 minutes'},
            {'level': 'x5', 'minutes': 1500, 'description': '1500 minutes'},
            {'level': 'x10', 'minutes': 3000, 'description': '3000 minutes'},
            {'level': 'x15', 'minutes': 4500, 'description': '4500 minutes'},
            {'level': 'x20', 'minutes': 6000, 'description': '6000 minutes'},
        ]
