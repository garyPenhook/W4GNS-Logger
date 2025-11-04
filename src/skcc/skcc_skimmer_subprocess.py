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
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SKCCSpot:
    """Represents a SKCC spot from SKCC Skimmer"""

    callsign: str
    frequency: float
    mode: str
    grid: Optional[str]
    reporter: str
    strength: int
    speed: Optional[int]
    timestamp: datetime
    is_skcc: bool = True
    skcc_number: Optional[str] = None


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
        - ~/apps/skcc_skimmer-master/ (GitHub clone)
        - ~/apps/skcc_skimmer/ (Generic app folder)
        - ~/Downloads/skcc_skimmer/
        - /opt/skcc_skimmer/
        - Current directory
        """
        candidates = [
            # Apps directory first (GitHub clones) - PRIORITY
            Path.home() / "apps" / "skcc_skimmer-master",
            Path.home() / "apps" / "skcc_skimmer",
            Path.home() / "apps" / "SKCC_Skimmer",
            # Standard locations
            Path.home() / "skcc_skimmer",
            Path.home() / "SKCC_Skimmer",
            # Downloads and other common locations
            Path.home() / "Downloads" / "skcc_skimmer",
            Path.home() / "Downloads" / "skcc_skimmer-master",
            # System-wide locations
            Path("/opt/skcc_skimmer"),
            Path("/usr/local/skcc_skimmer"),
            # Current directory
            Path.cwd() / "skcc_skimmer",
            Path.cwd() / "skcc_skimmer-master",
        ]

        for path in candidates:
            if path.exists() and (path / "skcc_skimmer.py").exists():
                logger.info(f"Found SKCC Skimmer at: {path}")
                return path

        # If not found, return default location (will fail gracefully on start)
        logger.warning("SKCC Skimmer not found in common locations")
        logger.warning(f"Searched: {', '.join(str(p) for p in candidates)}")
        return Path.home() / "skcc_skimmer"

    def set_callbacks(
        self,
        on_spot: Optional[Callable[[str], None]] = None,
        on_state_change: Optional[Callable[[SkimmerConnectionState], None]] = None,
    ) -> None:
        """Set callbacks for events"""
        self.on_spot = on_spot
        self.on_state_change = on_state_change

    def update_config(
        self,
        callsign: str = "",
        grid: str = "",
        adif_file: str = "",
        goals: str = "ALL,-BRAG,-K3Y",
        targets: str = "C,T,S",
    ) -> bool:
        """
        Update SKCC Skimmer configuration file before starting

        Args:
            callsign: Your ham radio callsign
            grid: Your grid square (e.g., EM87ui)
            adif_file: Path to your ADIF file
            goals: Comma-separated award goals (e.g., "ALL,-BRAG,-K3Y")
            targets: Award targets (e.g., "C,T,S" for Centurion/Tribune/Senator)

        Returns:
            True if config updated successfully
        """
        try:
            config_path = self.skimmer_path / "skcc_skimmer.cfg"
            if not config_path.exists():
                logger.warning(f"SKCC Skimmer config not found at: {config_path}")
                return False

            # Read current config
            with open(config_path, "r") as f:
                config_content = f.read()

            # Update configuration values
            import re

            # Update MY_CALLSIGN
            if callsign:
                config_content = re.sub(
                    r"MY_CALLSIGN\s*=\s*['\"].*?['\"]",
                    f"MY_CALLSIGN    = '{callsign.upper()}'",
                    config_content,
                )

            # Update MY_GRIDSQUARE
            if grid:
                config_content = re.sub(
                    r"MY_GRIDSQUARE\s*=\s*['\"].*?['\"]",
                    f"MY_GRIDSQUARE  = '{grid.upper()}'",
                    config_content,
                )

            # Update ADI_FILE
            if adif_file:
                # Escape backslashes for Windows paths
                adif_file_escaped = adif_file.replace("\\", "\\\\")
                config_content = re.sub(
                    r"ADI_FILE\s*=\s*r?['\"].*?['\"]",
                    f"ADI_FILE       = r'{adif_file_escaped}'",
                    config_content,
                )

            # Update GOALS
            if goals:
                config_content = re.sub(
                    r"GOALS\s*=\s*['\"].*?['\"]", f"GOALS          = '{goals}'", config_content
                )

            # Update TARGETS
            if targets:
                config_content = re.sub(
                    r"TARGETS\s*=\s*['\"].*?['\"]", f"TARGETS        = '{targets}'", config_content
                )

            # Write updated config
            with open(config_path, "w") as f:
                f.write(config_content)

            logger.info(
                f"Updated SKCC Skimmer config: callsign={callsign}, grid={grid}, goals={goals}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to update SKCC Skimmer config: {e}", exc_info=True)
            return False

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

            # Try to use the ./run script first (handles venv and dependencies)
            run_script = self.skimmer_path / "run"
            if run_script.exists() and run_script.is_file():
                logger.info("Using SKCC Skimmer's run script (recommended method)")
                # Use the run script which handles virtual environment
                # Merge stderr into stdout so we capture all output
                self.process = subprocess.Popen(
                    ["bash", str(run_script)],
                    cwd=str(self.skimmer_path),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    bufsize=1,
                )
                # Start a separate thread to read stderr
                self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
                self._stderr_thread.start()
            else:
                logger.warning("./run script not found, attempting direct python3 execution")
                # Fallback to direct python3 (may fail if dependencies missing)
                self.process = subprocess.Popen(
                    ["python3", str(skimmer_script)],
                    cwd=str(self.skimmer_path),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    bufsize=1,
                )
                # Start a separate thread to read stderr
                self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
                self._stderr_thread.start()

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
            line_count = 0
            spot_count = 0
            all_lines = []
            for line in iter(self.process.stdout.readline, ""):
                if self._stop_event.is_set():
                    break

                if not line.strip():
                    continue

                line_count += 1
                all_lines.append(line.strip())
                logger.info(f"[SKCC LINE {line_count}] {line.strip()}")

                # Check if this is a spot line
                if self._is_spot_line(line):
                    spot_count += 1
                    logger.info(f"[SPOT #{spot_count}] {line.strip()}")
                    if self.on_spot:
                        self.on_spot(line.strip())

        except Exception as e:
            logger.error(f"Error reading SKCC Skimmer output: {e}")
            self._set_state(SkimmerConnectionState.ERROR)
        finally:
            logger.info(f"[SKCC SUMMARY] Received {line_count} lines, {spot_count} spots detected")
            if line_count > 0 and spot_count == 0:
                logger.warning(f"[DEBUG] Sample lines (first 3):")
                for i, line in enumerate(all_lines[:3], 1):
                    logger.warning(f"  Line {i}: {line}")
            if self.process and self.process.poll() is None:
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()

    @staticmethod
    def _is_spot_line(line: str) -> bool:
        """
        Detect if line is a spot output from SKCC Skimmer

        Formats:
        - RBN: "HH:MM:SS ± CALLSIGN (SKCC#) on FREQUENCY MHz MODE"
        - Sked: "HHMM[Z] CALLSIGN (SKCC#) TEXT"
        """
        if not line or len(line) < 6:
            return False

        # Time can be HH:MM:SS or HHMM format
        time_pattern = r"^\d{1,2}:\d{2}:\d{2}|^\d{3,4}Z?"
        if not re.match(time_pattern, line):
            return False

        # Must have a callsign (2+ alphanumeric)
        if not re.search(r"\s([A-Z0-9]{2,})\s", line):
            return False

        # Skip non-spot lines (status/info messages)
        non_spot_keywords = [
            "connected",
            "running",
            "retrieving",
            "reading",
            "processing",
            "found",
            "finding",
            "goals",
            "targets",
            "bands",
            "progress",
            "qualifies",
            "requires",
            "award",
            "rosters",
            "centurion",
            "tribune",
            "senator",
            "page",
            "sked",
            "rrn",
            "version",
            "cfg",
        ]
        line_lower = line.lower()
        for keyword in non_spot_keywords:
            if keyword in line_lower:
                return False

        return True

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

    def _read_stderr(self) -> None:
        """Read SKCC Skimmer's stderr in background thread"""
        if not self.process or not self.process.stderr:
            return

        try:
            for line in iter(self.process.stderr.readline, ""):
                if self._stop_event.is_set():
                    break

                if not line.strip():
                    continue

                logger.error(f"[SKCC STDERR] {line.strip()}")

        except Exception as e:
            logger.error(f"Error reading SKCC Skimmer stderr: {e}")
