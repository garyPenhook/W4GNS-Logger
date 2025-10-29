"""
SKCC Spot Goal/Target Classifier

Determines if an incoming spot is:
- GOAL: You need to work this station (helps your awards)
- TARGET: You can help this station (don't need them for awards)
- BOTH: Mutual benefit
- None: Not relevant to your current awards

Uses QSO database and award eligibility analysis to classify spots.
"""

import logging
from typing import Optional, Set, Dict, Any
from functools import lru_cache
from datetime import datetime, timedelta, timezone

from src.database.repository import DatabaseRepository
from src.utils.skcc_number import get_member_type

logger = logging.getLogger(__name__)


class SpotClassifier:
    """
    Classifies incoming SKCC spots based on award eligibility and contact history
    
    Determines if a spot is:
    - GOAL: Need for current/future awards
    - TARGET: Can help them (don't personally benefit)
    - BOTH: Mutual benefit
    - None: Not relevant
    """

    # Cache timeout: refresh classification every 5 minutes or on new contact
    CACHE_TIMEOUT = 300  # 5 minutes

    def __init__(self, db: DatabaseRepository, my_skcc_number: str):
        """
        Initialize spot classifier

        Args:
            db: Database repository instance
            my_skcc_number: Your SKCC number (e.g., "14947T")
        """
        self.db = db
        self.my_skcc_number = my_skcc_number
        self.last_cache_time = datetime.now(timezone.utc)
        
        # Cached eligibility data
        self._eligibility_cache: Optional[Dict[str, Any]] = None
        self._contacted_callsigns_cache: Optional[Set[str]] = None
        self._contacted_states_cache: Optional[Set[str]] = None
        self._contacted_countries_cache: Optional[Set[str]] = None
        self._classification_cache: Dict[str, str] = {}

    def classify_spot(self, callsign: str, skcc_number: Optional[str] = None) -> Optional[str]:
        """
        Classify an incoming spot as GOAL, TARGET, BOTH, or None

        Args:
            callsign: Remote station callsign (e.g., "K5ABC")
            skcc_number: Optional SKCC number if known (e.g., "12345T")

        Returns:
            "GOAL" - Need this station for awards
            "TARGET" - Can help them, don't need for awards
            "BOTH" - Mutual benefit
            None - Not relevant to current awards
        """
        try:
            # Normalize callsign
            callsign_upper = callsign.upper().strip()

            # Check cache first (unless cache is stale)
            if self._is_cache_valid():
                if callsign_upper in self._classification_cache:
                    logger.debug(f"Spot classifier: Using cached classification for {callsign_upper}")
                    return self._classification_cache[callsign_upper]

            # Not in cache, classify now
            classification = self._classify_internal(callsign_upper, skcc_number)

            # Store in cache (use a sentinel for None to satisfy type expectations)
            self._classification_cache[callsign_upper] = classification or "NONE"

            logger.info(f"Spot classifier: {callsign_upper} classified as {classification}")
            return classification

        except Exception as e:
            logger.error(f"Spot classifier: Error classifying {callsign}: {e}", exc_info=True)
            return None

    def _is_cache_valid(self) -> bool:
        """Check if eligibility cache is still valid"""
        elapsed = (datetime.now(timezone.utc) - self.last_cache_time).total_seconds()
        return elapsed < self.CACHE_TIMEOUT

    def invalidate_cache(self) -> None:
        """Invalidate cache (call after logging new contact)"""
        logger.debug("Spot classifier: Cache invalidated")
        self.last_cache_time = datetime.now(timezone.utc)
        self._eligibility_cache = None
        self._contacted_callsigns_cache = None
        self._contacted_states_cache = None
        self._contacted_countries_cache = None
        self._classification_cache.clear()

    def _classify_internal(self, callsign: str, skcc_number: Optional[str]) -> Optional[str]:
        """
        Internal classification logic

        Args:
            callsign: Uppercase callsign
            skcc_number: Optional SKCC number

        Returns:
            Classification string or None
        """
        # 1. Get contact history
        contact_count = self._get_contact_count(callsign)

        # 2. If heavily contacted, likely TARGET
        if contact_count >= 3:
            logger.debug(f"Spot classifier: {callsign} contacted {contact_count} times → TARGET")
            return "TARGET"

        # 3. Get roster info and check if SKCC member
        roster_entry = self._get_roster_info(callsign, skcc_number)
        if not roster_entry:
            logger.debug(f"Spot classifier: {callsign} not in SKCC roster → SKIP")
            return None

        # 4. Check award needs
        award_needs = self._get_award_needs(roster_entry)

        if not award_needs:
            # No awards need this station
            logger.debug(f"Spot classifier: {callsign} not needed for awards → TARGET")
            return "TARGET"

        # 5. Classify based on contact history + needs
        if contact_count == 0:
            # Never contacted + needed = GOAL
            logger.debug(f"Spot classifier: {callsign} needed for {award_needs} + never contacted → GOAL")
            return "GOAL"
        else:
            # Already contacted + still needed = BOTH
            logger.debug(f"Spot classifier: {callsign} needed for {award_needs} + already contacted → BOTH")
            return "BOTH"

    def _get_contact_count(self, callsign: str) -> int:
        """Get number of times this callsign has been contacted"""
        try:
            contacts = self.db.get_contacts_by_callsign(callsign)
            return len(contacts) if contacts else 0

        except Exception as e:
            logger.debug(f"Error getting contact count for {callsign}: {e}")
            return 0

    def _get_roster_info(self, callsign: str, skcc_number: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Get SKCC roster information for a callsign

        Args:
            callsign: Callsign to look up
            skcc_number: Optional SKCC number if known

        Returns:
            Roster entry dict or None if not found
        """
        try:
            # If SKCC number provided, use it
            if skcc_number:
                member = self.db.skcc_members.get_member(skcc_number)
                if member:
                    return {
                        'callsign': member.get('call_sign', callsign),
                        'skcc_number': skcc_number,
                        'suffix': member.get('current_suffix'),  # C, T, S
                    }

            # Otherwise, search roster for callsign
            member = self.db.skcc_members.get_member_by_callsign(callsign)
            if member:
                return {
                    'callsign': callsign,
                    'skcc_number': member.get('skcc_number'),
                    'suffix': member.get('current_suffix'),  # C, T, S
                }

            return None

        except Exception as e:
            logger.debug(f"Error getting roster info for {callsign}: {e}")
            return None

    def _get_award_needs(self, roster_entry: Dict[str, Any]) -> Optional[str]:
        """
        Determine which awards would benefit from this station

        Args:
            roster_entry: Roster information for station

        Returns:
            Comma-separated list of award needs or None if no needs
        """
        try:
            # Get or refresh eligibility cache
            if self._eligibility_cache is None or not self._is_cache_valid():
                self._eligibility_cache = self.db.analyze_skcc_award_eligibility(self.my_skcc_number)
                self.last_cache_time = datetime.now(timezone.utc)

            eligibility = self._eligibility_cache
            needs = []
            
            # Extract award suffix (C/T/S) from SKCC number using both the suffix and member tables
            # The suffix in the number is not always reliable, so we check the member tables too
            skcc_number = roster_entry.get('skcc_number', '')
            member_type = get_member_type(skcc_number)  # Returns 'C', 'T', 'S', or None from suffix
            
            # Check actual membership status from database tables (more reliable)
            member_status = self.db.check_skcc_member_status(skcc_number)
            is_centurion = member_status['is_centurion'] or member_type == 'C'
            is_tribune = member_status['is_tribune'] or member_type == 'T'
            is_senator = member_status['is_senator'] or member_type == 'S'

            # 1. CENTURION - need any SKCC member (not yet achieved)
            if not eligibility.get('centurion', {}).get('qualified', False):
                needs.append("Centurion")

            # 2. TRIBUNE - ALWAYS need C/T/S members for Tribune endorsements
            # Tribune x1 = 50, x2 = 100, x3 = 150, ... x8 = 400
            # Even after achieving Tribune x1, you need MORE C/T/S contacts for endorsements
            centurion_qualified = eligibility.get('centurion', {}).get('qualified', False)
            is_centurion_tribune_senator = is_centurion or is_tribune or is_senator

            if centurion_qualified and is_centurion_tribune_senator:
                # Check if already achieved Tribune x8 (400 C/T/S contacts)
                # Tribune x8 is the threshold for Senator, so always highlight C/T/S until then
                tribune_count = eligibility.get('tribune', {}).get('count', 0)
                if tribune_count < 400:
                    needs.append("Tribune")

            # 3. SENATOR - need Senator (if Tribune x8 achieved)
            # Senator requires 200 T/S contacts AFTER achieving Tribune x8
            tribune_count = eligibility.get('tribune', {}).get('count', 0)
            senator_not_qualified = not eligibility.get('senator', {}).get('qualified', False)
            is_tribune_or_senator = is_tribune or is_senator

            if tribune_count >= 400 and senator_not_qualified and is_tribune_or_senator:
                needs.append("Senator")

            # 4. TRIPLE KEY - need specific key types (if not yet achieved)
            triple_key_info = eligibility.get('triple_key', {})
            if not triple_key_info.get('qualified', False):
                missing_keys = []
                if triple_key_info.get('straight_key', 0) < 100:
                    missing_keys.append("SK")
                if triple_key_info.get('bug', 0) < 100:
                    missing_keys.append("BUG")
                if triple_key_info.get('sideswiper', 0) < 100:
                    missing_keys.append("SS")
                if missing_keys:
                    needs.append(f"TripleKey-{'/'.join(missing_keys)}")

            # 5. WAS - need missing states
            # NOTE: We don't have state info from SKCC roster, so skip geographic checks
            # These would need to be looked up from contact history or external sources

            # 6. WAC - need missing continents
            # NOTE: Similar limitation - would need external geolocation

            return ", ".join(needs) if needs else None

        except Exception as e:
            logger.debug(f"Error determining award needs: {e}", exc_info=True)
            return None
