"""
Grid Square and Distance Calculations

Pure Python implementation for thread-safe grid calculations.
"""

import logging
from typing import Optional, List, Tuple, Dict, Any
from src.services.voacap_muf_fetcher import VOACAPMUFFetcher

logger = logging.getLogger(__name__)


def calculate_distance(grid1: str, grid2: str) -> Optional[float]:
    """
    Calculate distance between two Maidenhead grid squares.
    
    Args:
        grid1: First grid square (e.g., "FM06ew")
        grid2: Second grid square (e.g., "EM29nf")
        
    Returns:
        Distance in kilometers, or None if invalid
    """
    try:
        return VOACAPMUFFetcher._grid_distance(grid1, grid2)
    except Exception as e:
        logger.debug(f"Error calculating distance {grid1} → {grid2}: {e}")
        return None


def batch_calculate_distances(home_grid: str, grids: List[str]) -> List[Optional[float]]:
    """
    Calculate distances for multiple grid squares in one call.
    
    Args:
        home_grid: Home station grid square
        grids: List of contact grid squares
        
    Returns:
        List of distances in kilometers (None for invalid grids)
    """
    # Python implementation
    results = []
    for grid in grids:
        results.append(calculate_distance(home_grid, grid))
    return results


def calculate_bearing(grid1: str, grid2: str) -> Optional[float]:
    """
    Calculate bearing from grid1 to grid2.
    
    Args:
        grid1: Starting grid square
        grid2: Destination grid square
        
    Returns:
        Bearing in degrees (0-360), or None if invalid
    """
    try:
        # Python fallback not implemented
        logger.warning("Bearing calculation not yet implemented")
        return None
    except Exception as e:
        logger.debug(f"Error calculating bearing {grid1} → {grid2}: {e}")
        return None


def is_rust_available() -> bool:
    """Check if Rust acceleration is available - always False, using Python only"""
    return False


# Award calculation functions
def calculate_centurion_progress_rust(contacts: List[Tuple]) -> Tuple[int, List]:
    """
    Calculate Centurion award progress (Python implementation).

    Args:
        contacts: List of (callsign, skcc_number, mode, key_type, qso_date, band)

    Returns:
        (unique_count, details_list)
    """
    raise NotImplementedError("Centurion progress calculation requires database queries")


def calculate_tribune_progress_rust(contacts: List[Tuple]) -> Tuple[int, List]:
    """
    Calculate Tribune award progress (Python implementation).

    Args:
        contacts: List of (callsign, skcc_number, mode, key_type, qso_date, band)

    Returns:
        (unique_count, details_list)
    """
    raise NotImplementedError("Tribune progress calculation requires database queries")


def calculate_qrp_mpw_progress_rust(contacts: List[Tuple]) -> Tuple[int, float, float, List]:
    """
    Calculate QRP MPW award progress (Python implementation).

    Args:
        contacts: List of (callsign, tx_power, distance_km, mode, date, band)

    Returns:
        (qualifying_count, best_mpw, average_mpw, details_list)
    """
    raise NotImplementedError("QRP MPW progress calculation requires database queries")


def count_unique_states_rust(states: List[str]) -> int:
    """Count unique states (Python implementation)"""
    return len(set(s for s in states if s))


def count_unique_prefixes_rust(callsigns: List[str]) -> int:
    """Count unique prefixes (Python implementation)"""
    # Python implementation
    prefixes = set()
    for call in callsigns:
        if call:
            # Simple prefix extraction
            for i, c in enumerate(call):
                if c.isdigit():
                    prefixes.add(call[:i+1])
                    break
    return len(prefixes)


# Spot matcher functions (for RBN/DX Cluster real-time filtering)
def parse_rbn_spot(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse RBN telnet spot line.

    Example: "DX de K3LR-#:     14025.0  W4GNS          CW    24 dB  23 WPM  CQ      1234Z"

    Args:
        line: RBN spot line from telnet connection

    Returns:
        Dict with keys: callsign, frequency, snr, timestamp
        None if line cannot be parsed
    """
    # IMPORTANT: Always use Python implementation for parse_rbn_spot
    # The Rust version causes segmentation faults when called from background threads
    # due to PyO3 GIL handling issues when creating Python objects from Rust
    # See: https://github.com/PyO3/pyo3/issues/1205

    # Python implementation (thread-safe)
    parts = line.split()
    if len(parts) < 7 or parts[0] != "DX" or parts[1] != "de":
        return None

    try:
        freq = float(parts[3])
        callsign = parts[4]

        # Find SNR (look for "XX dB" pattern)
        snr = 0
        for i in range(len(parts) - 1):
            if parts[i + 1] == "dB":
                try:
                    snr = int(parts[i])
                    break
                except ValueError:
                    pass

        # Find timestamp (ends with Z)
        timestamp = ""
        for part in reversed(parts):
            if part.endswith('Z'):
                timestamp = part
                break

        return {
            'callsign': callsign,
            'frequency': freq,
            'snr': snr,
            'timestamp': timestamp
        }
    except (ValueError, IndexError):
        return None


def frequency_to_band(freq_mhz: float) -> str:
    """
    Convert frequency in MHz to ham band name.
    
    Args:
        freq_mhz: Frequency in megahertz
        
    Returns:
        Band name (e.g., "20M", "40M") or "UNK" if unknown
    """
    # Python implementation
    if 1.8 <= freq_mhz <= 2.0:
        return "160M"
    elif 3.5 <= freq_mhz <= 4.0:
        return "80M"
    elif 5.3 <= freq_mhz <= 5.4:
        return "60M"
    elif 7.0 <= freq_mhz <= 7.3:
        return "40M"
    elif 10.1 <= freq_mhz <= 10.15:
        return "30M"
    elif 14.0 <= freq_mhz <= 14.35:
        return "20M"
    elif 18.068 <= freq_mhz <= 18.168:
        return "17M"
    elif 21.0 <= freq_mhz <= 21.45:
        return "15M"
    elif 24.89 <= freq_mhz <= 24.99:
        return "12M"
    elif 28.0 <= freq_mhz <= 29.7:
        return "10M"
    elif 50.0 <= freq_mhz <= 54.0:
        return "6M"
    else:
        return "UNK"


def determine_mode(freq_mhz: float, mode_hint: Optional[str] = None) -> str:
    """
    Determine operating mode from frequency.

    Args:
        freq_mhz: Frequency in megahertz
        mode_hint: Optional explicit mode hint (e.g., "CW", "SSB")

    Returns:
        Mode string (e.g., "CW", "USB", "LSB", "SSB")
    """
    # IMPORTANT: Always use Python implementation for determine_mode
    # The Rust version causes segmentation faults when called from background threads
    # (spot_fetcher.py uses daemon threads to parse RBN spots)
    # This is due to PyO3 GIL handling issues when creating Python objects from Rust
    # See: https://github.com/PyO3/pyo3/issues/1205

    # Python implementation (thread-safe)
    if mode_hint and mode_hint.upper() in ["CW", "SSB", "USB", "LSB", "FM", "RTTY", "FT8", "FT4"]:
        return mode_hint.upper()
    
    # Determine from frequency (CW portions)
    if (1.8 <= freq_mhz <= 1.84 or
        3.5 <= freq_mhz <= 3.6 or
        7.0 <= freq_mhz <= 7.04 or
        14.0 <= freq_mhz <= 14.07 or
        21.0 <= freq_mhz <= 21.07 or
        28.0 <= freq_mhz <= 28.07 or
        50.0 <= freq_mhz <= 50.1):
        return "CW"
    
    # SSB portions - LSB on 160M, 80M, 40M
    if freq_mhz < 10.0:
        return "LSB"
    else:
        return "USB"

