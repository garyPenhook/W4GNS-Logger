"""
SKCC (Straight Key Century Club) module

Provides SKCC member spotting, roster management, and award tracking.

Uses SKCC Skimmer's proven RBN connection approach to fix segmentation faults.
"""

from .skcc_skimmer_rbn_fetcher import SkccSkimmerRBNFetcher, SKCCSpot, SKCCSpotFilter, RBNConnectionState
from .spot_manager import SKCCSpotManager

__all__ = [
    "SkccSkimmerRBNFetcher",
    "SKCCSpot",
    "SKCCSpotFilter",
    "RBNConnectionState",
    "SKCCSpotManager",
]
