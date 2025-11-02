"""
Spot Eligibility Analyzer - Determine Award Relevance of RBN Spots

Analyzes whether a spotted station is needed for any of the user's active awards.
Provides award-specific highlighting and filtering options.

Key Features:
- Checks if spot helps current award progress (e.g., "need 2 more for Centurion")
- Identifies if spot is needed for SKCC Skimmer / Sked modes
- Calculates priority level (CRITICAL, HIGH, MEDIUM, LOW)
- Returns award names and progress for tooltip display
"""

import logging
from typing import Optional, Dict, List, Tuple, Set
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from src.database.repository import DatabaseRepository
from src.skcc.spot_fetcher import SKCCSpot
from src.utils.skcc_number import get_member_type

logger = logging.getLogger(__name__)


class EligibilityLevel(Enum):
    """Priority level for award relevance"""
    CRITICAL = "critical"      # Critical for immediate award (e.g., "need 1 more contact for Centurion")
    HIGH = "high"              # Important for near-term award (within 50 contacts)
    MEDIUM = "medium"          # Helpful but long-term (100+ contacts needed)
    LOW = "low"                # Already worked or not needed for awards
    NONE = "none"              # Not relevant to any awards


@dataclass
class SpotEligibility:
    """Information about a spot's award relevance"""
    spot: SKCCSpot
    callsign: str
    is_eligible: bool          # True if needed for any award
    eligibility_level: EligibilityLevel
    
    # Award-specific information
    needed_for_awards: List[str]  # e.g., ["Centurion", "Tribune"]
    award_progress: Dict[str, str]  # e.g., {"Centurion": "98/100 contacts"}
    
    # Matching information
    is_worked: bool            # True if already worked this callsign
    worked_count: int          # Number of times worked
    worked_recently: bool      # True if worked in recent_days
    worked_days_ago: Optional[int]
    
    # Display information
    highlight_color: Optional[Tuple[int, int, int, int]]  # RGBA format
    tooltip_text: str          # Human-readable description


class SpotEligibilityAnalyzer:
    """
    Determines if a spotted station is needed for any of the user's awards.
    
    Enables intelligent highlighting and filtering of RBN spots based on:
    - Current award progress (e.g., "need 2 more for Centurion")
    - Contact history (already worked?)
    - Award prerequisites (Tribune requires Centurion first)
    - User preferences (highlight recent/frequent contacts?)
    """

    # Cache validity timeout
    CACHE_TIMEOUT = 1800  # 30 minutes (award eligibility changes infrequently)

    def __init__(self, db: DatabaseRepository, config_manager, my_callsign: str, my_skcc_number: str):
        """
        Initialize spot eligibility analyzer

        Args:
            db: Database repository for lookups
            config_manager: Configuration manager for user settings
            my_callsign: User's callsign (e.g., "W4GNS")
            my_skcc_number: User's SKCC number (e.g., "14947T")
        """
        self.db = db
        self.config_manager = config_manager
        self.my_callsign = my_callsign.upper()
        self.my_skcc_number = my_skcc_number

        # Cache eligibility data
        self._eligibility_cache: Optional[Dict] = None
        self._cache_timestamp: Optional[datetime] = None

        # Cache contact/worked callsigns
        self._worked_callsigns: Set[str] = set()
        self._contact_dates: Dict[str, str] = {}  # callsign -> YYYYMMDD of last contact
        self._contact_counts: Dict[str, int] = {}  # callsign -> total contact count

        # User preferences for highlighting
        self.highlight_worked = config_manager.get("spots.highlight_worked", True)
        self.highlight_recent_days = config_manager.get("spots.highlight_recent_days", 30)
        self.highlight_by_award = config_manager.get("spots.highlight_by_award", True)
        self.enable_eligibility = config_manager.get("spots.enable_award_eligibility", True)

        logger.info(f"SpotEligibilityAnalyzer initialized for {my_callsign} ({my_skcc_number})")

    def reload_config(self) -> None:
        """Reload preferences from config"""
        self.highlight_worked = self.config_manager.get("spots.highlight_worked", True)
        self.highlight_recent_days = self.config_manager.get("spots.highlight_recent_days", 30)
        self.highlight_by_award = self.config_manager.get("spots.highlight_by_award", True)
        self.enable_eligibility = self.config_manager.get("spots.enable_award_eligibility", True)
        logger.debug("SpotEligibilityAnalyzer config reloaded")

    def analyze_spot(self, spot: SKCCSpot) -> SpotEligibility:
        """
        Analyze whether a spotted station is needed for any award.

        Args:
            spot: SKCCSpot to analyze

        Returns:
            SpotEligibility with award relevance information
        """
        try:
            callsign = spot.callsign.upper().strip()

            # Check if we've worked this callsign before
            is_worked = self._is_worked(callsign)
            worked_count = self._get_contact_count(callsign)
            worked_recently, worked_days_ago = self._is_recently_worked(callsign)

            # Get award eligibility info
            eligibility = self._get_award_eligibility()
            needed_for_awards, award_progress = self._check_award_needs(callsign, eligibility, is_worked)

            # Determine eligibility level
            eligibility_level = self._calculate_eligibility_level(
                is_worked, worked_recently, worked_count, len(needed_for_awards), eligibility
            )

            # Get highlight color
            highlight_color = self._get_highlight_color(eligibility_level, is_worked, worked_recently)

            # Generate tooltip
            tooltip = self._generate_tooltip(
                callsign, is_worked, worked_count, worked_days_ago, needed_for_awards, award_progress
            )

            is_eligible = len(needed_for_awards) > 0

            return SpotEligibility(
                spot=spot,
                callsign=callsign,
                is_eligible=is_eligible,
                eligibility_level=eligibility_level,
                needed_for_awards=needed_for_awards,
                award_progress=award_progress,
                is_worked=is_worked,
                worked_count=worked_count,
                worked_recently=worked_recently,
                worked_days_ago=worked_days_ago,
                highlight_color=highlight_color,
                tooltip_text=tooltip
            )

        except Exception as e:
            logger.error(f"Error analyzing spot {spot.callsign}: {e}", exc_info=True)
            return SpotEligibility(
                spot=spot,
                callsign=spot.callsign,
                is_eligible=False,
                eligibility_level=EligibilityLevel.NONE,
                needed_for_awards=[],
                award_progress={},
                is_worked=False,
                worked_count=0,
                worked_recently=False,
                worked_days_ago=None,
                highlight_color=None,
                tooltip_text="Error analyzing spot"
            )

    def _is_worked(self, callsign: str) -> bool:
        """Check if we've worked this callsign before"""
        self._refresh_contact_cache_if_needed()
        return callsign in self._worked_callsigns

    def _get_contact_count(self, callsign: str) -> int:
        """Get number of times we've worked this callsign"""
        self._refresh_contact_cache_if_needed()
        return self._contact_counts.get(callsign, 0)

    def _is_recently_worked(self, callsign: str) -> Tuple[bool, Optional[int]]:
        """
        Check if recently worked

        Returns:
            Tuple of (is_recent, days_ago)
        """
        self._refresh_contact_cache_if_needed()

        if callsign not in self._contact_dates:
            return False, None

        last_contact = self._contact_dates[callsign]
        try:
            contact_date = datetime.strptime(last_contact, "%Y%m%d").replace(tzinfo=timezone.utc)
            days_ago = (datetime.now(timezone.utc) - contact_date).days
            is_recent = days_ago <= self.highlight_recent_days
            return is_recent, days_ago
        except Exception as e:
            logger.debug(f"Error parsing contact date {last_contact}: {e}")
            return False, None

    def _get_award_eligibility(self) -> Dict:
        """
        Get current award eligibility status.
        Cached for performance.
        """
        now = datetime.now(timezone.utc)

        if (self._eligibility_cache is None or self._cache_timestamp is None or
            (now - self._cache_timestamp).total_seconds() > self.CACHE_TIMEOUT):

            try:
                self._eligibility_cache = self.db.analyze_skcc_award_eligibility(self.my_skcc_number)
                self._cache_timestamp = now
                logger.debug("Award eligibility cache refreshed")
            except Exception as e:
                logger.error(f"Error getting award eligibility: {e}", exc_info=True)
                self._eligibility_cache = {}

        return self._eligibility_cache or {}

    def _check_award_needs(
        self, callsign: str, eligibility: Dict, is_worked: bool
    ) -> Tuple[List[str], Dict[str, str]]:
        """
        Check which awards would benefit from this callsign.

        Returns:
            Tuple of (needed_for_awards, award_progress)
            Example: (["Centurion", "Tribune"], {"Centurion": "98/100 contacts", "Tribune": "45/100 Tribune members"})
        """
        needed_for_awards = []
        award_progress = {}

        try:
            # Get roster info for the spotted station
            member = self.db.skcc_members.get_member_by_callsign(callsign)
            if not member:
                # Not a SKCC member, skip award checks
                return [], {}

            # Extract award suffix (C/T/S) from SKCC number using both the suffix and member tables
            # The suffix in the number is not always reliable, so we check the member tables too
            skcc_number = member.get('skcc_number', '')
            member_type = get_member_type(skcc_number)  # Returns 'C', 'T', 'S', or None from suffix
            
            # Check actual membership status from database tables (more reliable)
            member_status = self.db.check_skcc_member_status(skcc_number)
            is_centurion = member_status['is_centurion'] or member_type == 'C'
            is_tribune = member_status['is_tribune'] or member_type == 'T'
            is_senator = member_status['is_senator'] or member_type == 'S'

            # 1. CENTURION - need any SKCC member (not yet achieved)
            centurion = eligibility.get('centurion', {})
            if not centurion.get('qualified', False):
                current = centurion.get('current_contacts', 0)
                required = centurion.get('required_contacts', 100)
                remaining = required - current

                needed_for_awards.append("Centurion")
                award_progress["Centurion"] = f"{current}/{required} contacts (need {remaining} more)"

                # Log criticality
                if remaining <= 5:
                    logger.info(f"CRITICAL: {callsign} helps Centurion ({remaining} remaining)")

            # 2. TRIBUNE - ALWAYS need C/T/S members for Tribune endorsements
            # Tribune x1 = 50, x2 = 100, x3 = 150, ... x8 = 400
            # Even after achieving Tribune x1, you need MORE C/T/S contacts for endorsements
            if centurion.get('qualified', False):
                tribune = eligibility.get('tribune', {})
                tribune_count = tribune.get('current_contacts', 0)
                
                # Always highlight C/T/S members until Tribune x8 (400 contacts) is achieved
                # Tribune x8 is the prerequisite for Senator award
                if tribune_count < 400 and (is_centurion or is_tribune or is_senator):
                    required = tribune.get('required_contacts', 100)
                    remaining = max(0, required - tribune_count)

                    needed_for_awards.append("Tribune")
                    award_progress["Tribune"] = f"{tribune_count}/{required}+ C/T/S (x8 at 400)"

            # 3. SENATOR - need T/S members AFTER Tribune x8 (400 C/T/S contacts)
            if centurion.get('qualified', False):
                tribune = eligibility.get('tribune', {})
                tribune_count = tribune.get('current_contacts', 0)
                
                # Senator only applies AFTER Tribune x8 is achieved
                if tribune_count >= 400:
                    senator = eligibility.get('senator', {})
                    if not senator.get('qualified', False) and (is_tribune or is_senator):
                        current = senator.get('current_contacts', 0)
                        required = senator.get('required_contacts', 200)
                        remaining = required - current

                        needed_for_awards.append("Senator")
                        award_progress["Senator"] = f"{current}/{required} T/S (need {remaining})"

            # 4. TRIPLE KEY - check by key type
            triple_key = eligibility.get('triple_key', {})
            if not triple_key.get('qualified', False):
                key_type = member.get('key_type', '').upper()

                if key_type == 'SK':  # Straight Key
                    sk_count = triple_key.get('straight_key', 0)
                    sk_needed = triple_key.get('straight_key_required', 100)
                    if sk_count < sk_needed:
                        needed_for_awards.append("Triple Key (Straight)")
                        award_progress["Triple Key (Straight)"] = f"{sk_count}/{sk_needed} SK"

                elif key_type == 'BUG':  # Bug
                    bug_count = triple_key.get('bug', 0)
                    bug_needed = triple_key.get('bug_required', 100)
                    if bug_count < bug_needed:
                        needed_for_awards.append("Triple Key (Bug)")
                        award_progress["Triple Key (Bug)"] = f"{bug_count}/{bug_needed} Bug"

                elif key_type == 'SS':  # Sideswiper
                    ss_count = triple_key.get('sideswiper', 0)
                    ss_needed = triple_key.get('sideswiper_required', 100)
                    if ss_count < ss_needed:
                        needed_for_awards.append("Triple Key (Sideswiper)")
                        award_progress["Triple Key (Sideswiper)"] = f"{ss_count}/{ss_needed} SS"

            return needed_for_awards, award_progress

        except Exception as e:
            logger.error(f"Error checking award needs for {callsign}: {e}", exc_info=True)
            return [], {}

    def _calculate_eligibility_level(
        self, is_worked: bool, worked_recently: bool, worked_count: int,
        award_count: int, eligibility: Dict
    ) -> EligibilityLevel:
        """Determine eligibility level based on multiple factors"""

        # Already worked and recent = already in logbook
        if is_worked and worked_recently:
            return EligibilityLevel.LOW

        # Worked multiple times = probably not critical
        if worked_count >= 3:
            return EligibilityLevel.LOW

        # Not needed for any awards
        if award_count == 0:
            return EligibilityLevel.NONE

        # Needed for awards - check criticality
        centurion = eligibility.get('centurion', {})
        remaining = (centurion.get('required_contacts', 100) -
                    centurion.get('current_contacts', 0))

        if remaining <= 5:
            return EligibilityLevel.CRITICAL
        elif remaining <= 20:
            return EligibilityLevel.HIGH
        elif remaining <= 50:
            return EligibilityLevel.MEDIUM
        else:
            return EligibilityLevel.MEDIUM

    def _generate_tooltip(
        self, callsign: str, is_worked: bool, worked_count: int,
        worked_days_ago: Optional[int], needed_for_awards: List[str],
        award_progress: Dict[str, str]
    ) -> str:
        """Generate human-readable tooltip for the spot"""

        lines = [f"📍 {callsign}"]

        if is_worked:
            if worked_count == 1:
                lines.append(f"✓ Worked once")
            else:
                lines.append(f"✓ Worked {worked_count} times")

            if worked_days_ago is not None:
                if worked_days_ago == 0:
                    lines.append("  (TODAY)")
                elif worked_days_ago == 1:
                    lines.append("  (Yesterday)")
                else:
                    lines.append(f"  ({worked_days_ago} days ago)")

        if needed_for_awards:
            lines.append("")
            lines.append("🎯 AWARD OPPORTUNITIES:")
            for award in needed_for_awards:
                progress = award_progress.get(award, "")
                if progress:
                    lines.append(f"  • {award}: {progress}")
                else:
                    lines.append(f"  • {award}")
        else:
            if not is_worked:
                lines.append("")
                lines.append("ℹ️ Not needed for current awards")

        return "\n".join(lines)

    def _refresh_contact_cache_if_needed(self) -> None:
        """Refresh contact cache if needed"""
        try:
            contacts = self.db.get_all_contacts()

            self._worked_callsigns.clear()
            self._contact_dates.clear()
            self._contact_counts.clear()

            for contact in contacts:
                callsign = contact.callsign.upper()
                self._worked_callsigns.add(callsign)

                # Count total contacts with this callsign
                count = self._contact_counts.get(callsign, 0)
                self._contact_counts[callsign] = count + 1

                # Track most recent contact date
                qso_date = getattr(contact, 'qso_date', None)
                if qso_date:
                    if callsign not in self._contact_dates or qso_date > self._contact_dates[callsign]:
                        self._contact_dates[callsign] = qso_date

            logger.debug(f"Contact cache refreshed: {len(self._worked_callsigns)} unique callsigns")

        except Exception as e:
            logger.error(f"Error refreshing contact cache: {e}", exc_info=True)

    def get_statistics(self) -> Dict[str, int]:
        """Get analyzer statistics for debugging"""
        self._refresh_contact_cache_if_needed()
        return {
            "worked_callsigns": len(self._worked_callsigns),
            "cache_age_seconds": int((datetime.now(timezone.utc) - self._cache_timestamp).total_seconds())
                if self._cache_timestamp else -1,
        }

    def invalidate_cache(self) -> None:
        """Clear all caches (call after logging new contact or award update)"""
        self._eligibility_cache = None
        self._cache_timestamp = None
        self._worked_callsigns.clear()
        self._contact_dates.clear()
        self._contact_counts.clear()
        logger.info("SpotEligibilityAnalyzer caches invalidated")
