"""
SKCC Skimmer Subprocess Manager

Runs K7MJG's SKCC Skimmer as a subprocess and captures its spot output.
This lets SKCC Skimmer do the intelligent filtering while W4GNS-Logger
handles contact logging.
"""

import logging
import subprocess
import threading
import re
from pathlib import Path
from typing import Optional, Callable, List
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class SkimmerConnectionState(Enum):
    """SKCC Skimmer process states"""
    DISCONNECTED = "disconnected"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    STOPPED = "stopped"


class SkccSkimmerSubprocess:
    """
    Manages SKCC Skimmer as a subprocess.

    Runs K7MJG's SKCC Skimmer, captures its console output, and parses
    spots. This lets SKCC Skimmer handle all the intelligent filtering
    based on goals, targets, and ADIF analysis.
    """

    def __init__(self, skimmer_path: Optional[str] = None, adif_file: Optional[str] = None) -> None:
        """
        Initialize SKCC Skimmer subprocess manager

        Args:
            skimmer_path: Path to SKCC Skimmer directory (auto-detect if None)
            adif_file: Path to ADIF master file (passed to SKCC Skimmer config)
        """
        self.skimmer_path = Path(skimmer_path) if skimmer_path else self._find_skimmer()
        self.adif_file = adif_file
        self.process: Optional[subprocess.Popen] = None
        self.state = SkimmerConnectionState.DISCONNECTED
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Callbacks
        self.on_spot: Optional[Callable[[str], None]] = None
        self.on_state_change: Optional[Callable[[SkimmerConnectionState], None]] = None

    @staticmethod
    def _find_skimmer() -> Path:
        """
        Auto-detect SKCC Skimmer installation location

        Common locations:
        - ~/skcc_skimmer/
        - ~/SKCC_Skimmer/
        - /opt/skcc_skimmer/
        - Current directory
        """
        candidates = [
            Path.home() / "skcc_skimmer",
            Path.home() / "SKCC_Skimmer",
            Path.home() / "Downloads" / "skcc_skimmer",
            Path("/opt/skcc_skimmer"),
            Path.cwd() / "skcc_skimmer",
        ]

        for path in candidates:
            if path.exists() and (path / "skcc_skimmer.py").exists():
                logger.info(f"Found SKCC Skimmer at: {path}")
                return path

        # If not found, return home directory (will fail gracefully on start)
        logger.warning("SKCC Skimmer not found in common locations")
        return Path.home() / "skcc_skimmer"

    def set_callbacks(
        self,
        on_spot: Optional[Callable[[str], None]] = None,
        on_state_change: Optional[Callable[[SkimmerConnectionState], None]] = None,
    ) -> None:
        """Set callbacks for events"""
        self.on_spot = on_spot
        self.on_state_change = on_state_change

    def start(self) -> bool:
        """
        Start SKCC Skimmer subprocess

        Returns:
            True if started successfully, False otherwise
        """
        if self.process and self.process.poll() is None:
            logger.warning("SKCC Skimmer already running")
            return True

        try:
            self._set_state(SkimmerConnectionState.STARTING)

            # Check if SKCC Skimmer exists
            skimmer_script = self.skimmer_path / "skcc_skimmer.py"
            if not skimmer_script.exists():
                logger.error(f"SKCC Skimmer not found at: {skimmer_script}")
                self._set_state(SkimmerConnectionState.ERROR)
                return False

            logger.info(f"Starting SKCC Skimmer from: {self.skimmer_path}")

            # Start SKCC Skimmer as subprocess
            self.process = subprocess.Popen(
                ["python3", str(skimmer_script)],
                cwd=str(self.skimmer_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,  # Line buffered
            )

            self._set_state(SkimmerConnectionState.RUNNING)

            # Start reader thread to capture output
            self._stop_event.clear()
            self._reader_thread = threading.Thread(target=self._read_output, daemon=True)
            self._reader_thread.start()

            logger.info("SKCC Skimmer subprocess started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start SKCC Skimmer: {e}", exc_info=True)
            self._set_state(SkimmerConnectionState.ERROR)
            return False

    def stop(self) -> None:
        """Stop SKCC Skimmer subprocess"""
        logger.info("Stopping SKCC Skimmer subprocess...")
        self._stop_event.set()

        if self.process:
            try:
                self.process.terminate()
                # Wait up to 5 seconds for graceful shutdown
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("SKCC Skimmer did not terminate gracefully, killing...")
                self.process.kill()
                self.process.wait()
            except Exception as e:
                logger.error(f"Error stopping SKCC Skimmer: {e}")
            finally:
                self.process = None

        # Wait for reader thread
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=2.0)

        self._set_state(SkimmerConnectionState.STOPPED)
        logger.info("SKCC Skimmer subprocess stopped")

    def _read_output(self) -> None:
        """Read SKCC Skimmer's console output in background thread"""
        if not self.process or not self.process.stdout:
            return

        try:
            for line in iter(self.process.stdout.readline, ""):
                if self._stop_event.is_set():
                    break

                if not line.strip():
                    continue

                logger.debug(f"SKCC Skimmer: {line.strip()}")

                # Check if this is a spot line
                # SKCC Skimmer formats: "HH:MM:SS ± CALLSIGN MEMBER_INFO FREQUENCY MODE DETAILS"
                if self._is_spot_line(line):
                    if self.on_spot:
                        self.on_spot(line.strip())

        except Exception as e:
            logger.error(f"Error reading SKCC Skimmer output: {e}")
            self._set_state(SkimmerConnectionState.ERROR)
        finally:
            if self.process and self.process.poll() is None:
                # Process still running but stream closed
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()

    @staticmethod
    def _is_spot_line(line: str) -> bool:
        """
        Detect if line is a spot output from SKCC Skimmer

        SKCC Skimmer spot format: "HH:MM:SS ± CALLSIGN MEMBER_INFO FREQUENCY MODE DETAILS"
        Example: "14:23:45 + K4ABC (12345T) on 14025.0 kHz CW 23 dB 15 WPM"
        """
        # Look for time pattern at start: HH:MM:SS
        time_pattern = r"^\d{2}:\d{2}:\d{2}"
        # Look for signal/member indicators: +, -, space, or flag
        indicator_pattern = r"[\s+\-◆]"
        # Look for frequency pattern (khz or MHz)
        freq_pattern = r"\d+[,.]?\d*\s*(kHz|MHz)"

        has_time = bool(re.match(time_pattern, line))
        has_indicator = bool(re.search(indicator_pattern, line))
        has_freq = bool(re.search(freq_pattern, line))

        return has_time and has_indicator and has_freq

    def _set_state(self, state: SkimmerConnectionState) -> None:
        """Update connection state and call callback"""
        if self.state != state:
            self.state = state
            if self.on_state_change:
                self.on_state_change(state)
            logger.info(f"SKCC Skimmer state: {state.value}")

    def is_running(self) -> bool:
        """Check if subprocess is running"""
        if not self.process:
            return False
        return self.process.poll() is None
