"""
SKCC Skimmer Integration

Handles communication with SKCC Skimmer for real-time spot monitoring,
QSO analysis, and award tracking. Allows bidirectional data flow:
- Export current log for SKCC Skimmer analysis
- Import new QSOs from SKCC Skimmer
- Monitor RBN spots for needed stations
- Track award progress

SKCC Skimmer: https://www.k7mjg.com/SKCC_Skimmer
"""

import logging
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class RBNSpot:
    """Represents a spot from Reverse Beacon Network"""
    callsign: str
    frequency: float
    mode: str
    timestamp: str
    spotter: str
    snr: int = 0
    wpm: int = 0
    distance: Optional[float] = None
    bearing: Optional[int] = None
    goal_type: Optional[str] = None  # "GOAL", "TARGET", "BOTH", None
    reason: str = ""  # Why this spot is interesting (e.g., "need for C", "helps you for T")

    def to_dict(self) -> Dict[str, Any]:
        """Convert spot to dictionary"""
        return asdict(self)


class SKCCSkimmerIntegration:
    """
    Manages integration with SKCC Skimmer application

    Capabilities:
    - Export log to SKCC Skimmer format
    - Parse SKCC Skimmer output for RBN spots
    - Import QSOs from SKCC Skimmer analysis
    - Track spots and statistics
    """

    # SKCC Skimmer configuration
    SKIMMER_LOCATIONS = [
        Path.home() / "skcc_skimmer",  # Default install location
        Path.home() / "Applications" / "skcc_skimmer",  # macOS
        Path("C:/Program Files/skcc_skimmer"),  # Windows
        Path("C:/Program Files (x86)/skcc_skimmer"),  # Windows 32-bit
    ]

    def __init__(self, config_manager: Any):
        """
        Initialize SKCC Skimmer integration

        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.skimmer_path: Optional[Path] = None
        self.is_running = False
        self.process: Optional[subprocess.Popen] = None
        self.spots: List[RBNSpot] = []
        self.last_spot_time: Optional[str] = None
        self.spot_statistics = {
            "total_spots": 0,
            "goal_spots": 0,
            "target_spots": 0,
            "unique_callsigns": set(),
        }

        self._locate_skimmer()

    def _locate_skimmer(self) -> None:
        """Locate SKCC Skimmer installation"""
        for location in self.SKIMMER_LOCATIONS:
            if location.exists():
                self.skimmer_path = location
                logger.info(f"Found SKCC Skimmer at: {self.skimmer_path}")
                return

        logger.warning(
            "SKCC Skimmer not found. Install from: https://www.k7mjg.com/SKCC_Skimmer"
        )

    def is_available(self) -> bool:
        """Check if SKCC Skimmer is installed and available"""
        return self.skimmer_path is not None and self.skimmer_path.exists()

    def get_skimmer_path(self) -> Optional[Path]:
        """Get path to SKCC Skimmer installation"""
        return self.skimmer_path

    def export_log_for_analysis(
        self, contacts: List[Dict[str, Any]], output_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Export current log in SKCC Skimmer compatible format

        Args:
            contacts: List of contact dictionaries from database
            output_path: Optional output file path. Defaults to ~/.w4gns_logger/skimmer_export.adi

        Returns:
            Dictionary with:
            - success: bool
            - file_path: Path to exported file
            - contact_count: Number of contacts exported
            - message: Human-readable status

        Note:
            Exported file includes all required SKCC Skimmer fields:
            - CALL: Callsign
            - QSO_DATE: Date in YYYYMMDD format
            - TIME_ON: UTC time in HHMM format
            - FREQ: Frequency in MHz
            - MODE: CW (filtered for CW only)
            - RST_SENT: Report sent
            - RST_RCVD: Report received
            - TX_PWR: Transmit power (for QRP awards)
            - RX_PWR: Receive power (for 2xQRP)
            - APP_SKCCLOGGER_KEYTYPE: Key type (SK/BUG/SS)
            - SKCC: SKCC number
        """
        try:
            if output_path is None:
                output_path = Path.home() / ".w4gns_logger" / "skimmer_export.adi"

            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Filter to CW mode only and build ADIF
            adif_lines = ["<ADIF_VER:5>3.1.0", "<PROGRAMID:15>W4GNS SKCC Logger", "<EOH>\n"]

            exported_count = 0
            for contact in contacts:
                # Only export CW mode contacts
                mode = contact.get("mode", "").upper()
                if mode != "CW":
                    continue

                # Build ADIF record
                record_parts = []

                # Mandatory fields
                if callsign := contact.get("callsign"):
                    record_parts.append(f"<CALL:{len(callsign)}>{callsign}")

                if qso_date := contact.get("qso_date"):
                    # Format: YYYYMMDD
                    try:
                        if isinstance(qso_date, str):
                            date_str = qso_date.replace("-", "")
                        else:
                            date_str = qso_date.strftime("%Y%m%d")
                        record_parts.append(f"<QSO_DATE:8>{date_str}")
                    except Exception as e:
                        logger.warning(f"Error formatting date for {callsign}: {e}")
                        continue

                if time_on := contact.get("time_on"):
                    # Format: HHMM
                    try:
                        if isinstance(time_on, str):
                            time_str = time_on.replace(":", "")[:4]
                        else:
                            time_str = time_on.strftime("%H%M")
                        record_parts.append(f"<TIME_ON:4>{time_str}")
                    except Exception as e:
                        logger.warning(f"Error formatting time for {callsign}: {e}")
                        continue

                if freq := contact.get("frequency"):
                    record_parts.append(f"<FREQ:5>{float(freq):.5f}")

                # Mode (CW only - already filtered)
                record_parts.append("<MODE:2>CW")

                # Optional but useful fields
                if rst_sent := contact.get("rst_sent"):
                    record_parts.append(f"<RST_SENT:3>{rst_sent}")

                if rst_rcvd := contact.get("rst_rcvd"):
                    record_parts.append(f"<RST_RCVD:3>{rst_rcvd}")

                if tx_pwr := contact.get("tx_power"):
                    try:
                        record_parts.append(f"<TX_PWR:3>{float(tx_pwr):.0f}")
                    except (ValueError, TypeError):
                        pass

                if rx_pwr := contact.get("rx_power"):
                    try:
                        record_parts.append(f"<RX_PWR:3>{float(rx_pwr):.0f}")
                    except (ValueError, TypeError):
                        pass

                # Key type for TKA award
                if key_type := contact.get("key_type"):
                    key_type = key_type.upper()
                    if key_type in ("SK", "BUG", "SS"):
                        record_parts.append(
                            f"<APP_SKCCLOGGER_KEYTYPE:{len(key_type)}>{key_type}"
                        )

                # SKCC number
                if skcc := contact.get("skcc_number"):
                    record_parts.append(f"<SKCC:{len(str(skcc))}>{skcc}")

                # End of record
                record_parts.append("<EOR>")

                adif_lines.append(" ".join(record_parts))
                exported_count += 1

            # Write ADIF file
            with open(output_path, "w") as f:
                f.write("\n".join(adif_lines))

            logger.info(f"Exported {exported_count} CW contacts to: {output_path}")

            return {
                "success": True,
                "file_path": output_path,
                "contact_count": exported_count,
                "message": f"Successfully exported {exported_count} CW contacts",
            }

        except Exception as e:
            error_msg = f"Error exporting log for SKCC Skimmer: {e}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "file_path": output_path if output_path else None,
                "contact_count": 0,
                "message": error_msg,
            }

    def parse_skimmer_spots(self, spot_text: str) -> List[RBNSpot]:
        """
        Parse RBN spots from SKCC Skimmer output

        Args:
            spot_text: Raw spot text from SKCC Skimmer

        Returns:
            List of RBNSpot objects

        Note:
            Typical RBN spot format from SKCC Skimmer:
            "K1ABC 14.055 CW 23:45Z de W5XYZ @ 1234 km, 45 wpm, +15 dB"
        """
        spots = []
        try:
            for line in spot_text.strip().split("\n"):
                if not line.strip():
                    continue

                # Simple parsing - adjust based on actual SKCC Skimmer output format
                parts = line.split()
                if len(parts) < 3:
                    continue

                try:
                    spot = RBNSpot(
                        callsign=parts[0],
                        frequency=float(parts[1]),
                        mode=parts[2],
                        timestamp=datetime.utcnow().isoformat(),
                        spotter="RBN",
                    )
                    spots.append(spot)
                    self.spot_statistics["unique_callsigns"].add(spot.callsign)
                except (ValueError, IndexError) as e:
                    logger.debug(f"Skipping malformed spot: {line}, error: {e}")
                    continue

            self.spot_statistics["total_spots"] += len(spots)
            self.spots.extend(spots)
            logger.debug(f"Parsed {len(spots)} spots from SKCC Skimmer output")

        except Exception as e:
            logger.error(f"Error parsing SKCC Skimmer spots: {e}", exc_info=True)

        return spots

    def get_recent_spots(self, limit: int = 50) -> List[RBNSpot]:
        """
        Get most recent spots

        Args:
            limit: Maximum number of spots to return

        Returns:
            List of most recent RBNSpot objects
        """
        return self.spots[-limit:] if self.spots else []

    def get_spot_statistics(self) -> Dict[str, Any]:
        """
        Get spot statistics

        Returns:
            Dictionary with:
            - total_spots: Total number of spots received
            - unique_callsigns: Number of unique callsigns spotted
            - goal_spots: Spots for your goals
            - target_spots: Spots where you can help others
        """
        return {
            "total_spots": self.spot_statistics["total_spots"],
            "unique_callsigns": len(self.spot_statistics["unique_callsigns"]),
            "goal_spots": self.spot_statistics["goal_spots"],
            "target_spots": self.spot_statistics["target_spots"],
        }

    def get_integration_status(self) -> Dict[str, Any]:
        """
        Get current integration status

        Returns:
            Dictionary with:
            - available: SKCC Skimmer installed and available
            - path: Path to SKCC Skimmer
            - is_running: Whether integration is currently active
            - recent_spots: Number of recent spots
            - statistics: Spot statistics
        """
        return {
            "available": self.is_available(),
            "path": str(self.skimmer_path) if self.skimmer_path else None,
            "is_running": self.is_running,
            "recent_spots": len(self.spots),
            "statistics": self.get_spot_statistics(),
        }

    def get_configuration_template(self) -> str:
        """
        Get template SKCC Skimmer configuration

        Returns:
            Configuration file content template
        """
        my_callsign = self.config_manager.get("general.operator_callsign", "MYCALL")
        my_grid = self.config_manager.get("adif.my_grid_square", "")
        goals = self.config_manager.get("skimmer.goals", "C,T,S")
        targets = self.config_manager.get("skimmer.targets", "C,T,S")

        return f"""# SKCC Skimmer Configuration for W4GNS SKCC Logger Integration
# Generated: {datetime.now().isoformat()}

# Your callsign
MY_CALLSIGN = '{my_callsign}'

# Your Maidenhead grid square (4 or 6 characters)
MY_GRIDSQUARE = '{my_grid}'

# ADI log file - point to your exported log
ADI_FILE = r'{{EXPORT_PATH}}'

# Award goals you're working toward
GOALS = '{goals}'

# Awards you help others achieve
TARGETS = '{targets}'

# Optional settings
SPOTTER_RADIUS = 500  # Miles from your location
BANDS = '160 80 60 40 30 20 17 15 12 10 6 2'  # Bands to monitor
NOTIFICATION = 'on'  # Audio notification on new spots
DISTANCE_UNITS = 'mi'  # or 'km'
SKED = 'on'  # Monitor SKCC Sked Page
LOG_FILE = 'skcc_skimmer.log'  # Save spots to file

# Exclude certain callsigns (beacons, etc)
EXCLUSIONS = ''

# High priority callsigns (get highlighted)
FRIENDS = ''

# High speed CW handling: display, warn, or suppress
HIGH_WPM = 'display'

# Off-frequency spot handling: display, warn, or suppress
OFF_FREQUENCY = 'display'
"""


# Convenience function for integration
def get_skimmer_integration(config_manager: Any) -> SKCCSkimmerIntegration:
    """
    Factory function to create SKCC Skimmer integration

    Args:
        config_manager: Configuration manager instance

    Returns:
        SKCCSkimmerIntegration instance
    """
    return SKCCSkimmerIntegration(config_manager)
