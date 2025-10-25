"""
SKCC (Straight Key Century Club) module

Provides SKCC member spotting, roster management, and award tracking.
"""

from .spot_fetcher import RBNSpotFetcher, SKCCSpot, SKCCSpotFilter, RBNConnectionState
from .spot_manager import SKCCSpotManager

__all__ = [
    "RBNSpotFetcher",
    "SKCCSpot",
    "SKCCSpotFilter",
    "RBNConnectionState",
    "SKCCSpotManager",
]
