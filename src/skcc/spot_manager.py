"""
SKCC Spot Manager - Background thread manager for spot monitoring

Manages the background thread that monitors RBN for SKCC member spots
and integrates with the database and UI.
"""

import logging
from typing import Optional, Callable, Dict, List, Any
from datetime import datetime

from .spot_fetcher import RBNSpotFetcher, SKCCSpot, SKCCSpotFilter, RBNConnectionState
from src.database.repository import DatabaseRepository

logger = logging.getLogger(__name__)


class SKCCSpotManager:
    """
    Manages SKCC spot monitoring and integration

    Handles:
    - Background RBN monitoring
    - Spot filtering and processing
    - Database storage
    - UI callbacks
    """

    def __init__(self, db: DatabaseRepository):
        """
        Initialize SKCC spot manager

        Args:
            db: Database repository instance
        """
        self.db = db
        self.fetcher: Optional[RBNSpotFetcher] = None
        self.spot_filter = SKCCSpotFilter()
        self.use_test_spots = False

        # Callbacks
        self.on_new_spot: Optional[Callable[[SKCCSpot], None]] = None
        self.on_connection_state: Optional[Callable[[RBNConnectionState], None]] = None

    def start(self) -> None:
        """Start monitoring for SKCC spots"""
        try:
            # Load SKCC roster for member identification
            roster = self.db.skcc_members.get_roster_dict()
            roster_count = len(roster)
            logger.info(f"Loaded SKCC roster with {roster_count} members")

            if not roster:
                logger.warning("SKCC roster is empty! Spots will not be identified as SKCC members. "
                             "Try downloading the roster from Settings or running sync_membership_data()")

            # Create and configure fetcher
            self.fetcher = RBNSpotFetcher(roster, use_test_spots=self.use_test_spots)
            self.fetcher.set_callbacks(
                on_spot=self._on_new_spot,
                on_state_change=self._on_connection_state_changed,
            )

            # Start monitoring
            self.fetcher.start()
            mode = "TEST SPOTS" if self.use_test_spots else "RBN"
            logger.info(f"SKCC spot manager started (roster: {roster_count} members, mode: {mode})")

        except Exception as e:
            logger.error(f"Failed to start spot manager: {e}", exc_info=True)
            raise

    def stop(self) -> None:
        """Stop monitoring for SKCC spots"""
        if self.fetcher:
            self.fetcher.stop()
            self.fetcher = None
        logger.info("SKCC spot manager stopped")

    def set_spot_filter(self, spot_filter: SKCCSpotFilter) -> None:
        """
        Set the filter for spot processing

        Args:
            spot_filter: SKCCSpotFilter instance with filter criteria
        """
        self.spot_filter = spot_filter

    def set_callbacks(
        self,
        on_new_spot: Optional[Callable[[SKCCSpot], None]] = None,
        on_connection_state: Optional[Callable[[RBNConnectionState], None]] = None,
    ) -> None:
        """
        Set callbacks for spot events

        Args:
            on_new_spot: Called when a new spot is received
            on_connection_state: Called when connection state changes
        """
        self.on_new_spot = on_new_spot
        self.on_connection_state = on_connection_state

    def _on_new_spot(self, spot: SKCCSpot) -> None:
        """
        Handle new spot from RBN

        Args:
            spot: The SKCC spot received
        """
        try:
            # Get worked callsigns for filtering
            contacts = self.db.get_all_contacts()
            worked_callsigns = {c.callsign.upper() for c in contacts}

            # Apply filter
            if not self.spot_filter.matches(spot, worked_callsigns):
                return

            # Store in database
            spot_data = {
                "frequency": spot.frequency,
                "dx_callsign": spot.callsign,
                "de_callsign": spot.reporter,
                "dx_grid": spot.grid,
                "comment": f"Speed: {spot.speed} WPM" if spot.speed else None,
                "received_at": spot.timestamp,
                "spotted_date": spot.timestamp.strftime("%Y%m%d"),
                "spotted_time": spot.timestamp.strftime("%H%M"),
            }

            self.db.add_cluster_spot(spot_data)

            # Notify UI
            if self.on_new_spot:
                self.on_new_spot(spot)

            logger.debug(f"Processed SKCC spot: {spot.callsign} on {spot.frequency} MHz")

        except Exception as e:
            logger.error(f"Error processing spot: {e}")

    def _on_connection_state_changed(self, state: RBNConnectionState) -> None:
        """
        Handle RBN connection state change

        Args:
            state: New connection state
        """
        if self.on_connection_state:
            self.on_connection_state(state)
        logger.info(f"RBN connection state: {state.value}")

    def is_running(self) -> bool:
        """Check if spot monitoring is running"""
        return self.fetcher is not None and self.fetcher.connection_state != RBNConnectionState.DISCONNECTED

    def get_recent_spots(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent SKCC spots from database"""
        spots = self.db.get_recent_spots(limit)
        return [
            {
                "callsign": s.dx_callsign,
                "frequency": s.frequency,
                "reporter": s.de_callsign,
                "grid": s.dx_grid,
                "time": s.received_at,
                "comment": s.comment,
            }
            for s in spots
        ]

    def get_spots_by_band(self, band: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent spots for a specific band"""
        spots = self.db.get_spots_by_band(band, limit)
        return [
            {
                "callsign": s.dx_callsign,
                "frequency": s.frequency,
                "reporter": s.de_callsign,
                "grid": s.dx_grid,
                "time": s.received_at,
                "comment": s.comment,
            }
            for s in spots
        ]

    def cleanup_old_spots(self, hours: int = 24) -> int:
        """Remove spots older than specified hours"""
        return self.db.delete_old_spots(hours)
