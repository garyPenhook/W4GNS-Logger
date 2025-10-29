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
from datetime import datetime, timedelta
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
        
        # Cache of worked callsigns (updated periodically)
        self._worked_callsigns: Set[str] = set()
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 minutes
        
        # Track when we last worked each callsign (for highlighting based on recency)
        self._last_worked_dates: Dict[str, str] = {}  # callsign -> YYYYMMDD
        
        # Highlighting preferences
        self.highlight_worked = config_manager.get("spots.highlight_worked", True)
        self.highlight_recent_days = config_manager.get("spots.highlight_recent_days", 30)
        self.enable_matching = config_manager.get("spots.enable_matching", True)
        
        # Award eligibility analyzer (optional, lazy-loaded)
        self.eligibility_analyzer: Optional['SpotEligibilityAnalyzer'] = None
        self._my_callsign = my_callsign
        self._my_skcc_number = my_skcc_number
        
        logger.info(f"SpotMatcher initialized: highlight_worked={self.highlight_worked}, "
                   f"recent_days={self.highlight_recent_days}, award_eligibility_available={bool(my_skcc_number)}")

    def reload_config(self) -> None:
        """Reload highlighting preferences from config"""
        self.highlight_worked = self.config_manager.get("spots.highlight_worked", True)
        self.highlight_recent_days = self.config_manager.get("spots.highlight_recent_days", 30)
        self.enable_matching = self.config_manager.get("spots.enable_matching", True)
        logger.debug("SpotMatcher config reloaded")

    def match_spot(self, spot: SKCCSpot) -> SpotMatch:
        """
        Check if a spot matches a contact in the database

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

        # Refresh cache if needed
        self._refresh_cache_if_needed()

        callsign = spot.callsign.upper()

        # Check if we've worked this callsign before
        if callsign not in self._worked_callsigns:
            return SpotMatch(
                spot=spot,
                match_type="NONE",
                callsign=callsign
            )

        # Get the date we last worked this callsign
        contact_date = self._last_worked_dates.get(callsign)

        if not contact_date:
            # Worked but no date cached - return generic WORKED match
            return SpotMatch(
                spot=spot,
                match_type="WORKED",
                callsign=callsign,
                contact_date=None
            )

        # Check if it's a recent contact
        try:
            contact_datetime = datetime.strptime(contact_date, "%Y%m%d")
            days_ago = (datetime.utcnow() - contact_datetime).days

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

    def _refresh_cache_if_needed(self) -> None:
        """Refresh the worked callsigns cache if TTL has expired"""
        now = datetime.utcnow()

        if (self._cache_timestamp is None or
            (now - self._cache_timestamp).total_seconds() > self._cache_ttl_seconds):

            try:
                # Get all unique callsigns from database
                contacts = self.db.get_all_contacts()

                self._worked_callsigns.clear()
                self._last_worked_dates.clear()

                for contact in contacts:
                    callsign = contact.callsign.upper()
                    self._worked_callsigns.add(callsign)

                    # Track the most recent contact date for this callsign
                    # (in case they worked the same station multiple times)
                    qso_date = getattr(contact, 'qso_date', None)
                    if qso_date:
                        # Keep the most recent date
                        if (callsign not in self._last_worked_dates or
                            qso_date > self._last_worked_dates[callsign]):
                            self._last_worked_dates[callsign] = qso_date

                self._cache_timestamp = now

                logger.debug(f"SpotMatcher cache refreshed: {len(self._worked_callsigns)} worked callsigns")

            except Exception as e:
                logger.error(f"Error refreshing spot matcher cache: {e}", exc_info=True)

    def get_statistics(self) -> Dict[str, int]:
        """
        Get statistics about matched spots

        Returns:
            Dictionary with counts of different match types
        """
        self._refresh_cache_if_needed()

        return {
            "total_worked_callsigns": len(self._worked_callsigns),
            "cache_age_seconds": int((datetime.utcnow() - self._cache_timestamp).total_seconds())
                if self._cache_timestamp else 0,
        }

    def clear_cache(self) -> None:
        """Manually clear the cache (for testing or after bulk contact additions)"""
        self._worked_callsigns.clear()
        self._last_worked_dates.clear()
        self._cache_timestamp = None
        logger.info("SpotMatcher cache cleared")

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
