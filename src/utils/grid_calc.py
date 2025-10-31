"""
Grid Square and Distance Calculations

High-performance wrapper around Rust implementation with Python fallback.
"""

import logging
from typing import Optional, List, Tuple, Dict, Any
import importlib.util
import sys
import platform
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import Rust module, fallback to Python
_USE_RUST = False
try:
    # First try normal import
    import rust_grid_calc
    _USE_RUST = hasattr(rust_grid_calc, 'calculate_distance')

    if not _USE_RUST:
        # If it's a namespace package, try to load library directly
        # Determine platform-specific extension
        system = platform.system()
        if system == 'Windows':
            extensions = ['rust_grid_calc.pyd', 'rust_grid_calc.dll']
        elif system == 'Darwin':  # macOS
            extensions = ['rust_grid_calc.so', 'librust_grid_calc.dylib']
        else:  # Linux and others
            extensions = ['rust_grid_calc.so', 'librust_grid_calc.so']

        # Check multiple possible locations
        search_locations = []

        # Venv site-packages (Unix-like)
        if hasattr(sys, 'prefix'):
            site_packages_unix = Path(sys.prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
            search_locations.append(site_packages_unix)

            # Windows site-packages
            site_packages_win = Path(sys.prefix) / "Lib" / "site-packages"
            search_locations.append(site_packages_win)

        # Relative to current file
        venv_site_packages_unix = Path(__file__).parent.parent.parent / "venv" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
        venv_site_packages_win = Path(__file__).parent.parent.parent / "venv" / "Lib" / "site-packages"
        search_locations.extend([venv_site_packages_unix, venv_site_packages_win])

        # Try all combinations of locations and extensions
        found = False
        for location in search_locations:
            for ext in extensions:
                lib_path = location / ext
                if lib_path.exists():
                    spec = importlib.util.spec_from_file_location("rust_grid_calc", lib_path)
                    rust_grid_calc = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(rust_grid_calc)
                    _USE_RUST = True
                    sys.modules['rust_grid_calc'] = rust_grid_calc
                    logger.info(f"Loaded Rust grid calculator from {lib_path}")
                    found = True
                    break
            if found:
                break

except ImportError as e:
    logger.debug(f"Rust grid calculator import failed: {e}")
except Exception as e:
    logger.warning(f"Error loading Rust grid calculator: {e}")

if _USE_RUST:
    logger.info("Using Rust grid calculator (high performance)")
else:
    logger.warning("Rust grid calculator not available, using Python fallback")
    from src.services.voacap_muf_fetcher import VOACAPMUFFetcher


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
        if _USE_RUST:
            return rust_grid_calc.calculate_distance(grid1, grid2)
        else:
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
    if _USE_RUST:
        return rust_grid_calc.batch_calculate_distances(home_grid, grids)
    else:
        # Python fallback
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
        if _USE_RUST:
            return rust_grid_calc.calculate_bearing(grid1, grid2)
        else:
            # Python fallback not implemented
            logger.warning("Bearing calculation only available with Rust module")
            return None
    except Exception as e:
        logger.debug(f"Error calculating bearing {grid1} → {grid2}: {e}")
        return None


def is_rust_available() -> bool:
    """Check if Rust acceleration is available"""
    return _USE_RUST


# Award calculation functions
def calculate_centurion_progress_rust(contacts: List[Tuple]) -> Tuple[int, List]:
    """
    Calculate Centurion award progress using Rust.
    
    Args:
        contacts: List of (callsign, skcc_number, mode, key_type, qso_date, band)
        
    Returns:
        (unique_count, details_list)
    """
    if not _USE_RUST:
        raise RuntimeError("Rust module not available")
    return rust_grid_calc.calculate_centurion_progress(contacts)


def calculate_tribune_progress_rust(contacts: List[Tuple]) -> Tuple[int, List]:
    """
    Calculate Tribune award progress using Rust.
    
    Args:
        contacts: List of (callsign, skcc_number, mode, key_type, qso_date, band)
        
    Returns:
        (unique_count, details_list)
    """
    if not _USE_RUST:
        raise RuntimeError("Rust module not available")
    return rust_grid_calc.calculate_tribune_progress(contacts)


def calculate_qrp_mpw_progress_rust(contacts: List[Tuple]) -> Tuple[int, float, float, List]:
    """
    Calculate QRP MPW award progress using Rust.
    
    Args:
        contacts: List of (callsign, tx_power, distance_km, mode, date, band)
        
    Returns:
        (qualifying_count, best_mpw, average_mpw, details_list)
    """
    if not _USE_RUST:
        raise RuntimeError("Rust module not available")
    return rust_grid_calc.calculate_qrp_mpw_progress(contacts)


def count_unique_states_rust(states: List[str]) -> int:
    """Count unique states using Rust"""
    if not _USE_RUST:
        return len(set(s for s in states if s))
    return rust_grid_calc.count_unique_states(states)


def count_unique_prefixes_rust(callsigns: List[str]) -> int:
    """Count unique prefixes using Rust"""
    if not _USE_RUST:
        # Python fallback
        prefixes = set()
        for call in callsigns:
            if call:
                # Simple prefix extraction
                for i, c in enumerate(call):
                    if c.isdigit():
                        prefixes.add(call[:i+1])
                        break
        return len(prefixes)
    return rust_grid_calc.count_unique_prefixes(callsigns)


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
    if _USE_RUST:
        try:
            return rust_grid_calc.parse_rbn_spot(line)
        except ValueError:
            return None
        except Exception as e:
            logger.debug(f"Rust parse_rbn_spot failed: {e}")
            return None
    else:
        # Python fallback
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
    if _USE_RUST:
        try:
            return rust_grid_calc.frequency_to_band(freq_mhz)
        except Exception as e:
            logger.debug(f"Rust frequency_to_band failed: {e}")
    
    # Python fallback
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
    if _USE_RUST:
        try:
            if mode_hint:
                return rust_grid_calc.determine_mode(freq_mhz, mode_hint)
            else:
                return rust_grid_calc.determine_mode(freq_mhz)
        except Exception as e:
            logger.debug(f"Rust determine_mode failed: {e}")
    
    # Python fallback
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

