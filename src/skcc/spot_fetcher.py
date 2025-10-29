"""
SKCC Member Spot Fetcher - Monitor RBN for SKCC member activity

Connects to the Reverse Beacon Network (RBN) to identify SKCC member spots
and filter them based on user preferences (bands, modes, unworked stations, etc.)
"""

import logging
import socket
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Callable, Dict, List, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RBNConnectionState(Enum):
    """RBN connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass(slots=True)
@dataclass
class SKCCSpot:
    """Represents a SKCC member spot from RBN"""
    callsign: str
    frequency: float
    mode: str
    grid: Optional[str]
    reporter: str
    strength: int  # 0-9 signal strength
    speed: Optional[int]  # CW speed in WPM for CW spots
    timestamp: datetime
    is_skcc: bool  # Whether identified as SKCC member
    skcc_number: Optional[str] = None
    goal_type: Optional[str] = None  # GOAL/TARGET/BOTH classification from spot_classifier


class RBNSpotFetcher:
    """
    Connects to RBN and monitors for SKCC member spots

    RBN (Reverse Beacon Network) spots beacon CW transmissions heard by receivers.
    This module filters those spots to identify SKCC member activity.
    """

    # RBN telnet servers (CW spots)
    RBN_SERVERS = [
        ("telnet.reversebeacon.net", 7000),
        ("aprs.gids.nl", 14500),
    ]

    def __init__(self, skcc_roster: Dict[str, str], use_test_spots: bool = False) -> None:
        """
        Initialize RBN spot fetcher

        Args:
            skcc_roster: Dictionary mapping callsigns to SKCC numbers
            use_test_spots: If True, simulate test spots instead of connecting to real RBN
        """
        self.skcc_roster = skcc_roster
        self.connection_state = RBNConnectionState.DISCONNECTED
        self.socket: Optional[socket.socket] = None
        self._stop_event = threading.Event()
        self._listener_thread: Optional[threading.Thread] = None
        self.use_test_spots = use_test_spots

        # Callbacks for spot updates
        self.on_spot: Optional[Callable[[SKCCSpot], None]] = None
        self.on_state_change: Optional[Callable[[RBNConnectionState], None]] = None

    def set_callbacks(
        self,
        on_spot: Optional[Callable[[SKCCSpot], None]] = None,
        on_state_change: Optional[Callable[[RBNConnectionState], None]] = None,
    ) -> None:
        """
        Set callbacks for spot events

        Args:
            on_spot: Called when a new spot is received
            on_state_change: Called when connection state changes
        """
        self.on_spot = on_spot
        self.on_state_change = on_state_change

    def start(self) -> None:
        """Start monitoring for SKCC spots"""
        if self._listener_thread and self._listener_thread.is_alive():
            logger.warning("Spot fetcher already running")
            return

        self._stop_event.clear()
        self._listener_thread = threading.Thread(target=self._run, daemon=True)
        self._listener_thread.start()
        logger.info("SKCC spot fetcher started")

    def stop(self) -> None:
        """Stop monitoring for SKCC spots"""
        self._stop_event.set()
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"Error closing socket: {e}")
        self.socket = None
        self._set_state(RBNConnectionState.DISCONNECTED)
        logger.info("SKCC spot fetcher stopped")

    def _run(self) -> None:
        """Main loop for spot fetching"""
        if self.use_test_spots:
            logger.warning("Using TEST spot simulation (no real RBN connection)")
            self._generate_test_spots()
        else:
            while not self._stop_event.is_set():
                try:
                    self._connect_and_listen()
                except Exception as e:
                    logger.error(f"Spot fetcher error: {e}", exc_info=True)
                    self._set_state(RBNConnectionState.ERROR)
                    # Backoff before reconnecting
                    for _ in range(30):
                        if self._stop_event.is_set():
                            return
                        time.sleep(1)

    def _connect_and_listen(self) -> None:
        """Connect to RBN and listen for spots"""
        for server, port in self.RBN_SERVERS:
            try:
                logger.info(f"Connecting to RBN at {server}:{port}")
                self._set_state(RBNConnectionState.CONNECTING)

                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(10)
                self.socket.connect((server, port))

                self._set_state(RBNConnectionState.CONNECTED)
                logger.info(f"Connected to RBN at {server}:{port}")

                # RBN requires a callsign for login
                # Use a generic skimmer call or W4GNS Logger as identifier
                callsign = b"W4GNSLOGGER\n"

                logger.info(f"Sending RBN login with callsign...")
                self.socket.send(callsign)
                time.sleep(0.5)

                # Read login response to ensure we're authenticated
                try:
                    self.socket.settimeout(2)
                    response = self.socket.recv(1024).decode('utf-8', errors='ignore')
                    logger.debug(f"RBN login response: {response[:200]}")
                    self.socket.settimeout(10)  # Return to normal timeout
                except socket.timeout:
                    pass  # OK if no immediate response
                except Exception as e:
                    logger.debug(f"Error reading login response: {e}")

                logger.info("Logged in to RBN, listening for spots...")

                # Listen for spots
                self._listen_for_spots()
                return

            except Exception as e:
                logger.debug(f"Failed to connect to {server}:{port}: {e}")
                if self.socket:
                    try:
                        self.socket.close()
                    except Exception:
                        pass
                self.socket = None

        # All servers failed, wait before retrying
        self._set_state(RBNConnectionState.DISCONNECTED)
        logger.warning("Could not connect to any RBN server, retrying in 60 seconds")
        time.sleep(60)

    def _listen_for_spots(self) -> None:
        """Listen for incoming RBN spots"""
        buffer = ""
        line_count = 0
        spot_count = 0
        skip_count = 0

        while not self._stop_event.is_set() and self.socket:
            try:
                data = self.socket.recv(1024).decode("utf-8", errors="ignore")
                if not data:
                    logger.warning("RBN connection closed by server")
                    break

                buffer += data
                lines = buffer.split("\n")
                buffer = lines[-1]  # Keep incomplete line in buffer

                for line in lines[:-1]:
                    stripped = line.strip()
                    if stripped:
                        line_count += 1

                        # Log first few lines for debugging
                        if line_count <= 10:
                            logger.debug(f"RBN line {line_count}: {stripped[:100]}")

                        # Check if it's a spot line
                        if stripped.startswith("DX de "):
                            self._parse_spot_line(stripped)
                            spot_count += 1
                        else:
                            skip_count += 1

            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error receiving data: {e}")
                break

        logger.info(f"RBN listener stopped: {line_count} lines received, {spot_count} spots parsed, {skip_count} non-spot lines")

    def _parse_spot_line(self, line: str) -> None:
        """
        Parse RBN spot line

        RBN format: DX de Callsign: Frequency Mode Signal Report
        Examples:
        - DX de W5WJ: 3579.0 W1AW CW 33 dB 12 WPM
        - DX de K4XYZ: 14050.5 N0CALL SSB 25 dB
        - DX de VE3ABC: 7100.0 W4GNS CW 18 dB 35 WPM

        Args:
            line: Raw spot line from RBN
        """
        if not line:
            return

        # Must start with "DX de"
        if not line.startswith("DX de "):
            return

        try:
            # Parse: "DX de REPORTER: FREQ CALLSIGN MODE STRENGTH WPM"
            parts = line.split()
            if len(parts) < 6:
                logger.debug(f"Spot line too short ({len(parts)} parts): {line[:60]}")
                return

            # Extract reporter (remove trailing colon)
            reporter = parts[2].rstrip(":")
            if not reporter:
                return

            # Parse frequency (RBN sends frequencies in kHz)
            try:
                frequency_khz = float(parts[3])
                if frequency_khz < 100 or frequency_khz > 300000:  # Sanity check (100 kHz to 300 MHz)
                    return
                frequency = frequency_khz / 1000  # Convert kHz to MHz
            except (ValueError, IndexError):
                return

            # Parse callsign
            try:
                callsign = parts[4].upper()
                if not callsign or len(callsign) < 2:  # Minimum callsign length
                    return
            except IndexError:
                return

            # Parse mode
            try:
                mode = parts[5].upper()
            except IndexError:
                mode = "CW"

            # Extract signal strength (e.g., "10 dB" where 10 is parts[6] and dB is parts[7])
            strength = 0
            try:
                # Look for "dB" in parts and extract the numeric value before it
                for i, part in enumerate(parts[6:], start=6):
                    if part == "dB" or part.endswith("dB"):
                        # Found dB marker, strength is in previous part
                        if i > 0:
                            strength = int(parts[i-1])
                        break
            except (ValueError, IndexError):
                pass

            # Extract WPM if present (CW spots)
            speed: Optional[int] = None
            try:
                if len(parts) > 8:
                    # Look for WPM in the line
                    for i, part in enumerate(parts[7:], start=7):
                        if "WPM" in part.upper():
                            try:
                                speed = int(parts[i-1])
                            except (ValueError, IndexError):
                                pass
                            break
            except Exception:
                pass

            # Check if this is a SKCC member
            is_skcc = callsign in self.skcc_roster
            skcc_number = self.skcc_roster.get(callsign) if is_skcc else None

            spot = SKCCSpot(
                callsign=callsign,
                frequency=frequency,
                mode=mode,
                grid=None,  # RBN doesn't provide grid typically
                reporter=reporter,
                strength=strength,
                speed=speed,
                timestamp=datetime.now(timezone.utc),
                is_skcc=is_skcc,
                skcc_number=skcc_number,
            )

            if self.on_spot:
                self.on_spot(spot)
                logger.debug(f"Parsed spot: {callsign} on {frequency} MHz (SKCC: {is_skcc})")

        except Exception as e:
            logger.debug(f"Error parsing spot line '{line[:60]}': {e}")

    def _set_state(self, state: RBNConnectionState) -> None:
        """Update connection state and call callback"""
        if self.connection_state != state:
            self.connection_state = state
            if self.on_state_change:
                self.on_state_change(state)
            logger.debug(f"RBN connection state: {state.value}")

    def _generate_test_spots(self) -> None:
        """Generate simulated test spots for development/testing"""
        import random

        self._set_state(RBNConnectionState.CONNECTED)
        logger.info("TEST: Starting simulated spot generation")

        test_callsigns = list(self.skcc_roster.keys())
        if not test_callsigns:
            logger.warning("TEST: No SKCC members in roster for test spots")
            return

        bands = ["160M", "80M", "40M", "20M", "15M", "10M"]
        band_freqs = {
            "160M": (1.8, 2.0),
            "80M": (3.5, 4.0),
            "40M": (7.0, 7.3),
            "20M": (14.0, 14.35),
            "15M": (21.0, 21.45),
            "10M": (28.0, 29.7),
        }

        spot_count = 0
        try:
            while not self._stop_event.is_set():
                # Generate a random test spot
                band = random.choice(bands)
                freq_low, freq_high = band_freqs[band]
                frequency = round(random.uniform(freq_low, freq_high), 3)

                callsign = random.choice(test_callsigns)
                skcc_number = self.skcc_roster.get(callsign)

                spot = SKCCSpot(
                    callsign=callsign,
                    frequency=frequency,
                    mode="CW",
                    grid=None,
                    reporter="TEST",
                    strength=random.randint(10, 45),
                    speed=random.randint(15, 40),
                    timestamp=datetime.now(timezone.utc),
                    is_skcc=True,
                    skcc_number=skcc_number,
                )

                if self.on_spot:
                    self.on_spot(spot)
                    spot_count += 1
                    logger.debug(f"TEST: Generated spot {spot_count}: {callsign} on {frequency} MHz")

                # Generate a spot every 2-5 seconds
                time.sleep(random.uniform(2, 5))

        except Exception as e:
            logger.error(f"Error generating test spots: {e}")
        finally:
            self._set_state(RBNConnectionState.DISCONNECTED)
            logger.info(f"TEST: Stopped after generating {spot_count} test spots")


class SKCCSpotFilter:
    """Filter SKCC spots based on user preferences"""

    def __init__(self) -> None:
        """Initialize spot filter"""
        self.enabled_bands: List[str] = []  # Empty = all bands
        self.enabled_modes: List[str] = []  # Empty = all modes
        self.unworked_only = False
        self.min_strength = 0
        self.max_age_seconds = 300  # Only show spots newer than 5 minutes

    def matches(self, spot: SKCCSpot, worked_callsigns: set) -> bool:
        """
        Check if spot matches filter criteria

        Args:
            spot: The SKCC spot to filter
            worked_callsigns: Set of callsigns already worked

        Returns:
            True if spot matches all filter criteria
        """
        # Check if SKCC member
        if not spot.is_skcc:
            return False

        # Check age (use timezone-aware UTC)
        age = (datetime.now(timezone.utc) - spot.timestamp).total_seconds()
        if age > self.max_age_seconds:
            return False

        # Check strength
        if spot.strength < self.min_strength:
            return False

        # Check band
        if self.enabled_bands:
            band = self._freq_to_band(spot.frequency)
            if band and band not in self.enabled_bands:
                return False

        # Check mode
        if self.enabled_modes and spot.mode not in self.enabled_modes:
            return False

        # Check if already worked
        if self.unworked_only and spot.callsign in worked_callsigns:
            return False

        return True

    @staticmethod
    def _freq_to_band(frequency: float) -> Optional[str]:
        """Convert frequency to band name using cached mapping"""
        for band, (low, high) in BANDS.items():
            if low <= frequency <= high:
                return band

        return None

# Shared HF/VHF band bounds mapping for quick lookups
BANDS: Dict[str, tuple] = {
    "160M": (1.8, 2.0),
    "80M": (3.5, 4.0),
    "60M": (5.1, 5.4),
    "40M": (7.0, 7.3),
    "30M": (10.1, 10.15),
    "20M": (14.0, 14.35),
    "17M": (18.068, 18.168),
    "15M": (21.0, 21.45),
    "12M": (24.89, 24.99),
    "10M": (28.0, 29.7),
    "6M": (50.0, 54.0),
    "2M": (144.0, 148.0),
    "70cm": (420.0, 450.0),
}
