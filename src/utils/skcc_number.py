"""
SKCC Number Utilities

Helper functions for parsing and validating SKCC member numbers.
"""

import re
from typing import Optional


def extract_base_skcc_number(skcc_number: str) -> Optional[str]:
    """
    Extract base SKCC number from a full SKCC number string.
    
    SKCC numbers can have suffixes like:
    - C, T, S (Centurion, Tribune, Senator)
    - x2, x3, etc. (endorsement levels)
    - Combinations like "12345Tx2"
    
    Examples:
        "12345" -> "12345"
        "12345C" -> "12345"
        "12345T" -> "12345"
        "12345Tx2" -> "12345"
        "12345 Tx2" -> "12345"
        "12345Sx10" -> "12345"
    
    Args:
        skcc_number: Full SKCC number string
        
    Returns:
        Base numeric SKCC number, or None if invalid
    """
    if not skcc_number:
        return None
        
    # Remove leading/trailing whitespace
    skcc_number = skcc_number.strip()
    
    # Split on whitespace and take first part
    base = skcc_number.split()[0]
    
    # Remove letter suffix (C, T, S) if present at the end
    if base and base[-1] in 'CTS':
        base = base[:-1]
    
    # Remove 'x' multiplier suffix (like x2, x10, etc.)
    if base and 'x' in base:
        base = base.split('x')[0]
    
    # Verify it's a valid number
    if base and base.isdigit():
        return base
    
    return None


def parse_skcc_suffix(skcc_number: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parse SKCC number into base number and suffix.
    
    Args:
        skcc_number: Full SKCC number string
        
    Returns:
        Tuple of (base_number, suffix) where suffix could be:
        - "C", "T", "S" for member type
        - "x2", "x10", etc. for endorsement level
        - "Tx2", "Sx10", etc. for combination
        - None if no suffix
    """
    if not skcc_number:
        return None, None
    
    skcc_number = skcc_number.strip()
    base = skcc_number.split()[0]
    
    # Extract suffix
    suffix = None
    if base and not base.isdigit():
        # Find where digits end
        match = re.match(r'^(\d+)(.*)$', base)
        if match:
            return match.group(1), match.group(2) if match.group(2) else None
    
    if base and base.isdigit():
        return base, None
    
    return None, None


def get_member_type(skcc_number: str) -> Optional[str]:
    """
    Get member type from SKCC number.
    
    Args:
        skcc_number: Full SKCC number string
        
    Returns:
        'C' (Centurion), 'T' (Tribune), 'S' (Senator), or None
    """
    if not skcc_number:
        return None
    
    _, suffix = parse_skcc_suffix(skcc_number)
    if suffix and suffix[0] in 'CTS':
        return suffix[0]
    
    return None


def is_valid_skcc_number(skcc_number: str) -> bool:
    """
    Check if a string is a valid SKCC number format.
    
    Args:
        skcc_number: String to validate
        
    Returns:
        True if valid SKCC number format
    """
    base = extract_base_skcc_number(skcc_number)
    return base is not None and base.isdigit() and len(base) >= 1
