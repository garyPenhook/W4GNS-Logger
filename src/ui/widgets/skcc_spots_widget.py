"""
SKCC Spots Widget - Display and manage SKCC member spots

Shows recent SKCC member spots from RBN with filtering and integration
with the logging form.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QComboBox, QCheckBox, QSpinBox, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from src.skcc import SKCCSpotManager, SKCCSpot, SKCCSpotFilter, RBNConnectionState

logger = logging.getLogger(__name__)


class SKCCSpotStatusIndicator(QLabel):
    """Status indicator for RBN connection"""

    def __init__(self):
        super().__init__()
        self.setFixedSize(16, 16)
        self.update_state(RBNConnectionState.DISCONNECTED)

    def update_state(self, state: RBNConnectionState) -> None:
        """Update indicator color based on connection state"""
        colors = {
            RBNConnectionState.DISCONNECTED: "#cccccc",
            RBNConnectionState.CONNECTING: "#ffff00",
            RBNConnectionState.CONNECTED: "#00ff00",
            RBNConnectionState.ERROR: "#ff0000",
        }
        color = colors.get(state, "#cccccc")
        self.setStyleSheet(f"background-color: {color}; border-radius: 8px;")
        self.setToolTip(f"RBN Status: {state.value}")


class SKCCSpotRow:
    """Represents a row in the spots table"""

    def __init__(self, spot: SKCCSpot):
        self.spot = spot
        self.callsign = spot.callsign
        self.frequency = f"{spot.frequency:.1f}"
        self.mode = spot.mode
        self.speed = f"{spot.speed} WPM" if spot.speed else ""
        self.reporter = spot.reporter
        self.time = spot.timestamp.strftime("%H:%M:%S")
        self.age_seconds = (datetime.utcnow() - spot.timestamp).total_seconds()

    def get_age_string(self) -> str:
        """Get human-readable age string"""
        if self.age_seconds < 60:
            return f"{int(self.age_seconds)}s"
        elif self.age_seconds < 3600:
            return f"{int(self.age_seconds / 60)}m"
        else:
            return f"{int(self.age_seconds / 3600)}h"


class SKCCSpotWidget(QWidget):
    """Widget for displaying and managing SKCC spots"""

    # Signal when user clicks on a spot (to populate logging form)
    spot_selected = pyqtSignal(str, float)  # callsign, frequency

    def __init__(self, spot_manager: SKCCSpotManager, parent: Optional[QWidget] = None):
        """
        Initialize SKCC spots widget

        Args:
            spot_manager: SKCCSpotManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.spot_manager = spot_manager
        self.spots: List[SKCCSpot] = []
        self.filtered_spots: List[SKCCSpot] = []

        # Cache for award-critical spots
        self.award_critical_skcc_members: set = set()
        self.worked_skcc_members: set = set()
        self._refresh_award_cache()

        # Duplicate detection: track last time each callsign was shown (3-minute cooldown)
        self.last_shown_time: Dict[str, datetime] = {}
        self.duplicate_cooldown_seconds = 180  # 3 minutes

        # Set up UI
        self._init_ui()
        self._connect_signals()

        # Refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_spots)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds

        # Auto-cleanup timer
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._cleanup_old_spots)
        self.cleanup_timer.start(300000)  # Cleanup every 5 minutes

        # Award cache refresh timer (refresh every minute)
        self.award_cache_timer = QTimer()
        self.award_cache_timer.timeout.connect(self._refresh_award_cache)
        self.award_cache_timer.start(60000)

    def _init_ui(self) -> None:
        """Initialize UI components"""
        layout = QVBoxLayout()

        # Header section
        header_layout = QHBoxLayout()

        # Status indicator
        self.status_indicator = SKCCSpotStatusIndicator()
        header_layout.addWidget(QLabel("RBN Status:"))
        header_layout.addWidget(self.status_indicator)

        # Sync roster button
        self.sync_btn = QPushButton("Sync Roster")
        self.sync_btn.clicked.connect(self._sync_roster)
        header_layout.addWidget(self.sync_btn)

        # Test data button (for development)
        self.test_btn = QPushButton("Load Test Data")
        self.test_btn.clicked.connect(self._load_test_data)
        self.test_btn.setToolTip("Load test SKCC members for development (no internet required)")
        header_layout.addWidget(self.test_btn)

        # Diagnostics button
        self.diag_btn = QPushButton("Test RBN")
        self.diag_btn.setToolTip("Test RBN connection (if real spots don't work)")
        self.diag_btn.clicked.connect(self._test_rbn_connection)
        header_layout.addWidget(self.diag_btn)

        # Connection button
        self.connect_btn = QPushButton("Start Monitoring")
        self.connect_btn.clicked.connect(self._toggle_monitoring)
        header_layout.addWidget(self.connect_btn)

        header_layout.addStretch()

        # Spot count
        self.spot_count_label = QLabel("Spots: 0")
        font = QFont()
        font.setBold(True)
        self.spot_count_label.setFont(font)
        header_layout.addWidget(self.spot_count_label)

        layout.addLayout(header_layout)

        # Filter section
        filter_layout = QHBoxLayout()

        # Band filter
        filter_layout.addWidget(QLabel("Band:"))
        self.band_combo = QComboBox()
        self.band_combo.addItem("All Bands")
        for band in ["160M", "80M", "60M", "40M", "30M", "20M", "17M", "15M", "12M", "10M", "6M", "2M", "70cm"]:
            self.band_combo.addItem(band)
        self.band_combo.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.band_combo)

        # Mode filter
        filter_layout.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("All Modes")
        for mode in ["CW", "SSB", "FM", "RTTY", "PSK31", "JT65", "FT8"]:
            self.mode_combo.addItem(mode)
        self.mode_combo.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.mode_combo)

        # Min signal strength
        filter_layout.addWidget(QLabel("Min Strength (dB):"))
        self.strength_spin = QSpinBox()
        self.strength_spin.setRange(0, 50)
        self.strength_spin.setValue(0)
        self.strength_spin.valueChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.strength_spin)

        # Unworked only
        self.unworked_only_check = QCheckBox("Unworked Only")
        self.unworked_only_check.stateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.unworked_only_check)

        filter_layout.addStretch()

        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_spots)
        filter_layout.addWidget(self.refresh_btn)

        layout.addLayout(filter_layout)

        # Status label (with word wrap for multi-line messages)
        self.status_label = QLabel("Ready to start monitoring")
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(40)
        status_font = self.status_label.font()
        status_font.setPointSize(9)
        self.status_label.setFont(status_font)
        layout.addWidget(self.status_label)

        # Spots table
        self.spots_table = QTableWidget()
        self.spots_table.setColumnCount(7)
        self.spots_table.setHorizontalHeaderLabels([
            "Callsign", "Frequency", "Mode", "Speed", "Reporter", "Time", "Age"
        ])
        self.spots_table.itemSelectionChanged.connect(self._on_spot_selected)
        self.spots_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.spots_table)

        self.setLayout(layout)

    def _connect_signals(self) -> None:
        """Connect spot manager signals"""
        self.spot_manager.set_callbacks(
            on_new_spot=self._on_new_spot,
            on_connection_state=self._on_connection_state_changed,
        )

    def _sync_roster(self) -> None:
        """Sync SKCC membership roster - force fresh download"""
        try:
            self.sync_btn.setEnabled(False)
            self.status_label.setText("Status: Clearing cache and downloading fresh roster... (may take 30 seconds)")

            # Force fresh download by clearing cache first
            logger.info("Force-clearing SKCC roster cache for fresh download...")
            self.spot_manager.db.skcc_members.clear_cache()

            # Now sync - this will force a download since cache is empty
            success = self.spot_manager.db.skcc_members.sync_membership_data()
            roster_count = self.spot_manager.db.skcc_members.get_member_count()

            if success and roster_count > 100:  # Real roster should have thousands
                self.status_label.setText(f"✓ SUCCESS: {roster_count} real SKCC members loaded! Click Start Monitoring for real spots.")
                logger.info(f"Successfully downloaded real SKCC roster: {roster_count} members")
            elif roster_count > 0:
                self.status_label.setText(f"⚠️  Roster has {roster_count} members (expected 1000+). Real roster download may have failed.")
                logger.warning(f"Roster download returned {roster_count} members - may be test data or partial")
            else:
                self.status_label.setText("❌ Roster sync failed - check network connection. Use Load Test Data to continue.")
                logger.error("Roster sync failed - 0 members")

            # Switch to RBN mode when syncing real roster
            self.spot_manager.use_test_spots = False
            logger.info("Switched to RBN mode (real spots)")

            # Refresh award cache with new roster
            self._refresh_award_cache()

        except Exception as e:
            logger.error(f"Error syncing roster: {e}", exc_info=True)
            self.status_label.setText(f"Error syncing roster: {str(e)}")
        finally:
            self.sync_btn.setEnabled(True)

    def _test_rbn_connection(self) -> None:
        """Test RBN server connectivity"""
        import socket

        self.diag_btn.setEnabled(False)
        self.status_label.setText("Testing RBN servers...")

        rbn_servers = [
            ("telnet.reversebeacon.net", 7000),
            ("aprs.gids.nl", 14500),
            ("rbn.telegraphy.net", 7000),  # Alternative
        ]

        results = []
        for server, port in rbn_servers:
            try:
                logger.info(f"Testing {server}:{port}...")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((server, port))

                # Try to receive initial data
                sock.send(b"hello\n")
                sock.settimeout(2)
                data = sock.recv(1024).decode('utf-8', errors='ignore')
                sock.close()

                results.append(f"✓ {server}:{port} - Connected, received {len(data)} bytes")
                logger.info(f"Success: {server}:{port} - {data[:100]}")

            except socket.timeout:
                results.append(f"⏱️ {server}:{port} - Timeout (slow/blocked)")
                logger.warning(f"Timeout: {server}:{port}")
            except socket.gaierror:
                results.append(f"❌ {server}:{port} - DNS lookup failed")
                logger.warning(f"DNS failed: {server}:{port}")
            except ConnectionRefusedError:
                results.append(f"❌ {server}:{port} - Connection refused")
                logger.warning(f"Refused: {server}:{port}")
            except Exception as e:
                results.append(f"❌ {server}:{port} - {str(e)[:30]}")
                logger.warning(f"Error: {server}:{port} - {e}")

        # Show results
        if any("✓" in r for r in results):
            msg = "✓ RBN connection available:\n" + "\n".join(results)
        else:
            msg = "⚠️ All RBN servers unreachable. Use Test Data mode or check network:\n" + "\n".join(results)

        self.status_label.setText(msg)
        logger.info(f"RBN Test Results:\n{msg}")
        self.diag_btn.setEnabled(True)

    def _load_test_data(self) -> None:
        """Load test SKCC data and enable test spot generation"""
        try:
            self.test_btn.setEnabled(False)
            self.status_label.setText("Status: Loading test data...")

            success = self.spot_manager.db.skcc_members.load_test_data()
            roster_count = self.spot_manager.db.skcc_members.get_member_count()

            if success:
                # Enable test spot mode
                self.spot_manager.use_test_spots = True
                self.status_label.setText(f"✓ Test data & simulated spots enabled: {roster_count} test members")
                logger.warning(f"Test mode enabled: {roster_count} members, simulated spots will be generated")
                # Refresh award cache
                self._refresh_award_cache()
            else:
                self.status_label.setText("Error loading test data")

        except Exception as e:
            logger.error(f"Error loading test data: {e}", exc_info=True)
            self.status_label.setText(f"Error loading test data: {str(e)}")
        finally:
            self.test_btn.setEnabled(True)

    def _toggle_monitoring(self) -> None:
        """Toggle RBN monitoring on/off"""
        try:
            if self.spot_manager.is_running():
                self.spot_manager.stop()
                self.connect_btn.setText("Start Monitoring")
                self.status_label.setText("Status: Stopped")
            else:
                self.connect_btn.setEnabled(False)
                self.status_label.setText("Status: Starting... (check logs if stuck)")

                # Check roster
                roster_count = len(self.spot_manager.db.skcc_members.get_roster_dict())
                if roster_count == 0:
                    self.status_label.setText(
                        "⚠️  SKCC roster empty! Click 'Sync Roster' button first."
                    )
                    self.connect_btn.setEnabled(True)
                    logger.warning("Cannot start spotting - SKCC roster is empty")
                    return

                self.spot_manager.start()
                self.connect_btn.setText("Stop Monitoring")
                self.connect_btn.setEnabled(True)
                mode = "TEST SPOTS" if self.spot_manager.use_test_spots else "RBN"
                self.status_label.setText(f"Status: {mode} mode active (roster: {roster_count} members)")

        except Exception as e:
            logger.error(f"Error toggling monitoring: {e}", exc_info=True)
            self.status_label.setText(f"Error: {str(e)}")
            self.connect_btn.setEnabled(True)

    def _on_new_spot(self, spot: SKCCSpot) -> None:
        """Handle new spot received, filtering duplicates within 3-minute cooldown"""
        now = datetime.utcnow()
        callsign = spot.callsign.upper()

        # Check if this callsign was shown recently
        if callsign in self.last_shown_time:
            time_since_last = (now - self.last_shown_time[callsign]).total_seconds()
            if time_since_last < self.duplicate_cooldown_seconds:
                # Duplicate within cooldown period - skip it
                logger.debug(f"Skipping duplicate spot: {callsign} (shown {time_since_last:.0f}s ago)")
                return

        # Not a duplicate (or cooldown expired) - add the spot and update tracking
        self.last_shown_time[callsign] = now
        self.spots.insert(0, spot)

        # Keep only recent spots (last 500)
        if len(self.spots) > 500:
            self.spots = self.spots[:500]

        self._apply_filters()

    def _on_connection_state_changed(self, state: RBNConnectionState) -> None:
        """Handle RBN connection state change"""
        self.status_indicator.update_state(state)

        # Update status label with connection state
        state_messages = {
            RBNConnectionState.DISCONNECTED: "Status: Disconnected (click Start Monitoring)",
            RBNConnectionState.CONNECTING: "Status: Connecting to RBN... (may take 10-30 seconds)",
            RBNConnectionState.CONNECTED: "Status: Connected to RBN, listening for spots...",
            RBNConnectionState.ERROR: "Status: Connection error - check logs and try again",
        }
        self.status_label.setText(state_messages.get(state, f"Status: {state.value}"))
        logger.debug(f"RBN state changed: {state.value}")

    def _apply_filters(self) -> None:
        """Apply filters to spots list"""
        self.filtered_spots = self.spots.copy()

        # Band filter
        band = self.band_combo.currentText()
        if band != "All Bands":
            freq_range = self._get_band_freq_range(band)
            if freq_range:
                low, high = freq_range
                self.filtered_spots = [
                    s for s in self.filtered_spots
                    if low <= s.frequency <= high
                ]

        # Mode filter
        mode = self.mode_combo.currentText()
        if mode != "All Modes":
            self.filtered_spots = [
                s for s in self.filtered_spots
                if s.mode == mode
            ]

        # Strength filter
        min_strength = self.strength_spin.value()
        self.filtered_spots = [
            s for s in self.filtered_spots
            if s.strength >= min_strength
        ]

        # Unworked only
        if self.unworked_only_check.isChecked():
            worked = {c.callsign.upper() for c in self.spot_manager.db.get_all_contacts()}
            self.filtered_spots = [
                s for s in self.filtered_spots
                if s.callsign not in worked
            ]

        self._update_table()

    def _on_spot_selected(self) -> None:
        """Handle spot selection in table"""
        if self.spots_table.selectedIndexes():
            row = self.spots_table.selectedIndexes()[0].row()
            item = self.spots_table.item(row, 0)
            if item:
                spot = item.data(Qt.ItemDataRole.UserRole)
                if spot:
                    self.spot_selected.emit(spot.callsign, spot.frequency)

    def _refresh_spots(self) -> None:
        """Refresh spots display"""
        # Spots are auto-updated via callback, just update the table
        # This ensures age column is updated even without new spots
        self._apply_filters()

    def _cleanup_old_spots(self) -> None:
        """Clean up old spots from memory and database"""
        # Remove spots older than 1 hour from memory
        cutoff = datetime.utcnow() - timedelta(hours=1)
        self.spots = [s for s in self.spots if s.timestamp > cutoff]

        # Remove spots older than 24 hours from database
        self.spot_manager.cleanup_old_spots(hours=24)

        # Clean up old entries from duplicate tracking (older than 10 minutes)
        cutoff_tracking = datetime.utcnow() - timedelta(minutes=10)
        removed_count = 0
        callsigns_to_remove = [
            callsign for callsign, timestamp in self.last_shown_time.items()
            if timestamp < cutoff_tracking
        ]
        for callsign in callsigns_to_remove:
            del self.last_shown_time[callsign]
            removed_count += 1

        if removed_count > 0:
            logger.debug(f"Cleaned up {removed_count} old entries from duplicate tracking")

    @staticmethod
    def _get_band_freq_range(band: str) -> Optional[tuple]:
        """Get frequency range for band"""
        bands = {
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
        return bands.get(band)

    def _refresh_award_cache(self) -> None:
        """Refresh cached data for award-critical SKCC members"""
        try:
            # Get all SKCC contacts we've already worked
            contacts = self.spot_manager.db.get_all_contacts()
            self.worked_skcc_members = {
                c.skcc_number.upper() for c in contacts
                if c.skcc_number
            }

            # Get SKCC roster to identify members we haven't worked
            roster = self.spot_manager.db.skcc_members.get_roster_dict()

            # Get current SKCC award progress
            skcc_progress = self.spot_manager.db.get_award_progress("SKCC", "Members")

            # Determine how many unique SKCC members we need for our target award
            # SKCC levels: C=25, T=50, S=100, O=200, X=500, K=1000+
            target_count = self._get_target_skcc_count(skcc_progress)

            # If we need more members, identify which ones would help
            if target_count and len(self.worked_skcc_members) < target_count:
                # All unworked SKCC members are "award-critical"
                all_skcc_numbers = set(roster.keys()) if roster else set()
                self.award_critical_skcc_members = all_skcc_numbers - self.worked_skcc_members
            else:
                self.award_critical_skcc_members = set()

            logger.debug(
                f"Award cache updated: worked={len(self.worked_skcc_members)}, "
                f"critical={len(self.award_critical_skcc_members)}, "
                f"target={target_count}"
            )

        except Exception as e:
            logger.error(f"Error refreshing award cache: {e}")

    @staticmethod
    def _get_target_skcc_count(progress: Any) -> Optional[int]:
        """
        Get the target SKCC member count for current award level

        Args:
            progress: AwardProgress object

        Returns:
            Target member count or None
        """
        if not progress:
            return 25  # Default to first level (C = 25 members)

        # SKCC award levels
        levels = {
            "C": 25,
            "T": 50,
            "S": 100,
            "O": 200,
            "X": 500,
            "K": 1000,
        }

        # Get current level from progress
        current_level = getattr(progress, "achievement_level", None)
        if current_level and current_level in levels:
            return levels[current_level]

        # Default to next level up
        current_count = getattr(progress, "contact_count", 0) or 0
        for level, count in sorted(levels.items()):
            if current_count < count:
                return count

        return 1000  # If exceeds all known levels

    def _is_award_critical_spot(self, spot: SKCCSpot) -> bool:
        """
        Check if a spot is critical for unachieved awards

        Args:
            spot: The SKCC spot to check

        Returns:
            True if this spot would help toward an unachieved award
        """
        if not spot.is_skcc or not spot.skcc_number:
            return False

        # Check if already worked
        if spot.skcc_number.upper() in self.worked_skcc_members:
            return False

        # Check if needed for award
        return spot.skcc_number.upper() in self.award_critical_skcc_members

    def _update_table(self) -> None:
        """Update spots table with filtered spots"""
        self.spots_table.setRowCount(len(self.filtered_spots))
        self.spot_count_label.setText(f"Spots: {len(self.filtered_spots)}")

        for row, spot in enumerate(self.filtered_spots):
            row_data = SKCCSpotRow(spot)

            items = [
                QTableWidgetItem(row_data.callsign),
                QTableWidgetItem(row_data.frequency),
                QTableWidgetItem(row_data.mode),
                QTableWidgetItem(row_data.speed),
                QTableWidgetItem(row_data.reporter),
                QTableWidgetItem(row_data.time),
                QTableWidgetItem(row_data.get_age_string()),
            ]

            # Highlight award-critical spots in green
            is_award_critical = self._is_award_critical_spot(spot)
            if is_award_critical:
                for item in items:
                    item.setBackground(QColor("#90EE90"))  # Light green
                    item.setData(Qt.ItemDataRole.ToolTipRole, "Award-critical SKCC member")

            for col, item in enumerate(items):
                item.setData(Qt.ItemDataRole.UserRole, spot)
                self.spots_table.setItem(row, col, item)

    def closeEvent(self, event) -> None:
        """Clean up when widget is closed"""
        self.refresh_timer.stop()
        self.cleanup_timer.stop()
        self.award_cache_timer.stop()
        if self.spot_manager.is_running():
            self.spot_manager.stop()
        super().closeEvent(event)
