"""
Spot Source Adapter - Unified interface for spot sources

Provides a unified interface for Direct RBN connection for spot data.
"""

import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime
from enum import Enum

from .spot_fetcher import SKCCSpot, RBNConnectionState

logger = logging.getLogger(__name__)


class SpotSource(Enum):
    """Spot data source"""
    DIRECT_RBN = "direct_rbn"


class SpotSourceAdapter:
    """
    Unified interface for spot sources

    Uses Direct RBN for spot data.
    """

    def __init__(self) -> None:
        """Initialize spot source adapter"""
        self.active_source: SpotSource = SpotSource.DIRECT_RBN
        
        # Callbacks
        self.on_spot: Optional[Callable[[Dict[str, Any]], None]] = None

    def use_direct_rbn(self) -> None:
        """Switch to direct RBN connection"""
        self.active_source = SpotSource.DIRECT_RBN
        logger.info("Using direct RBN as spot source")

    def get_active_source(self) -> SpotSource:
        """Get currently active spot source"""
        return self.active_source

    def get_status(self) -> Dict[str, Any]:
        """Get status of spot source adapter"""
        return {
            "active_source": self.active_source.value,
        }

