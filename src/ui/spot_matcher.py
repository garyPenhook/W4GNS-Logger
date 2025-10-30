"""
Spot Matcher - Compare RBN Spots with User Contacts and Award Eligibility

Identifies RBN spots that:
1. Correspond to contacts already worked (visual feedback for duplicates)
2. Help with current award progress (GOAL/TARGET/BOTH classification)
3. Are critical for near-term award qualification

Enables intelligent highlighting based on contact history and award goals.
"""

import logging
from typing import Optional, Dict, Set, List, Tuple, TYPE_CHECKING
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

from src.database.repository import DatabaseRepository
from src.skcc.spot_fetcher import SKCCSpot

if TYPE_CHECKING:
    from src.ui.spot_eligibility_analyzer import SpotEligibilityAnalyzer, SpotEligibility

logger = logging.getLogger(__name__)


@dataclass
class SpotMatch:
    """Information about a spot-contact match"""
    spot: SKCCSpot
    match_type: str  # "WORKED" | "RECENT" | "NONE"
    contact_date: Optional[str] = None  # YYYYMMDD format
    last_worked_days_ago: Optional[int] = None
    callsign: str = ""  # Contact callsign


class SpotMatcher:
    """
    Compares RBN spots against user's contact database.
    
    Enables highlighting of spots for stations already worked,
    providing quick visual feedback on whether a spotted station
    is a duplicate or new potential contact.
    """

    def __init__(self, db: DatabaseRepository, config_manager, my_callsign: Optional[str] = None,
                 my_skcc_number: Optional[str] = None):
        """
        Initialize spot matcher

        Args:
            db: Database repository for contact lookups
            config_manager: Configuration manager for user settings
            my_callsign: User's callsign (optional, for award eligibility analysis)
            my_skcc_number: User's SKCC number (optional, for award eligibility analysis)
        """
        self.db = db
        self.config_manager = config_manager

        # OPTIMIZED: Use database queries instead of in-memory cache
        # This eliminates the need to load all 10,000+ contacts into memory
        # Small LRU cache for recently queried callsigns (max 1000 entries)
        self._recent_lookups: Dict[str, Tuple[bool, Optional[str]]] = {}  # callsign -> (worked, last_date)
        self._recent_lookups_max_size = 1000

        # Highlighting preferences
        self.highlight_worked = config_manager.get("spots.highlight_worked", True)
        self.highlight_recent_days = config_manager.get("spots.highlight_recent_days", 30)
        self.enable_matching = config_manager.get("spots.enable_matching", True)

        # Award eligibility analyzer (optional, lazy-loaded)
        self.eligibility_analyzer: Optional['SpotEligibilityAnalyzer'] = None
        self._my_callsign = my_callsign
        self._my_skcc_number = my_skcc_number

        logger.info(f"SpotMatcher initialized (OPTIMIZED): highlight_worked={self.highlight_worked}, "
                   f"recent_days={self.highlight_recent_days}, award_eligibility_available={bool(my_skcc_number)}")

    def reload_config(self) -> None:
        """Reload highlighting preferences from config"""
        self.highlight_worked = self.config_manager.get("spots.highlight_worked", True)
        self.highlight_recent_days = self.config_manager.get("spots.highlight_recent_days", 30)
        self.enable_matching = self.config_manager.get("spots.enable_matching", True)
        logger.debug("SpotMatcher config reloaded")

    def match_spot(self, spot: SKCCSpot) -> SpotMatch:
        """
        Check if a spot matches a contact in the database (OPTIMIZED: on-demand query)

        Args:
            spot: SKCCSpot object to check

        Returns:
            SpotMatch object with matching information
        """
        if not self.enable_matching:
            return SpotMatch(
                spot=spot,
                match_type="NONE",
                callsign=spot.callsign
            )

        callsign = spot.callsign.upper()

        # OPTIMIZED: Check recent lookups cache first (LRU cache)
        if callsign in self._recent_lookups:
            worked, contact_date = self._recent_lookups[callsign]
            if not worked:
                return SpotMatch(
                    spot=spot,
                    match_type="NONE",
                    callsign=callsign
                )
        else:
            # Query database for this specific callsign (indexed query)
            worked, contact_date = self._query_callsign_worked(callsign)

            # Add to LRU cache
            self._add_to_recent_lookups(callsign, worked, contact_date)

            if not worked:
                return SpotMatch(
                    spot=spot,
                    match_type="NONE",
                    callsign=callsign
                )

        if not contact_date:
            # Worked but no date available
            return SpotMatch(
                spot=spot,
                match_type="WORKED",
                callsign=callsign,
                contact_date=None
            )

        # Check if it's a recent contact
        try:
            contact_datetime = datetime.strptime(contact_date, "%Y%m%d").replace(tzinfo=timezone.utc)
            days_ago = (datetime.now(timezone.utc) - contact_datetime).days

            if days_ago <= self.highlight_recent_days:
                return SpotMatch(
                    spot=spot,
                    match_type="RECENT",
                    callsign=callsign,
                    contact_date=contact_date,
                    last_worked_days_ago=days_ago
                )
            else:
                return SpotMatch(
                    spot=spot,
                    match_type="WORKED",
                    callsign=callsign,
                    contact_date=contact_date,
                    last_worked_days_ago=days_ago
                )
        except Exception as e:
            logger.error(f"Error parsing contact date {contact_date}: {e}")
            return SpotMatch(
                spot=spot,
                match_type="WORKED",
                callsign=callsign,
                contact_date=contact_date
            )

    def get_highlight_color(self, match: SpotMatch) -> Optional[Tuple[int, int, int, int]]:
        """
        Get highlight color for a matched spot (RGBA format)

        Args:
            match: SpotMatch object

        Returns:
            Tuple of (R, G, B, Alpha) or None if no highlighting
        """
        if match.match_type == "RECENT":
            # Recently worked: bright yellow/orange
            return (255, 200, 0, 120)  # RGBA

        elif match.match_type == "WORKED":
            # Previously worked: light orange
            return (255, 160, 0, 80)  # RGBA

        else:
            # No match: no highlighting
            return None

    def get_match_tooltip(self, match: SpotMatch) -> str:
        """
        Get tooltip text describing the spot match

        Args:
            match: SpotMatch object

        Returns:
            Human-readable match description
        """
        if match.match_type == "RECENT":
            if match.last_worked_days_ago == 0:
                return f"✓ Worked TODAY ({match.callsign})"
            elif match.last_worked_days_ago == 1:
                return f"✓ Worked YESTERDAY ({match.callsign})"
            else:
                return f"✓ Worked {match.last_worked_days_ago} days ago ({match.callsign})"

        elif match.match_type == "WORKED":
            if match.last_worked_days_ago:
                return f"✓ Previously worked {match.last_worked_days_ago} days ago ({match.callsign})"
            else:
                return f"✓ Worked before ({match.callsign})"

        else:
            return f"New opportunity: {match.callsign}"

    def _query_callsign_worked(self, callsign: str) -> Tuple[bool, Optional[str]]:
        """
        Query database to check if callsign has been worked (OPTIMIZED: single callsign query)

        Args:
            callsign: Callsign to check (already uppercased)

        Returns:
            Tuple of (worked: bool, last_date: Optional[str])
        """
        try:
            session = self.db.get_session()
            try:
                from src.database.models import Contact
                from sqlalchemy.sql import func

                # OPTIMIZED: Use indexed query with MAX aggregate
                # This uses the callsign index for fast lookup
                result = session.query(func.max(Contact.qso_date)).filter(
                    func.upper(Contact.callsign) == callsign
                ).scalar()

                if result:
                    return (True, result)
                else:
                    return (False, None)

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error querying callsign {callsign}: {e}", exc_info=True)
            return (False, None)

    def _add_to_recent_lookups(self, callsign: str, worked: bool, last_date: Optional[str]) -> None:
        """
        Add callsign lookup result to LRU cache

        Args:
            callsign: Callsign (uppercased)
            worked: Whether callsign has been worked
            last_date: Last contact date (YYYYMMDD format)
        """
        # Simple LRU: if cache is full, remove oldest entry
        if len(self._recent_lookups) >= self._recent_lookups_max_size:
            # Remove first item (oldest in insertion order for Python 3.7+)
            first_key = next(iter(self._recent_lookups))
            del self._recent_lookups[first_key]

        self._recent_lookups[callsign] = (worked, last_date)

    def get_statistics(self) -> Dict[str, int]:
        """
        Get statistics about matched spots (OPTIMIZED: query database for count)

        Returns:
            Dictionary with counts of different match types
        """
        try:
            session = self.db.get_session()
            try:
                from src.database.models import Contact
                from sqlalchemy.sql import func

                # Count distinct callsigns in database (fast with index)
                total_worked = session.query(func.count(func.distinct(Contact.callsign))).scalar() or 0

                return {
                    "total_worked_callsigns": total_worked,
                    "recent_lookups_cached": len(self._recent_lookups),
                    "cache_max_size": self._recent_lookups_max_size,
                }
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Error getting statistics: {e}", exc_info=True)
            return {
                "total_worked_callsigns": 0,
                "recent_lookups_cached": len(self._recent_lookups),
                "cache_max_size": self._recent_lookups_max_size,
            }

    def clear_cache(self) -> None:
        """Manually clear the LRU cache (called after contact changes)"""
        self._recent_lookups.clear()
        logger.info("SpotMatcher LRU cache cleared")

    def enable_award_eligibility(self, my_callsign: str, my_skcc_number: str) -> None:
        """
        Enable award eligibility analysis for spots.
        Call this after user settings are loaded.

        Args:
            my_callsign: User's callsign
            my_skcc_number: User's SKCC number
        """
        try:
            from src.ui.spot_eligibility_analyzer import SpotEligibilityAnalyzer

            self._my_callsign = my_callsign
            self._my_skcc_number = my_skcc_number
            self.eligibility_analyzer = SpotEligibilityAnalyzer(
                self.db, self.config_manager, my_callsign, my_skcc_number
            )
            logger.info(f"Award eligibility analysis enabled for {my_callsign}")
        except Exception as e:
            logger.error(f"Failed to enable award eligibility: {e}", exc_info=True)

    def get_spot_eligibility(self, spot: SKCCSpot) -> Optional['SpotEligibility']:
        """
        Get award eligibility information for a spot.

        Args:
            spot: SKCCSpot to analyze

        Returns:
            SpotEligibility object or None if not available
        """
        if not self.eligibility_analyzer:
            return None

        try:
            return self.eligibility_analyzer.analyze_spot(spot)
        except Exception as e:
            logger.error(f"Error getting spot eligibility: {e}", exc_info=True)
            return None

    def invalidate_eligibility_cache(self) -> None:
        """Clear eligibility cache after logging new contact or award change"""
        if self.eligibility_analyzer:
            self.eligibility_analyzer.invalidate_cache()
            logger.info("Spot eligibility cache invalidated")
