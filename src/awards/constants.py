"""
SKCC Award Constants

Centralized constants for SKCC award requirements and endorsement levels.
"""

from typing import List, Tuple

# Centurion Award Endorsement Levels
CENTURION_ENDORSEMENTS: List[Tuple[int, str]] = [
    (100, "Centurion"),
    (200, "Centurion x2"),
    (300, "Centurion x3"),
    (400, "Centurion x4"),
    (500, "Centurion x5"),
    (600, "Centurion x6"),
    (700, "Centurion x7"),
    (800, "Centurion x8"),
    (900, "Centurion x9"),
    (1000, "Centurion x10"),
    (1500, "Centurion x15"),
    (2000, "Centurion x20"),
    (2500, "Centurion x25"),
    (3000, "Centurion x30"),
    (3500, "Centurion x35"),
    (4000, "Centurion x40"),
]

# Tribune Award Endorsement Levels
TRIBUNE_ENDORSEMENTS: List[Tuple[int, str]] = [
    (50, "Tribune"),
    (100, "Tribune x2"),
    (150, "Tribune x3"),
    (200, "Tribune x4"),
    (250, "Tribune x5"),
    (300, "Tribune x6"),
    (350, "Tribune x7"),
    (400, "Tribune x8"),
    (450, "Tribune x9"),
    (500, "Tribune x10"),
    (750, "Tribune x15"),
    (1000, "Tribune x20"),
    (1250, "Tribune x25"),
    (1500, "Tribune x30"),
]

# Senator Award Endorsement Levels
SENATOR_ENDORSEMENTS: List[Tuple[int, str]] = [
    (200, "Senator"),
    (400, "Senator x2"),
    (600, "Senator x3"),
    (800, "Senator x4"),
    (1000, "Senator x5"),
    (1200, "Senator x6"),
    (1400, "Senator x7"),
    (1600, "Senator x8"),
    (1800, "Senator x9"),
    (2000, "Senator x10"),
]

# Award Effective Dates (YYYYMMDD format)
TRIBUNE_EFFECTIVE_DATE = "20070301"  # March 1, 2007
SENATOR_EFFECTIVE_DATE = "20130801"  # August 1, 2013
CENTURION_SPECIAL_EVENT_CUTOFF = "20091201"  # December 1, 2009
TRIBUNE_SPECIAL_EVENT_CUTOFF = "20081001"  # October 1, 2008
CANADIAN_PROVINCES_EFFECTIVE_DATE = "20090901"  # September 1, 2009
CANADIAN_TERRITORIES_EFFECTIVE_DATE = "20140101"  # January 2014
WAS_EFFECTIVE_DATE = "20111009"  # October 9, 2011

# Special Event Calls (don't count after cutoff dates)
SPECIAL_EVENT_CALLS = {
    'K9SKC',  # SKCC Club Call
    'K3Y',    # Example special-event call
}

# Valid Mechanical Key Types (SKCC requirement)
VALID_KEY_TYPES = {'STRAIGHT', 'BUG', 'SIDESWIPER'}

# Award Requirements
CENTURION_BASE_REQUIREMENT = 100  # Unique SKCC members
TRIBUNE_BASE_REQUIREMENT = 50  # Tribune/Senator members
SENATOR_BASE_REQUIREMENT = 200  # Tribune/Senator members after Tx8
TRIBUNE_PREREQUISITE = 100  # Must be Centurion first
SENATOR_PREREQUISITE = 400  # Must be Tribune x8 first


def get_endorsement_level(count: int, endorsement_list: List[Tuple[int, str]]) -> str:
    """
    Get endorsement level name for a given contact count.
    
    Args:
        count: Number of qualifying contacts
        endorsement_list: List of (threshold, name) tuples in ascending order
        
    Returns:
        Endorsement level name (e.g., "Tribune x2") or "Not Yet"
    """
    if count < endorsement_list[0][0]:
        return "Not Yet"
    
    # Find the highest level achieved
    current_level = endorsement_list[0][1]
    for threshold, name in endorsement_list:
        if count >= threshold:
            current_level = name
        else:
            break
    
    return current_level


def get_next_endorsement_threshold(count: int, endorsement_list: List[Tuple[int, str]]) -> int:
    """
    Get the contact count needed for the next endorsement level.
    
    Args:
        count: Current contact count
        endorsement_list: List of (threshold, name) tuples in ascending order
        
    Returns:
        Next threshold value
    """
    for threshold, _ in endorsement_list:
        if count < threshold:
            return threshold
    
    # Beyond highest defined level - calculate based on pattern
    last_threshold = endorsement_list[-1][0]
    if endorsement_list == CENTURION_ENDORSEMENTS:
        return ((count // 500) + 1) * 500  # 500-contact increments
    elif endorsement_list == TRIBUNE_ENDORSEMENTS:
        return ((count // 250) + 1) * 250  # 250-contact increments
    elif endorsement_list == SENATOR_ENDORSEMENTS:
        return ((count // 200) + 1) * 200  # 200-contact increments
    
    return last_threshold
