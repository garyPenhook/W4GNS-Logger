"""
Spot Adapter - Convert between different spot formats

Allows the logger to work with spots from different sources:
- Direct RBN connection (RBNSpot)
- SKCC Skimmer file output (SkimmerSpot)
- Database spots
- Test spots

Provides unified interface for spot handling throughout the logger.
"""

import logging
from typing import Union, Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from .spot_fetcher import SKCCSpot, RBNConnectionState

logger = logging.getLogger(__name__)


@dataclass
class UnifiedSpot:
    """
    Unified spot format for internal use
    
    Normalizes spots from any source into a common format
    """
    callsign: str
    frequency: float
    mode: str
    timestamp: datetime
    spotter: str
    snr: Optional[int] = None
    wpm: Optional[int] = None
    distance: Optional[float] = None
    bearing: Optional[int] = None
    source: str = "unknown"  # "rbn", "skcc_skimmer", "test", "database"
    
    def to_skcc_spot(self) -> SKCCSpot:
        """Convert to SKCCSpot for compatibility"""
        return SKCCSpot(
            callsign=self.callsign,
            frequency=self.frequency,
            mode=self.mode,
            timestamp=self.timestamp,
            reporter=self.spotter,
            speed=self.wpm or 0,
            grid="",  # May be added later
        )


class SpotAdapter:
    """
    Adapts spots from different sources to unified format
    
    Handles:
    - SKCCSpot (from direct RBN) → UnifiedSpot
    - SkimmerSpot (from SKCC Skimmer file) → UnifiedSpot
    - Dict (from database/API) → UnifiedSpot
    """
    
    @staticmethod
    def from_skcc_spot(spot: SKCCSpot, source: str = "rbn") -> UnifiedSpot:
        """
        Convert SKCCSpot to UnifiedSpot
        
        Args:
            spot: SKCCSpot from direct RBN connection
            source: Source identifier ("rbn", "test", etc.)
            
        Returns:
            UnifiedSpot with normalized fields
        """
        # Ensure timestamp is datetime
        if isinstance(spot.timestamp, str):
            try:
                ts = datetime.fromisoformat(spot.timestamp)
            except (ValueError, TypeError):
                ts = datetime.utcnow()
        else:
            ts = spot.timestamp if spot.timestamp else datetime.utcnow()
        
        return UnifiedSpot(
            callsign=spot.callsign,
            frequency=spot.frequency,
            mode=spot.mode,
            timestamp=ts,
            spotter=spot.reporter,
            snr=None,
            wpm=spot.speed if spot.speed > 0 else None,
            distance=None,
            bearing=None,
            source=source,
        )
    
    @staticmethod
    def from_skimmer_spot(spot: Dict[str, Any]) -> UnifiedSpot:
        """
        Convert SKCC Skimmer spot to UnifiedSpot
        
        Args:
            spot: Spot dict from SKCC Skimmer file output
                  Expected keys: callsign, frequency, mode, timestamp, spotter, 
                  snr (optional), wpm (optional), distance (optional)
            
        Returns:
            UnifiedSpot with normalized fields
        """
        # Parse timestamp
        ts_str = spot.get("timestamp", "")
        if isinstance(ts_str, str):
            # Handle UTC time format (e.g., "23:45Z")
            if ts_str.endswith("Z"):
                try:
                    time_parts = ts_str.rstrip("Z").split(":")
                    if len(time_parts) == 2:
                        hour, minute = int(time_parts[0]), int(time_parts[1])
                        ts = datetime.utcnow().replace(hour=hour, minute=minute, second=0, microsecond=0)
                    else:
                        ts = datetime.utcnow()
                except (ValueError, TypeError):
                    ts = datetime.utcnow()
            else:
                try:
                    ts = datetime.fromisoformat(ts_str)
                except (ValueError, TypeError):
                    ts = datetime.utcnow()
        else:
            ts = spot.get("timestamp", datetime.utcnow())
        
        return UnifiedSpot(
            callsign=spot.get("callsign", "").upper(),
            frequency=float(spot.get("frequency", 0.0)),
            mode=spot.get("mode", "CW").upper(),
            timestamp=ts,
            spotter=spot.get("spotter", "SKCC Skimmer"),
            snr=spot.get("snr"),
            wpm=spot.get("wpm"),
            distance=spot.get("distance"),  # Already in km from SKCC Skimmer
            bearing=spot.get("bearing"),
            source="skcc_skimmer",
        )
    
    @staticmethod
    def from_dict(spot_dict: Dict[str, Any]) -> UnifiedSpot:
        """
        Convert generic dict to UnifiedSpot
        
        Args:
            spot_dict: Dictionary with spot fields
            
        Returns:
            UnifiedSpot
        """
        # Parse timestamp
        ts = spot_dict.get("timestamp", datetime.utcnow())
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except (ValueError, TypeError):
                ts = datetime.utcnow()
        
        return UnifiedSpot(
            callsign=spot_dict.get("callsign", "").upper(),
            frequency=float(spot_dict.get("frequency", 0.0)),
            mode=spot_dict.get("mode", "CW").upper(),
            timestamp=ts,
            spotter=spot_dict.get("spotter", ""),
            snr=spot_dict.get("snr"),
            wpm=spot_dict.get("wpm"),
            distance=spot_dict.get("distance"),
            bearing=spot_dict.get("bearing"),
            source=spot_dict.get("source", "unknown"),
        )


class SpotSourceManager:
    """
    Manages which source provides spots to the logger
    
    Can switch between:
    - Direct RBN connection (RBNSpotFetcher)
    - SKCC Skimmer file monitoring (SkimmerSpotMonitor)
    """
    
    def __init__(self):
        """Initialize spot source manager"""
        self.active_source = "rbn"  # "rbn" or "skcc_skimmer"
        self.source_config: Dict[str, Any] = {
            "rbn": {"enabled": True, "use_test_spots": False},
            "skcc_skimmer": {"enabled": False, "monitor_path": None},
        }
        logger.info(f"Spot source manager initialized (active: {self.active_source})")
    
    def set_active_source(self, source: str) -> bool:
        """
        Switch active spot source
        
        Args:
            source: "rbn" or "skcc_skimmer"
            
        Returns:
            True if switch successful
        """
        if source not in self.source_config:
            logger.error(f"Unknown spot source: {source}")
            return False
        
        self.active_source = source
        logger.info(f"Switched spot source to: {source}")
        return True
    
    def get_active_source(self) -> str:
        """Get currently active spot source"""
        return self.active_source
    
    def configure_source(self, source: str, config: Dict[str, Any]) -> None:
        """
        Configure a spot source
        
        Args:
            source: "rbn" or "skcc_skimmer"
            config: Configuration dict for the source
        """
        if source in self.source_config:
            self.source_config[source].update(config)
            logger.info(f"Configured {source} spot source: {config}")
    
    def get_source_config(self, source: str) -> Dict[str, Any]:
        """Get configuration for a spot source"""
        return self.source_config.get(source, {})
