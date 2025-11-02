"""
SKCC (Straight Key Century Club) module

Uses K7MJG's SKCC Skimmer for intelligent SKCC member spot filtering.
SKCC Skimmer analyzes user's ADIF file and goals/targets to provide
relevant spot recommendations.
"""

from .skcc_skimmer_subprocess import SkccSkimmerSubprocess, SkimmerConnectionState, SKCCSpot

__all__ = [
    "SkccSkimmerSubprocess",
    "SkimmerConnectionState",
    "SKCCSpot",
]
