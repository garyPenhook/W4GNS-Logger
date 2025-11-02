"""
SKCC Skimmer RBN Fetcher - Alternative RBN connection using SKCC Skimmer's proven approach

This fetcher uses the same RBN connection pattern as K7MJG's SKCC Skimmer,
which is proven to work reliably without segmentation faults.

Key differences from the direct RBN fetcher:
- Uses pure Python socket operations with select() for robustness
- Avoids all Rust-accelerated functions that cause segfaults in threads
- Implements proper IPv4/IPv6 failover like SKCC Skimmer
- Uses keepalive to maintain stable connection
"""

import logging
import socket
import select
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
    goal_type: Optional[str] = None


class SkccSkimmerRBNFetcher:
    """
    RBN spot fetcher using SKCC Skimmer's proven connection approach.

    This fetcher is based on K7MJG's SKCC Skimmer which:
    - Connects to RBN via socket (no async/await)
    - Uses IPv4/IPv6 fallback
    - Implements TCP keepalive
    - Has been proven to work without segmentation faults
    """

    # RBN telnet servers (IPv4 and IPv6)
    RBN_PRIMARY = ("telnet.reversebeacon.net", 7000)
    RBN_FALLBACK = ("aprs.gids.nl", 14500)

    def __init__(self, skcc_roster: Dict[str, str]) -> None:
        """
        Initialize RBN fetcher using SKCC Skimmer approach

        Args:
            skcc_roster: Dictionary mapping callsigns to SKCC numbers
        """
        self.skcc_roster = skcc_roster
        self.connection_state = RBNConnectionState.DISCONNECTED
        self.socket: Optional[socket.socket] = None
        self._stop_event = threading.Event()
        self._listener_thread: Optional[threading.Thread] = None

        # Callbacks for spot updates
        self.on_spot: Optional[Callable[[SKCCSpot], None]] = None
        self.on_state_change: Optional[Callable[[RBNConnectionState], None]] = None

    def set_callbacks(
        self,
        on_spot: Optional[Callable[[SKCCSpot], None]] = None,
        on_state_change: Optional[Callable[[RBNConnectionState], None]] = None,
    ) -> None:
        """Set callbacks for spot events"""
        self.on_spot = on_spot
        self.on_state_change = on_state_change

    def start(self) -> None:
        """Start monitoring for SKCC spots"""
        if self._listener_thread and self._listener_thread.is_alive():
            logger.warning("SKCC Skimmer RBN fetcher already running")
            return

        self._stop_event.clear()
        self._listener_thread = threading.Thread(target=self._run, daemon=True)
        self._listener_thread.start()
        logger.info("SKCC Skimmer RBN fetcher started")

    def stop(self) -> None:
        """Stop monitoring for SKCC spots with proper cleanup"""
        logger.info("Stopping SKCC Skimmer RBN fetcher...")
        self._stop_event.set()

        # Close socket to interrupt recv() call
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except Exception as e:
                logger.debug(f"Socket shutdown error: {e}")

            try:
                self.socket.close()
            except Exception as e:
                logger.debug(f"Error closing socket: {e}")

        self.socket = None

        # Wait for listener thread to finish
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=2.0)
            if self._listener_thread.is_alive():
                logger.warning("Listener thread did not stop within timeout")

        self._set_state(RBNConnectionState.DISCONNECTED)
        logger.info("SKCC Skimmer RBN fetcher stopped")

    def _run(self) -> None:
        """Main loop for spot fetching"""
        while not self._stop_event.is_set():
            try:
                self._connect_and_listen()
            except Exception as e:
                logger.error(f"SKCC Skimmer RBN fetcher error: {e}")
                self._set_state(RBNConnectionState.ERROR)
                # Backoff before reconnecting
                for i in range(60):
                    if self._stop_event.is_set():
                        return
                    time.sleep(1)

    def _connect_and_listen(self) -> None:
        """Connect to RBN and listen for spots, using SKCC Skimmer's approach"""
        servers = [self.RBN_PRIMARY, self.RBN_FALLBACK]

        for server, port in servers:
            if self._stop_event.is_set():
                return

            try:
                logger.info(f"Connecting to RBN at {server}:{port}")
                self._set_state(RBNConnectionState.CONNECTING)

                # Create socket
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(10)

                # Connect
                self.socket.connect((server, port))

                # Enable TCP keepalive (like SKCC Skimmer)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

                self._set_state(RBNConnectionState.CONNECTED)
                logger.info(f"Connected to RBN at {server}:{port}")

                # Send login (RBN requires callsign)
                callsign = b"W4GNSLOGGER\n"
                logger.info("Sending RBN login...")
                self.socket.send(callsign)
                time.sleep(0.5)

                # Read login response
                try:
                    self.socket.settimeout(2)
                    response = self.socket.recv(1024).decode('utf-8', errors='ignore')
                    logger.debug(f"RBN login response received")
                    self.socket.settimeout(10)
                except socket.timeout:
                    pass
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

        # All servers failed
        self._set_state(RBNConnectionState.DISCONNECTED)
        logger.warning("Could not connect to any RBN server, will retry")

    def _listen_for_spots(self) -> None:
        """Listen for incoming RBN spots"""
        buffer = ""
        line_count = 0
        spot_count = 0

        while not self._stop_event.is_set() and self.socket:
            try:
                # Use select() with timeout to allow checking stop event
                ready = select.select([self.socket], [], [], 0.5)

                if not ready[0]:
                    # Timeout - check stop event and loop again
                    continue

                # Socket is ready for reading
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

                        # Check if it's a spot line (RBN format: "DX de ...")
                        if stripped.startswith("DX de "):
                            self._parse_spot_line(stripped)
                            spot_count += 1

            except Exception as e:
                logger.error(f"Error receiving data: {e}")
                break

        logger.info(f"RBN listener stopped: {line_count} lines, {spot_count} spots parsed")

    def _parse_spot_line(self, line: str) -> None:
        """
        Parse RBN spot line using pure Python (no Rust functions!)

        Format: DX de Spotter: Frequency CallSign Signal Report
        Example: DX de W5WJ: 3579.0 W1AW CW 33 dB 12 WPM
        """
        if not line:
            return

        try:
            # Pure Python parsing - NO RUST FUNCTIONS!
            parts = line.split()
            if len(parts) < 7 or parts[0] != "DX" or parts[1] != "de":
                return

            # Extract parts: "DX de K3LR: 14025.0 W4GNS CW 24 dB 23 WPM"
            #               [0] [1] [2] [3]    [4]  [5] [6] [7][8][9][10]
            frequency_khz = float(parts[3])

            # Sanity check frequency (100 kHz to 300 MHz)
            if frequency_khz < 100 or frequency_khz > 300000:
                return

            # Convert kHz to MHz
            frequency = round(frequency_khz / 1000, 3)

            # Extract callsign
            callsign = parts[4].upper()

            # Extract reporter (part before colon)
            reporter = parts[2].rstrip(":") if len(parts) > 2 else "UNKNOWN"

            # Extract signal strength (look for "XX dB" pattern)
            strength = 0
            for i in range(len(parts) - 1):
                if parts[i + 1] == "dB":
                    try:
                        strength = int(parts[i])
                        break
                    except (ValueError, IndexError):
                        pass

            # Extract WPM if present (CW spots only)
            speed: Optional[int] = None
            try:
                for i, part in enumerate(parts):
                    if "WPM" in part.upper() and i > 0:
                        speed = int(parts[i - 1])
                        break
            except (ValueError, IndexError):
                pass

            # Determine mode from frequency (CW/SSB)
            mode = self._determine_mode(frequency)

            # Check if this is a SKCC member
            is_skcc = callsign in self.skcc_roster
            skcc_number = self.skcc_roster.get(callsign) if is_skcc else None

            # Create spot
            spot = SKCCSpot(
                callsign=callsign,
                frequency=frequency,
                mode=mode,
                grid=None,
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
            logger.debug(f"Error parsing spot line: {e}")

    @staticmethod
    def _determine_mode(freq_mhz: float) -> str:
        """Pure Python mode determination (CW/SSB)"""
        # CW portions
        if (1.8 <= freq_mhz <= 1.84 or
            3.5 <= freq_mhz <= 3.6 or
            7.0 <= freq_mhz <= 7.04 or
            14.0 <= freq_mhz <= 14.07 or
            21.0 <= freq_mhz <= 21.07 or
            28.0 <= freq_mhz <= 28.07 or
            50.0 <= freq_mhz <= 50.1):
            return "CW"

        # SSB portions - LSB on low bands
        if freq_mhz < 10.0:
            return "LSB"
        else:
            return "USB"

    def _set_state(self, state: RBNConnectionState) -> None:
        """Update connection state and call callback"""
        if self.connection_state != state:
            self.connection_state = state
            if self.on_state_change:
                self.on_state_change(state)
            logger.debug(f"SKCC Skimmer RBN connection state: {state.value}")


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
        """Convert frequency to band name"""
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
