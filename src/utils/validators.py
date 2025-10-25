"""
Data Validators Module

Provides validation functions for ham radio data formats.
"""

import re
from typing import Tuple


def validate_callsign(callsign: str) -> Tuple[bool, str]:
    """
    Validate ham radio callsign format

    Args:
        callsign: Callsign to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not callsign:
        return False, "Callsign cannot be empty"

    if len(callsign) > 12:
        return False, "Callsign cannot exceed 12 characters"

    # Callsign pattern: alphanumeric with optional slash
    pattern = r"^[A-Z0-9/]+$"
    if not re.match(pattern, callsign, re.IGNORECASE):
        return False, "Callsign must contain only letters, numbers, and slash"

    return True, ""


def validate_date(date_str: str) -> Tuple[bool, str]:
    """
    Validate YYYYMMDD date format

    Args:
        date_str: Date string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not date_str or len(date_str) != 8 or not date_str.isdigit():
        return False, "Date must be in YYYYMMDD format"

    year = int(date_str[:4])
    month = int(date_str[4:6])
    day = int(date_str[6:8])

    if not (1900 <= year <= 2100):
        return False, f"Year must be between 1900 and 2100"

    if not (1 <= month <= 12):
        return False, f"Month must be between 01 and 12"

    if not (1 <= day <= 31):
        return False, f"Day must be between 01 and 31"

    return True, ""


def validate_time(time_str: str) -> Tuple[bool, str]:
    """
    Validate HHMM time format

    Args:
        time_str: Time string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not time_str or len(time_str) != 4 or not time_str.isdigit():
        return False, "Time must be in HHMM format"

    hours = int(time_str[:2])
    minutes = int(time_str[2:4])

    if not (0 <= hours <= 23):
        return False, "Hours must be between 00 and 23"

    if not (0 <= minutes <= 59):
        return False, "Minutes must be between 00 and 59"

    return True, ""


def validate_frequency(freq: float, band: str) -> Tuple[bool, str]:
    """
    Validate frequency for a given band

    Args:
        freq: Frequency in MHz
        band: Band designation (e.g., "20M", "2M")

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Band frequency ranges (MHz)
    BAND_RANGES = {
        "160M": (1.8, 2.0),
        "80M": (3.5, 4.0),
        "60M": (5.330, 5.405),
        "40M": (7.0, 7.300),
        "30M": (10.1, 10.15),
        "20M": (14.0, 14.35),
        "17M": (18.068, 18.168),
        "15M": (21.0, 21.45),
        "12M": (24.89, 24.99),
        "10M": (28.0, 29.7),
        "6M": (50.0, 54.0),
        "2M": (144.0, 148.0),
        "70CM": (420.0, 450.0),
    }

    if band not in BAND_RANGES:
        return False, f"Unknown band: {band}"

    min_freq, max_freq = BAND_RANGES[band]

    if not (min_freq <= freq <= max_freq):
        return False, f"Frequency {freq} MHz is outside {band} range ({min_freq}-{max_freq})"

    return True, ""


def validate_rst(rst: str) -> Tuple[bool, str]:
    """
    Validate RST (Readability-Strength-Tone) report

    Args:
        rst: RST report (e.g., "599", "579")

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not rst or len(rst) != 3 or not rst.isdigit():
        return False, "RST must be 3 digits"

    readability = int(rst[0])
    strength = int(rst[1])
    tone = int(rst[2])

    if not (1 <= readability <= 5):
        return False, "Readability must be 1-5"

    if not (1 <= strength <= 9):
        return False, "Strength must be 1-9"

    if not (1 <= tone <= 9):
        return False, "Tone must be 1-9"

    return True, ""


def validate_mode(mode: str) -> Tuple[bool, str]:
    """
    Validate operating mode

    Args:
        mode: Mode designation

    Returns:
        Tuple of (is_valid, error_message)
    """
    VALID_MODES = {
        "CW", "SSB", "AM", "FM", "RTTY", "PSK31", "PSK63", "PSK125",
        "PSKOTHER", "OLIVIA", "HELLSCHREIBER", "BPSK", "QPSK",
        "JT9", "JT65", "JT4", "WSPR", "FT8", "FSK441", "FT4"
    }

    if mode.upper() not in VALID_MODES:
        return False, f"Unknown mode: {mode}"

    return True, ""


def validate_grid(grid: str) -> Tuple[bool, str]:
    """
    Validate Maidenhead grid square format

    Args:
        grid: Grid square (e.g., "FN20qd")

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not grid:
        return False, "Grid cannot be empty"

    if len(grid) < 4 or len(grid) > 10:
        return False, "Grid must be 4-10 characters"

    # Grid pattern: 2 letters, 2 digits, optionally 4 more chars
    pattern = r"^[A-X]{2}[0-9]{2}([a-x]{2}[0-9]{2})?$"
    if not re.match(pattern, grid, re.IGNORECASE):
        return False, "Invalid grid square format"

    return True, ""
