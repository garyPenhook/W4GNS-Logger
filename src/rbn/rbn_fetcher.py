"""
RBN (Reverse Beacon Network) Spot Fetcher - Telnet Stream

Connects to rbn.telegraphy.de:7000 and reads live CW spot stream
"""

import logging
import threading
import socket
from datetime import datetime, timezone
from typing import Optional, Callable
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RBNSpot:
    """Represents a CW spot from RBN"""

    callsign: str
    frequency: float  # MHz
    mode: str = "CW"
    grid: Optional[str] = None
    reporter: str = ""
    strength: int = 0  # dB
    speed: Optional[int] = None  # WPM
    timestamp: Optional[datetime] = None
    skcc_number: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class RBNConnectionState(Enum):
    """RBN connection states"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    RUNNING = "running"
    ERROR = "error"
    STOPPED = "stopped"


class RBNFetcher:
    """Fetches spots from Telegraphy.de RBN telnet stream"""

    HOST = "rbn.telegraphy.de"
    PORT = 7000

    def __init__(self):
        self.state = RBNConnectionState.DISCONNECTED
        self._running = False
        self._socket: Optional[socket.socket] = None
        self._read_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.on_spot: Optional[Callable[[RBNSpot], None]] = None
        self.on_state_change: Optional[Callable[[RBNConnectionState], None]] = None
        self.my_callsign: Optional[str] = None

    def set_callbacks(
        self,
        on_spot: Optional[Callable[[RBNSpot], None]] = None,
        on_state_change: Optional[Callable[[RBNConnectionState], None]] = None,
    ) -> None:
        """Set callbacks for events"""
        self.on_spot = on_spot
        self.on_state_change = on_state_change

    def start(self) -> bool:
        """Start fetching RBN spots"""
        if self._running:
            logger.warning("RBN fetcher already running")
            return True

        try:
            self._set_state(RBNConnectionState.CONNECTING)
            self._running = True
            self._stop_event.clear()
            self._read_thread = threading.Thread(target=self._connect_and_read, daemon=True)
            self._read_thread.start()
            logger.info("RBN fetcher started")
            return True
        except Exception as e:
            logger.error(f"Failed to start RBN fetcher: {e}")
            self._set_state(RBNConnectionState.ERROR)
            return False

    def stop(self) -> None:
        """Stop fetching RBN spots"""
        logger.info("Stopping RBN fetcher...")
        self._running = False
        self._stop_event.set()

        if self._socket:
            try:
                self._socket.close()
            except:
                pass
            self._socket = None

        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=5)

        self._set_state(RBNConnectionState.STOPPED)

    def _connect_and_read(self) -> None:
        """Connect to RBN telnet stream and read spots"""
        retries = 0
        while self._running and retries < 10:
            try:
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.settimeout(10)
                logger.info(f"Connecting to {self.HOST}:{self.PORT}")
                self._socket.connect((self.HOST, self.PORT))
                logger.info("Connected to RBN")
                self._set_state(RBNConnectionState.RUNNING)
                retries = 0

                # Step 1: Read server banner asking for callsign
                try:
                    banner = self._socket.recv(4096).decode("utf-8", errors="ignore")
                    logger.debug(f"Server banner: {repr(banner)}")
                except socket.timeout:
                    logger.debug("No initial banner received (timeout)")
                except Exception as e:
                    logger.debug(f"Error reading banner: {e}")

                # Step 2: Send callsign to authenticate
                callsign = self.my_callsign or "W4GNS"  # Use real callsign, not ANONYMOUS
                logger.debug(f"Sending callsign: {callsign}")
                self._socket.send(f"{callsign}\n".encode("utf-8"))

                # Step 3: Read welcome message after callsign
                try:
                    response = self._socket.recv(4096).decode("utf-8", errors="ignore")
                    logger.debug(f"After callsign: {repr(response)}")
                except socket.timeout:
                    logger.debug("No response after callsign (timeout)")

                # Step 4: Send set/raw to receive all spots (not just club-filtered)
                logger.debug("Sending 'set/raw' command")
                self._socket.send(b"set/raw\n")

                # Step 5: Read confirmation of set/raw
                try:
                    response = self._socket.recv(4096).decode("utf-8", errors="ignore")
                    logger.debug(f"After set/raw: {repr(response)}")
                except socket.timeout:
                    logger.debug("No response after set/raw (timeout)")

                # Step 6: Send set/nodupes to reduce traffic
                logger.debug("Sending 'set/nodupes' command")
                self._socket.send(b"set/nodupes\n")

                # Step 7: Read confirmation of set/nodupes
                try:
                    response = self._socket.recv(4096).decode("utf-8", errors="ignore")
                    logger.debug(f"After set/nodupes: {repr(response)}")
                except socket.timeout:
                    logger.debug("No response after set/nodupes (timeout)")

                # Set longer timeout for reading stream
                self._socket.settimeout(30)
                self._read_stream()

            except Exception as e:
                retries += 1
                logger.error(f"Connection error (retry {retries}/10): {type(e).__name__}: {e}")
                if self._socket:
                    try:
                        self._socket.close()
                    except:
                        pass
                    self._socket = None

                if self._running and retries < 10:
                    import time

                    time.sleep(min(5 * retries, 30))

        if retries >= 10:
            logger.error("Max retries reached")
            self._set_state(RBNConnectionState.ERROR)

    def _read_stream(self) -> None:
        """Read from RBN telnet stream"""
        if not self._socket:
            logger.error("Socket is None in _read_stream")
            return

        buffer = ""
        try:
            while self._running and not self._stop_event.is_set():
                try:
                    data = self._socket.recv(4096).decode("utf-8", errors="ignore")
                    if not data:
                        logger.info("Connection closed by server (empty data)")
                        break

                    buffer += data
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()

                        if line.startswith("DX de "):
                            try:
                                spot = self._parse_line(line)
                                if spot and self.on_spot:
                                    logger.info(
                                        f"[RBN] {spot.callsign} {spot.frequency:.1f}M dB={spot.strength} wpm={spot.speed or 0}"
                                    )
                                    self.on_spot(spot)
                            except Exception as e:
                                logger.debug(f"Parse error: {e}")
                        elif line:
                            logger.debug(f"[RBN] Non-spot line: {line}")

                except socket.timeout:
                    logger.debug("Socket timeout (normal)")
                    continue
                except Exception as e:
                    logger.error(f"Recv error: {type(e).__name__}: {e}")
                    break

        except Exception as e:
            logger.error(f"Stream read error: {type(e).__name__}: {e}")
        finally:
            logger.debug("_read_stream exiting")

    def _parse_line(self, line: str) -> Optional[RBNSpot]:
        """
        Parse RBN spot line format:
        DX de <spotter> <freq_khz> <callsign> <mode> <snr> <wpm> <activity> <timestamp>

        Example: DX de LZ5DI-#:    7026.1  ON6QS          CW     6 dB  18 WPM  CQ      1544Z
        """
        try:
            # Remove multiple spaces and split
            parts = line.split()

            # Expected format: DX de SPOTTER FREQ CALLSIGN MODE SNR WPM ACTIVITY TIME
            if len(parts) < 9:
                return None

            # Skip "DX" and "de"
            if parts[0] != "DX" or parts[1] != "de":
                return None

            reporter = parts[2].rstrip(":")  # Remove trailing colon from spotter call
            freq_mhz = float(parts[3])
            callsign = parts[4].upper()
            mode = parts[5]  # CW, SSB, etc.

            # Parse SNR (e.g., "6" or "28")
            strength = int(parts[6]) if parts[6].isdigit() else 0

            # Parse WPM (e.g., "18" or "28")
            speed = None
            if len(parts) > 7:
                try:
                    speed = int(parts[7])
                except ValueError:
                    pass

            return RBNSpot(
                callsign=callsign,
                frequency=freq_mhz,
                reporter=reporter,
                strength=strength,
                speed=speed,
                mode=mode,
            )
        except (ValueError, IndexError):
            return None

    def _set_state(self, state: RBNConnectionState) -> None:
        """Update state"""
        if self.state != state:
            self.state = state
            if self.on_state_change:
                self.on_state_change(state)
            logger.info(f"RBN state: {state.value}")

    def is_running(self) -> bool:
        """Check if running"""
        return self._running
