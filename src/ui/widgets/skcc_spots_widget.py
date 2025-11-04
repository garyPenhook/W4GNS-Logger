"""
SKCC Spots Widget - Display and manage SKCC member spots

Shows recent SKCC member spots from RBN with filtering and integration
with the logging form.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QHeaderView,
    QGroupBox,
    QGridLayout,
    QScrollArea,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
from PyQt6.QtGui import QColor, QFont

from src.skcc import SkccSkimmerSubprocess, SkimmerConnectionState, SKCCSpot
from src.config.settings import get_config_manager
from src.database.models import Contact

logger = logging.getLogger(__name__)


class SKCCSpotStatusIndicator(QLabel):
    """Status indicator for SKCC Skimmer connection"""

    def __init__(self):
        super().__init__()
        self.setFixedSize(16, 16)
        self.update_state(SkimmerConnectionState.DISCONNECTED)

    def update_state(self, state: SkimmerConnectionState) -> None:
        """Update indicator color based on connection state"""
        colors = {
            SkimmerConnectionState.DISCONNECTED: "#cccccc",
            SkimmerConnectionState.STARTING: "#ffff00",
            SkimmerConnectionState.RUNNING: "#00ff00",
            SkimmerConnectionState.ERROR: "#ff0000",
            SkimmerConnectionState.STOPPED: "#cccccc",
        }
        color = colors.get(state, "#cccccc")
        self.setStyleSheet(f"background-color: {color}; border-radius: 8px;")
        self.setToolTip(f"SKCC Skimmer Status: {state.value}")


class SKCCSpotRow:
    """Represents a row in the spots table"""

    def __init__(self, spot: SKCCSpot):
        self.spot = spot
        self.callsign = spot.callsign
        # Format frequency - if 0.0 (Sked entry), mark it
        self.frequency = "Sked" if spot.frequency == 0.0 else f"{spot.frequency:.3f}"
        self.mode = spot.mode
        self.speed = f"{spot.speed} WPM" if spot.speed else ""
        self.reporter = spot.reporter
        self.time = spot.timestamp.strftime("%H:%M:%S")
        self.age_seconds = (datetime.now(timezone.utc) - spot.timestamp).total_seconds()

    def get_age_string(self) -> str:
        """Get human-readable age string"""
        if self.age_seconds < 60:
            return f"{int(self.age_seconds)}s"
        elif self.age_seconds < 3600:
            return f"{int(self.age_seconds / 60)}m"
        else:
            return f"{int(self.age_seconds / 3600)}h"


class SKCCSpotWidget(QWidget):
    """Widget for displaying and managing SKCC spots from SKCC Skimmer"""

    # Signal when user clicks on a spot (to populate logging form)
    spot_selected = pyqtSignal(str, float)  # callsign, frequency

    # Signal for thread-safe RBN spot handling (emitted from background thread, handled in main thread)
    rbn_spot_received = pyqtSignal(object)  # RBNSpot object

    def __init__(self, db, parent: Optional[QWidget] = None):
        """
        Initialize SKCC spots widget

        Args:
            db: Database instance for querying worked callsigns
            parent: Parent widget
        """
        super().__init__(parent)
        self.db = db
        self.spots: List[SKCCSpot] = []
        self.filtered_spots: List[SKCCSpot] = []

        # RBN Fetcher for real-time CW spots from Telegraphy.de
        from src.rbn.rbn_fetcher import RBNFetcher

        self.rbn_fetcher = RBNFetcher()

        # Worked callsigns cache for "Unworked only" filter
        self._worked_callsigns_cache: set[str] = set()
        self._worked_cache_timestamp: Optional[datetime] = None
        self._worked_cache_ttl_seconds: int = 1800  # 30 minutes

        # SKCC roster cache for suffix filtering (C, T, S only)
        self._skcc_roster_cache: dict = {}
        self._skcc_roster_cache_timestamp: Optional[datetime] = None
        self._skcc_roster_cache_ttl_seconds: int = 1800  # 30 minutes

        # Load caches on startup (non-blocking)
        QTimer.singleShot(100, self._load_startup_caches)

        # Duplicate detection: track last time each callsign+frequency was shown (4-hour cooldown)
        self.last_shown_time: Dict[str, datetime] = {}
        self.duplicate_cooldown_seconds = 14400  # 4 hours

        self._is_shutting_down = False  # Flag to prevent new operations during shutdown

        # Config manager for persisting band selections
        self.config_manager = get_config_manager()

        # Debounce timer to throttle filter changes
        self._filter_debounce_timer = QTimer()
        self._filter_debounce_timer.setSingleShot(True)
        self._filter_debounce_timer.timeout.connect(self._apply_filters_debounced)
        self._filter_debounce_ms = 100  # Wait 100ms after last change before updating

        # Set up UI
        self._init_ui()
        self._load_band_selections()  # Load saved band selections

        # Auto-cleanup timer (runs periodically to clean up old spots)
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._cleanup_old_spots)
        self.cleanup_timer.start(30000)  # Cleanup every 30 seconds

        # Connect RBN spot signal for thread-safe UI updates (moved here for clarity)
        self.rbn_spot_received.connect(self._on_rbn_spot, Qt.ConnectionType.QueuedConnection)

        # Auto-start RBN monitoring after short delay (UI needs to be ready first)
        QTimer.singleShot(2000, self._auto_start_rbn_if_enabled)

    def _init_ui(self) -> None:
        """Initialize UI components"""
        layout = QVBoxLayout()

        # Header section
        header_layout = QHBoxLayout()

        # Status indicator
        self.status_indicator = SKCCSpotStatusIndicator()
        header_layout.addWidget(QLabel("SKCC Skimmer Status:"))
        header_layout.addWidget(self.status_indicator)

        # Sync roster button
        self.sync_btn = QPushButton("Sync Roster")
        self.sync_btn.clicked.connect(self._sync_roster)
        header_layout.addWidget(self.sync_btn)

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

        # Band filter with checkboxes (HF only, no VHF/UHF)
        band_group = QGroupBox("Bands")
        band_layout = QGridLayout()
        band_layout.setSpacing(3)
        band_layout.setContentsMargins(5, 5, 5, 5)
        self.band_checks: Dict[str, QCheckBox] = {}
        bands = ["160M", "80M", "60M", "40M", "30M", "20M", "17M", "15M", "12M", "10M", "6M"]
        for i, band in enumerate(bands):
            check = QCheckBox(band)
            check.setChecked(True)  # All bands selected by default
            check.stateChanged.connect(
                self._on_band_selection_changed
            )  # Save selections when changed
            self.band_checks[band] = check
            band_layout.addWidget(check, i // 3, i % 3)  # 3 columns
        band_group.setLayout(band_layout)
        filter_layout.addWidget(band_group)

        # Min signal strength
        filter_layout.addWidget(QLabel("Min Strength (dB):"))
        self.strength_spin = QSpinBox()
        self.strength_spin.setRange(0, 50)
        self.strength_spin.setValue(0)
        self.strength_spin.valueChanged.connect(self._on_filter_changed)  # Debounced
        filter_layout.addWidget(self.strength_spin)

        # Unworked only
        self.unworked_only_check = QCheckBox("Unworked Only")
        self.unworked_only_check.stateChanged.connect(self._on_filter_changed)  # Debounced
        filter_layout.addWidget(self.unworked_only_check)

        # SKCC Members Only
        self.skcc_only_check = QCheckBox("SKCC Members Only")
        self.skcc_only_check.setChecked(True)  # Default to showing only SKCC members
        self.skcc_only_check.stateChanged.connect(self._on_filter_changed)  # Debounced
        filter_layout.addWidget(self.skcc_only_check)

        # Continent filter
        filter_layout.addWidget(QLabel("Continent:"))
        self.continent_combo = QComboBox()
        self.continent_combo.addItems(
            [
                "All Continents",
                "North America",
                "South America",
                "Europe",
                "Asia",
                "Africa",
                "Oceania",
                "Antarctica",
            ]
        )
        self.continent_combo.setCurrentText("North America")  # Default to North America
        self.continent_combo.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.continent_combo)

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

        # Color-coded legend for spot highlighting
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("Highlight Colors:"))

        # Red - CRITICAL
        red_label = QLabel(" CRITICAL (1-5 needed for award) ")
        red_label.setStyleSheet(
            "background-color: rgba(255, 0, 0, 120); padding: 2px 5px; border-radius: 3px;"
        )
        legend_layout.addWidget(red_label)

        # Orange - HIGH
        orange_label = QLabel(" HIGH (6-20 needed) ")
        orange_label.setStyleSheet(
            "background-color: rgba(255, 100, 0, 100); padding: 2px 5px; border-radius: 3px;"
        )
        legend_layout.addWidget(orange_label)

        # Yellow - MEDIUM
        yellow_label = QLabel(" MEDIUM (21-50 needed) ")
        yellow_label.setStyleSheet(
            "background-color: rgba(255, 200, 0, 80); padding: 2px 5px; border-radius: 3px;"
        )
        legend_layout.addWidget(yellow_label)

        # Green - LOW
        green_label = QLabel(" LOW (already worked) ")
        green_label.setStyleSheet(
            "background-color: rgba(100, 200, 100, 60); padding: 2px 5px; border-radius: 3px;"
        )
        legend_layout.addWidget(green_label)

        # Info label
        info_label = QLabel(" Hover over highlighted spots for award details")
        info_label.setStyleSheet("font-style: italic; color: gray;")
        legend_layout.addWidget(info_label)

        legend_layout.addStretch()
        layout.addLayout(legend_layout)

        # Spots table
        self.spots_table = QTableWidget()
        self.spots_table.setColumnCount(8)
        self.spots_table.setHorizontalHeaderLabels(
            ["Callsign", "Frequency", "Mode", "Speed", "SKCC#", "Reporter", "Time", "Age"]
        )
        self.spots_table.itemSelectionChanged.connect(self._on_spot_selected)

        # Set column resize modes with optimized widths
        # Column 0: Callsign - fixed at 80px
        self.spots_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.spots_table.setColumnWidth(0, 80)

        # Column 1: Frequency - 50px for 3 decimal places (e.g., "21.051")
        self.spots_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.spots_table.setColumnWidth(1, 50)

        # Column 2: Mode - reduced by 50%
        self.spots_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.spots_table.setColumnWidth(2, 30)

        # Column 3: Speed - reduced by 50%
        self.spots_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self.spots_table.setColumnWidth(3, 50)

        # Column 4: SKCC# - fixed/compact
        self.spots_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        self.spots_table.setColumnWidth(4, 70)

        # Column 5: Reporter - reduced by 50%
        self.spots_table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.ResizeToContents
        )
        self.spots_table.setColumnWidth(5, 80)

        # Column 6: Time - reduced by 50% (85px → 42px)
        self.spots_table.horizontalHeader().setSectionResizeMode(
            6, QHeaderView.ResizeMode.ResizeToContents
        )
        self.spots_table.setColumnWidth(6, 42)

        # Column 7: Age - reduced by 50%
        self.spots_table.horizontalHeader().setSectionResizeMode(
            7, QHeaderView.ResizeMode.ResizeToContents
        )
        self.spots_table.setColumnWidth(7, 45)

        layout.addWidget(self.spots_table)

        self.setLayout(layout)

    def _load_startup_caches(self) -> None:
        """Load caches on startup to avoid queries during normal operation"""
        try:
            logger.info("Loading startup caches...")
            if self.db:
                # Pre-load worked callsigns and SKCC roster (with internal null checks)
                _ = self._get_worked_callsigns_cached()
                _ = self._get_skcc_roster_cached()
            else:
                logger.debug("No database instance provided; skipping startup cache preload")
            logger.info("Startup caches loaded successfully")
        except Exception as e:
            logger.error(f"Error loading startup caches: {e}", exc_info=True)

    def _load_band_selections(self) -> None:
        """Load saved band selections from config and apply them"""
        try:
            # Get saved band selections from config
            saved_bands_str = self.config_manager.get("dx_cluster.band_selections", "")
            if saved_bands_str and saved_bands_str.strip():  # Only if non-empty
                saved_bands = set(saved_bands_str.split(","))
                # Apply saved selections to checkboxes
                for band, check in self.band_checks.items():
                    check.setChecked(band in saved_bands)
                logger.debug(f"Loaded band selections from config: {saved_bands_str}")
            else:
                # Default: keep all bands checked (already set in _init_ui)
                logger.debug("No saved band selections - using all bands")
        except Exception as e:
            logger.warning(f"Error loading band selections: {e}")

    def _on_band_selection_changed(self) -> None:
        """Handle band selection change - save selections and reapply filters (debounced)"""
        try:
            # Get currently selected bands
            selected_bands = [band for band, check in self.band_checks.items() if check.isChecked()]
            # Save to config
            self.config_manager.set("dx_cluster.band_selections", ",".join(selected_bands))
            logger.debug(f"Saved band selections: {selected_bands}")
            # Reapply filters to update displayed spots (debounced to avoid excessive updates)
            self._on_filter_changed()
        except Exception as e:
            logger.error(f"Error saving band selections: {e}")

    def _on_filter_changed(self) -> None:
        """Debounce filter changes to prevent excessive table updates on main thread"""
        # Restart the debounce timer
        self._filter_debounce_timer.stop()
        self._filter_debounce_timer.start(self._filter_debounce_ms)  # Start with interval
        # Also call immediately as fallback (in case timer doesn't work)
        QTimer.singleShot(0, self._apply_filters)

    def _apply_filters_debounced(self) -> None:
        """Apply filters after debounce period (called from timer)"""
        self._apply_filters()

    def _sync_roster(self) -> None:
        """Sync SKCC membership roster - force fresh download in background thread"""
        try:
            self.sync_btn.setEnabled(False)
            self.status_label.setText(
                "Status: Clearing cache and downloading fresh roster... (may take 30 seconds)"
            )

            # Force fresh download by clearing cache first
            logger.info("Force-clearing SKCC roster cache for fresh download...")
            self.db.skcc_members.clear_cache()

            # Create background thread for roster download
            class RosterSyncThread(QThread):
                finished_signal = pyqtSignal(bool, int)  # success, member_count

                def __init__(self, db):
                    super().__init__()
                    self.db = db

                def run(self):
                    try:
                        success = self.db.skcc_members.sync_membership_data()
                        roster_count = self.db.skcc_members.get_member_count()
                        self.finished_signal.emit(success, roster_count)
                    except Exception as e:
                        logger.error(f"Roster sync thread error: {e}", exc_info=True)
                        self.finished_signal.emit(False, 0)

            def on_sync_complete(success: bool, roster_count: int):
                try:
                    if success and roster_count > 100:  # Real roster should have thousands
                        self.status_label.setText(
                            f"✓ SUCCESS: {roster_count} real SKCC members loaded! Click Start Monitoring for real spots."
                        )
                        logger.info(
                            f"Successfully downloaded real SKCC roster: {roster_count} members"
                        )
                    elif roster_count > 0:
                        self.status_label.setText(
                            f"⚠️  Roster has {roster_count} members (expected 1000+). Real roster download may have failed."
                        )
                        logger.warning(
                            f"Roster download returned {roster_count} members - may be test data or partial"
                        )
                    else:
                        self.status_label.setText(
                            "❌ Roster sync failed - check network connection."
                        )
                        logger.error("Roster sync failed - 0 members")
                except Exception as e:
                    logger.error(f"Error handling roster sync completion: {e}", exc_info=True)
                finally:
                    self.sync_btn.setEnabled(True)
                    if hasattr(self, "_roster_sync_thread"):
                        self._roster_sync_thread.deleteLater()
                        self._roster_sync_thread = None

            # Start background thread
            self._roster_sync_thread = RosterSyncThread(self.db)
            self._roster_sync_thread.finished_signal.connect(on_sync_complete)
            self._roster_sync_thread.start()

        except Exception as e:
            logger.error(f"Error starting roster sync: {e}", exc_info=True)
            self.status_label.setText(f"Error syncing roster: {str(e)}")
            self.sync_btn.setEnabled(True)

    def _toggle_monitoring(self) -> None:
        """Toggle RBN spot monitoring on/off"""
        try:
            if self.rbn_fetcher.is_running():
                self.rbn_fetcher.stop()
                self.connect_btn.setText("Start Monitoring")
                self.status_label.setText("Status: Stopped")
            else:
                self.connect_btn.setEnabled(False)
                self.status_label.setText("Status: Starting RBN...")

                # Get callsign from settings for callsign filtering
                my_callsign = self.config_manager.get("general.operator_callsign", "").upper()
                self.rbn_fetcher.my_callsign = (
                    my_callsign if my_callsign and my_callsign != "MYCALL" else None
                )

                # Set callbacks - use signal for thread-safe spot handling to main thread
                self.rbn_fetcher.set_callbacks(
                    on_spot=self.rbn_spot_received.emit,
                    on_state_change=self._on_rbn_state_changed,
                )

                # Start fetching
                success = self.rbn_fetcher.start()

                if success:
                    self.connect_btn.setText("Stop Monitoring")
                    self.connect_btn.setEnabled(True)
                    self.status_label.setText("Status: RBN active (fetching CW spots)")
                else:
                    logger.error("Failed to start RBN fetcher")
                    self.connect_btn.setText("Start Monitoring")
                    self.connect_btn.setEnabled(True)
                    self.status_label.setText("Status: Failed to start RBN fetcher")

        except Exception as e:
            logger.error(f"Error toggling monitoring: {e}", exc_info=True)
            self.status_label.setText(f"Error: {str(e)}")
            self.connect_btn.setEnabled(True)

    def _auto_start_rbn_if_enabled(self) -> None:
        """Auto-start RBN monitoring if configured to do so"""
        try:
            auto_start = self.config_manager.get("skcc.auto_start_spots", True)
            if auto_start and not self.rbn_fetcher.is_running():
                logger.info("Auto-starting RBN monitoring...")
                self._toggle_monitoring()
        except Exception as e:
            logger.warning(f"Error in auto-start RBN: {e}")

    def _handle_skimmer_spot(self, spot: SKCCSpot) -> None:
        """
        Handle new spot from SKCC Skimmer

        Checks for duplicates and adds spot to display list.
        """
        try:
            now = datetime.now(timezone.utc)
            callsign = spot.callsign.upper()
            spot_key = f"{callsign}_{spot.frequency:.3f}"

            # Check if this callsign on this frequency was shown recently
            if spot_key in self.last_shown_time:
                time_since_last = (now - self.last_shown_time[spot_key]).total_seconds()
                if time_since_last < self.duplicate_cooldown_seconds:
                    logger.debug(
                        f"Skipping duplicate spot: {callsign} on {spot.frequency:.3f} MHz (shown {time_since_last:.0f}s ago)"
                    )
                    return

            # Add to display list and update tracking
            self.last_shown_time[spot_key] = now
            self.spots.insert(0, spot)
            logger.debug(f"[UI] Added spot: {spot.callsign} - Total spots: {len(self.spots)}")

            # Keep only recent spots in memory
            if len(self.spots) > 200:
                self.spots = self.spots[:200]

            # Update the display
            logger.debug(f"[UI] Calling _on_filter_changed")
            self._on_filter_changed()

        except Exception as e:
            logger.error(f"Error handling spot {spot.callsign}: {e}", exc_info=True)

    def _on_rbn_spot_from_thread(self, rbn_spot) -> None:
        """Handle RBN spot from background thread - marshals to main thread"""
        if not rbn_spot:
            return

        # Use QTimer to marshal this call to the main thread
        # This ensures thread safety without needing signals
        QTimer.singleShot(0, lambda s=rbn_spot: self._on_rbn_spot(s))

    def _on_rbn_spot(self, rbn_spot) -> None:
        """Handle RBN spot from Telegraphy.de API (called in main thread via signal)"""
        if not rbn_spot:
            return

        print(f"*** SIGNAL RECEIVED: {rbn_spot.callsign} ***")  # Immediate stdout
        logger.info(f"*** SIGNAL RECEIVED: {rbn_spot.callsign} ***")  # Also log

        try:
            # Convert RBN spot to SKCCSpot format
            from src.skcc.skcc_skimmer_subprocess import SKCCSpot

            # Normalize frequency to MHz (RBN telegraphy sends kHz like 14042.0)
            freq_mhz = rbn_spot.frequency or 0.0
            if freq_mhz and freq_mhz > 1000:
                freq_mhz = round(freq_mhz / 1000.0, 3)

            # Look up SKCC number from roster
            skcc_number = None
            is_skcc_member = False
            skcc_roster = self._get_skcc_roster_cached()
            if skcc_roster:
                callsign_upper = rbn_spot.callsign.upper()
                member_info = skcc_roster.get(callsign_upper)
                if member_info:
                    is_skcc_member = True
                    # Extract SKCC number from member info
                    if isinstance(member_info, dict):
                        skcc_number = member_info.get("skcc_number")
                    else:
                        skcc_number = member_info

            spot = SKCCSpot(
                callsign=rbn_spot.callsign,
                frequency=freq_mhz,
                mode=rbn_spot.mode,
                grid=rbn_spot.grid,
                reporter=rbn_spot.reporter,
                strength=rbn_spot.strength,
                speed=rbn_spot.speed,
                timestamp=rbn_spot.timestamp,
                is_skcc=is_skcc_member,
                skcc_number=str(skcc_number) if skcc_number else None,
            )

            logger.debug(
                f"[UI] Processing RBN spot: {spot.callsign} {spot.frequency}M SKCC#{skcc_number or 'N/A'}"
            )
            self._handle_skimmer_spot(spot)

        except Exception as e:
            logger.error(f"Error handling RBN spot: {e}", exc_info=True)

    def _on_rbn_state_changed(self, state) -> None:
        """Handle RBN connection state changes"""
        logger.info(f"RBN state: {state.value}")

        if "running" in state.value:
            self.status_label.setText("Status: RBN active (fetching CW spots)")
        elif "connecting" in state.value:
            self.status_label.setText("Status: Connecting to RBN...")
        elif "error" in state.value:
            self.status_label.setText("Status: RBN error")
        elif "stopped" in state.value:
            self.status_label.setText("Status: Stopped")

    def _is_valid_skcc_suffix(self, callsign: str, skcc_roster: dict) -> bool:
        """
        Check if a callsign has valid SKCC suffix (C, T, or S).
        Looks up the SKCC number from the roster.

        Args:
            callsign: The callsign to check
            skcc_roster: Dictionary mapping callsign to SKCC member info

        Returns:
            True if callsign has SKCC number ending with C, T, or S, False otherwise
        """
        try:
            if not skcc_roster:
                return False

            callsign_upper = callsign.upper()
            member_info = skcc_roster.get(callsign_upper)

            if not member_info:
                return False

            # member_info is typically a dict with 'skcc_number' key
            skcc_number = (
                member_info.get("skcc_number") if isinstance(member_info, dict) else member_info
            )

            if not skcc_number:
                return False

            # Ensure skcc_number is a string before checking suffix
            skcc_str = str(skcc_number).strip()
            if len(skcc_str) == 0:
                return False

            return skcc_str[-1] in ("C", "T", "S")
        except Exception as e:
            logger.debug(f"Error checking SKCC suffix for {callsign}: {e}")
            return False

    def _get_worked_callsigns_cached(self) -> set[str]:
        """Return worked callsigns with a 30-minute TTL to reduce DB queries."""
        if not self.db:
            return set()  # No database, return empty set

        now = datetime.now(timezone.utc)
        if (
            self._worked_cache_timestamp is None
            or (now - self._worked_cache_timestamp).total_seconds() > self._worked_cache_ttl_seconds
        ):
            try:
                # Use efficient query - callsigns only, not full Contact objects
                session = self.db.get_session()
                try:
                    worked_callsigns_result = session.query(Contact.callsign).distinct().all()
                    self._worked_callsigns_cache = {
                        c[0].upper() for c in worked_callsigns_result if c[0]
                    }
                    self._worked_cache_timestamp = now
                finally:
                    session.close()
            except Exception as e:
                logger.debug(f"Error refreshing worked callsigns cache: {e}")
                # On error, return existing cache (may be empty)
        return self._worked_callsigns_cache

    def _get_skcc_roster_cached(self) -> dict:
        """
        Return SKCC roster with a 30-minute TTL to reduce DB queries.

        Critical: This prevents thread safety issues from calling get_roster_dict()
        on every filter operation during high-volume spot processing.

        Returns:
            Dictionary mapping callsigns to SKCC member info
        """
        if not self.db:
            return {}  # No database, return empty dict

        now = datetime.now(timezone.utc)
        if (
            self._skcc_roster_cache_timestamp is None
            or (now - self._skcc_roster_cache_timestamp).total_seconds()
            > self._skcc_roster_cache_ttl_seconds
        ):
            try:
                # Cache the entire roster once per 30 minutes
                self._skcc_roster_cache = self.db.skcc_members.get_roster_dict()
                if not isinstance(self._skcc_roster_cache, dict):
                    self._skcc_roster_cache = {}
                self._skcc_roster_cache_timestamp = now
            except Exception as e:
                logger.debug(f"Error refreshing SKCC roster cache: {e}")
                # On error, return existing cache (may be empty)
                if not isinstance(self._skcc_roster_cache, dict):
                    self._skcc_roster_cache = {}
        return self._skcc_roster_cache

    @staticmethod
    def _get_continent_from_callsign(callsign: str) -> str:
        """Determine continent from amateur radio callsign prefix.

        Returns: One of 'North America', 'South America', 'Europe', 'Asia', 'Africa', 'Oceania', 'Antarctica', or 'Unknown'
        """
        if not callsign:
            return "Unknown"

        # Extract prefix (everything before first digit)
        prefix = ""
        for char in callsign.upper():
            if char.isdigit():
                break
            if char.isalpha():
                prefix += char

        if not prefix:
            return "Unknown"

        # North America (W, K, N, VE, VA, VO, XE, etc.)
        if (
            prefix in ["W", "K", "N", "A"]
            or prefix.startswith("V")
            and len(callsign) > 2
            and callsign[1] in ["E", "A", "O", "Y"]
        ):
            return "North America"
        if prefix in ["XE", "XF"]:  # Mexico
            return "North America"
        if (
            prefix.startswith("C") and len(callsign) > 2 and callsign[1] in ["M", "O"]
        ):  # Cuba, various Caribbean
            return "North America"
        if prefix in ["KP", "KL", "WP", "NH", "NP"]:  # US territories
            return "North America"
        if prefix in ["TI", "YN", "HP", "HI", "YV", "HH"]:  # Central America/Caribbean
            return "North America"

        # South America
        if prefix in ["PY", "PT", "PP", "PR", "PS", "PU", "PV", "PW", "PX"]:  # Brazil
            return "South America"
        if prefix in ["LU", "AY", "AZ", "L"]:  # Argentina
            return "South America"
        if prefix in ["CE", "CA", "CB", "CC", "CD", "XQ", "XR"]:  # Chile
            return "South America"
        if prefix in ["CP", "CX", "CV", "HC", "HK", "OA", "YV", "ZP"]:  # Various SA countries
            return "South America"

        # Europe
        if prefix in ["G", "M", "GW", "GI", "GD", "GJ", "GM", "GU", "GB"]:  # UK
            return "Europe"
        if prefix in ["F", "TM", "TO", "TP", "TQ", "TV"]:  # France
            return "Europe"
        if prefix in [
            "D",
            "DA",
            "DB",
            "DC",
            "DD",
            "DE",
            "DF",
            "DG",
            "DH",
            "DI",
            "DJ",
            "DK",
            "DL",
            "DM",
            "DN",
            "DO",
        ]:  # Germany
            return "Europe"
        if prefix in ["I", "IK", "IW", "IZ", "IT"]:  # Italy
            return "Europe"
        if prefix in ["EA", "EB", "EC", "ED", "EE", "EF", "EG", "EH", "AM"]:  # Spain
            return "Europe"
        if prefix in ["PA", "PB", "PC", "PD", "PE", "PF", "PG", "PH", "PI"]:  # Netherlands
            return "Europe"
        if prefix in ["OH", "OF", "OG", "OI", "OJ"]:  # Finland
            return "Europe"
        if prefix in [
            "SM",
            "SA",
            "SB",
            "SC",
            "SD",
            "SE",
            "SF",
            "SG",
            "SH",
            "SI",
            "SJ",
            "SK",
            "SL",
        ]:  # Sweden
            return "Europe"
        if prefix in [
            "LA",
            "LB",
            "LC",
            "LD",
            "LE",
            "LF",
            "LG",
            "LH",
            "LI",
            "LJ",
            "LK",
            "LL",
            "LM",
            "LN",
        ]:  # Norway
            return "Europe"
        if prefix in ["ON", "OO", "OP", "OQ", "OR", "OS", "OT"]:  # Belgium
            return "Europe"
        if prefix in ["OZ", "OU", "OV", "OW"]:  # Denmark
            return "Europe"
        if prefix in ["SP", "SN", "SO", "SQ", "SR"]:  # Poland
            return "Europe"
        if prefix in ["OK", "OL"]:  # Czech Republic
            return "Europe"
        if prefix in ["HA", "HG"]:  # Hungary
            return "Europe"
        if prefix in ["YO", "YP", "YQ", "YR"]:  # Romania
            return "Europe"
        if prefix in ["YU", "YT", "YZ"]:  # Serbia/Yugoslavia
            return "Europe"
        if prefix in [
            "LY",
            "LZ",
            "SV",
            "SW",
            "SX",
            "SY",
            "SZ",
            "OM",
            "S5",
            "S50",
            "S51",
            "S52",
            "S53",
            "S54",
            "S55",
            "S56",
            "S57",
            "S58",
            "S59",
        ]:
            return "Europe"
        if prefix in ["EI", "EJ"]:  # Ireland
            return "Europe"
        if prefix in ["CT", "CR", "CS", "CU"]:  # Portugal
            return "Europe"
        if prefix in ["HB", "HE"]:  # Switzerland
            return "Europe"
        if prefix in ["OE"]:  # Austria
            return "Europe"
        if prefix in ["LX"]:  # Luxembourg
            return "Europe"
        if prefix.startswith("R") or prefix.startswith("U"):  # Russia/Ukraine
            return "Europe"  # Western Russia/Ukraine considered Europe for amateur radio
        if prefix in ["ER", "ES", "LY"]:  # Moldova, Estonia, Lithuania
            return "Europe"
        if prefix in ["YL"]:  # Latvia
            return "Europe"
        if prefix in ["9A"]:  # Croatia
            return "Europe"
        if prefix in ["9H"]:  # Malta
            return "Europe"
        if prefix in ["T9"]:  # Bosnia
            return "Europe"

        # Asia
        if prefix in [
            "JA",
            "JE",
            "JF",
            "JG",
            "JH",
            "JI",
            "JJ",
            "JK",
            "JL",
            "JM",
            "JN",
            "JO",
            "JP",
            "JQ",
            "JR",
        ]:  # Japan
            return "Asia"
        if prefix in [
            "B",
            "BA",
            "BD",
            "BG",
            "BH",
            "BI",
            "BJ",
            "BL",
            "BM",
            "BT",
            "BY",
            "BZ",
        ]:  # China
            return "Asia"
        if prefix in ["HL", "HM", "DS", "DT", "D7", "D8", "D9"]:  # South Korea
            return "Asia"
        if prefix in ["VU", "AT", "AU", "AV", "AW", "8T", "8U", "8V", "8W", "8X", "8Y"]:  # India
            return "Asia"
        if prefix in ["HS", "E2"]:  # Thailand
            return "Asia"
        if prefix in [
            "YB",
            "YC",
            "YD",
            "YE",
            "YF",
            "YG",
            "YH",
            "7A",
            "7B",
            "7C",
            "7D",
            "7E",
            "7F",
            "7G",
            "7H",
            "7I",
        ]:  # Indonesia
            return "Asia"
        if prefix in ["9M", "9W"]:  # Malaysia
            return "Asia"
        if prefix in ["9V"]:  # Singapore
            return "Asia"
        if prefix in [
            "DU",
            "DV",
            "DW",
            "DX",
            "DY",
            "DZ",
            "4D",
            "4E",
            "4F",
            "4G",
            "4H",
            "4I",
        ]:  # Philippines
            return "Asia"
        if prefix in ["XU"]:  # Cambodia
            return "Asia"
        if prefix in ["E5"]:  # Cook Islands (Oceania, but sometimes grouped with Asia)
            return "Oceania"
        if prefix in ["BV", "BW", "BX", "BU"]:  # Taiwan
            return "Asia"
        if prefix in ["VR", "VS", "XX"]:  # Hong Kong
            return "Asia"
        if prefix in ["A4"]:  # Oman
            return "Asia"
        if prefix in ["A6", "A7", "A9"]:  # UAE, Qatar, Bahrain
            return "Asia"

        # Africa
        if prefix in ["5Z", "5Y"]:  # Kenya
            return "Africa"
        if prefix in ["CN", "5C", "5D", "5E", "5F", "5G"]:  # Morocco
            return "Africa"
        if prefix in ["5H", "5I"]:  # Tanzania
            return "Africa"
        if prefix in ["5N", "5O"]:  # Nigeria
            return "Africa"
        if prefix in ["5R", "5S"]:  # Madagascar
            return "Africa"
        if prefix in ["5T"]:  # Mauritania
            return "Africa"
        if prefix in ["5U"]:  # Niger
            return "Africa"
        if prefix in ["5V"]:  # Togo
            return "Africa"
        if prefix in ["5W"]:  # Western Samoa (actually Oceania)
            return "Oceania"
        if prefix in ["5X"]:  # Uganda
            return "Africa"
        if prefix in ["6V", "6W"]:  # Senegal
            return "Africa"
        if prefix in ["7Q", "7P"]:  # Malawi
            return "Africa"
        if prefix in ["9G"]:  # Ghana
            return "Africa"
        if prefix in ["9J"]:  # Zambia
            return "Africa"
        if prefix in ["9L"]:  # Sierra Leone
            return "Africa"
        if prefix in ["9Q"]:  # DR Congo
            return "Africa"
        if prefix in ["9U"]:  # Burundi
            return "Africa"
        if prefix in ["9X"]:  # Rwanda
            return "Africa"
        if prefix in ["ZS", "ZR", "ZT", "ZU"]:  # South Africa
            return "Africa"
        if prefix in ["D2", "D3", "D4"]:  # Angola
            return "Africa"
        if prefix in ["ET", "E3"]:  # Ethiopia
            return "Africa"
        if prefix in ["ST", "SU", "SS", "6A", "6B"]:  # Sudan
            return "Africa"
        if prefix in ["EL"]:  # Liberia
            return "Africa"
        if prefix in ["C5"]:  # The Gambia
            return "Africa"
        if prefix in ["C9", "CR", "D2"]:  # Mozambique
            return "Africa"
        if prefix in ["TU"]:  # Ivory Coast
            return "Africa"
        if prefix in ["TY", "TZ"]:  # Benin
            return "Africa"
        if prefix in ["XT"]:  # Burkina Faso
            return "Africa"
        if prefix in ["TT"]:  # Chad
            return "Africa"
        if prefix in ["TR"]:  # Gabon
            return "Africa"
        if prefix in ["TJ"]:  # Cameroon
            return "Africa"
        if prefix in ["TL"]:  # Central African Republic
            return "Africa"
        if prefix in ["TN"]:  # Congo
            return "Africa"
        if prefix in ["A2"]:  # Botswana
            return "Africa"
        if prefix in ["V5"]:  # Namibia
            return "Africa"
        if prefix in ["Z2", "Z8"]:  # Zimbabwe
            return "Africa"
        if prefix in ["3V", "3X"]:  # Tunisia
            return "Africa"
        if prefix in ["3C", "7O", "7P"]:  # Equatorial Guinea
            return "Africa"
        if prefix in ["3DA"]:  # Swaziland
            return "Africa"

        # Oceania
        if prefix in [
            "VK",
            "VI",
            "VJ",
            "VL",
            "VM",
            "VN",
            "VO",
            "VP",
            "VQ",
            "VR",
            "VZ",
            "AX",
        ]:  # Australia
            return "Oceania"
        if prefix in ["ZL", "ZK", "ZM"]:  # New Zealand
            return "Oceania"
        if prefix in ["DU", "KH"]:  # Some Pacific islands
            return "Oceania"
        if prefix in ["T2", "T3"]:  # Tuvalu, Kiribati
            return "Oceania"
        if prefix in ["YJ"]:  # Vanuatu
            return "Oceania"
        if prefix in ["3D2"]:  # Fiji
            return "Oceania"
        if prefix in ["FO", "FW"]:  # French Polynesia
            return "Oceania"
        if prefix in ["H4"]:  # Solomon Islands
            return "Oceania"
        if prefix in ["P2"]:  # Papua New Guinea
            return "Oceania"
        if prefix in ["T8"]:  # Palau
            return "Oceania"
        if prefix in ["V6"]:  # Micronesia
            return "Oceania"
        if prefix in ["V7"]:  # Marshall Islands
            return "Oceania"
        if prefix in ["V8"]:  # Brunei (Asia, but sometimes grouped)
            return "Asia"

        # Antarctica
        if prefix in ["KC4", "CE9", "VP8", "R1AN", "DP0", "DP1", "3Y"]:  # Antarctic stations
            return "Antarctica"

        return "Unknown"

    def _apply_filters(self) -> None:
        """Apply filters to spots list (optimized for performance)"""
        # Start with all spots
        filtered_spots = self.spots

        # Build band frequency ranges once
        selected_bands = [band for band, check in self.band_checks.items() if check.isChecked()]
        band_ranges = {}
        if selected_bands:
            for band in selected_bands:
                freq_range = self._get_band_freq_range(band)
                if freq_range:
                    band_ranges[band] = freq_range

        # Apply filters
        min_strength = self.strength_spin.value()
        check_unworked = self.unworked_only_check.isChecked()
        check_skcc_only = self.skcc_only_check.isChecked()
        worked_callsigns = self._get_worked_callsigns_cached() if check_unworked else set()

        # Get SKCC roster for suffix filtering
        skcc_roster = self._get_skcc_roster_cached()

        # Continent filtering
        selected_continent = self.continent_combo.currentText()

        # Single-pass filtering
        self.filtered_spots = []
        for s in filtered_spots:
            # Skip if SKCC-only is checked and this spot has no SKCC number
            if check_skcc_only and not s.skcc_number:
                logger.debug(f"[FILTER] Skipping {s.callsign} - not a SKCC member")
                continue

            # Skip if unworked-only is checked and this is already worked
            if check_unworked and s.callsign in worked_callsigns:
                logger.debug(f"[FILTER] Skipping {s.callsign} - already worked")
                continue

            # Skip if below minimum signal strength
            if s.strength > 0 and s.strength < min_strength:
                logger.debug(
                    f"[FILTER] Skipping {s.callsign} - strength {s.strength} < {min_strength}"
                )
                continue

            # Skip if band filter is active and frequency is outside selected bands
            # (only apply band filter if frequency is valid, i.e., not 0.0)
            if selected_bands and s.frequency > 0:
                if not any(low <= s.frequency <= high for low, high in band_ranges.values()):
                    logger.debug(
                        f"[FILTER] Skipping {s.callsign} {s.frequency}M - not in selected bands {selected_bands}"
                    )
                    continue

            # Skip if continent filter is active and continent doesn't match
            if selected_continent != "All Continents":
                continent = self._get_continent_from_callsign(s.callsign)
                if continent != selected_continent:
                    logger.debug(
                        f"[FILTER] Skipping {s.callsign} {s.frequency}M - continent {continent} != {selected_continent}"
                    )
                    continue

            # Accept the spot
            logger.debug(f"[FILTER] Accepting {s.callsign} {s.frequency}M dB={s.strength}")
            self.filtered_spots.append(s)

        logger.info(
            f"[FILTER] Filtered {len(self.filtered_spots)} spots from {len(filtered_spots)} total (bands: {selected_bands}, min_dB={min_strength}, unworked_only={check_unworked}, skcc_only={check_skcc_only}, continent={selected_continent})"
        )
        self._update_table()

    def _update_table(self) -> None:
        """Update spots table with filtered spots"""
        self.spots_table.setUpdatesEnabled(False)
        try:
            self.spots_table.setRowCount(len(self.filtered_spots))
            self.spot_count_label.setText(f"Spots: {len(self.filtered_spots)}")
            logger.info(f"[TABLE] Row count set to {len(self.filtered_spots)}")

            for row, spot in enumerate(self.filtered_spots):
                row_data = SKCCSpotRow(spot)

                # Build SKCC number string
                skcc_str = spot.skcc_number if spot.skcc_number else ""

                # Format frequency - if 0.0 (Sked entry), show "Sked" instead
                freq_str = "Sked" if spot.frequency == 0.0 else row_data.frequency

                items = [
                    QTableWidgetItem(row_data.callsign),
                    QTableWidgetItem(freq_str),
                    QTableWidgetItem(row_data.mode),
                    QTableWidgetItem(row_data.speed),
                    QTableWidgetItem(skcc_str),
                    QTableWidgetItem(row_data.reporter),
                    QTableWidgetItem(row_data.time),
                    QTableWidgetItem(row_data.get_age_string()),
                ]

                for col, item in enumerate(items):
                    item.setData(Qt.ItemDataRole.UserRole, spot)
                    self.spots_table.setItem(row, col, item)
            if self.filtered_spots:
                top = self.filtered_spots[0]
                logger.info(
                    f"[TABLE] Top row: {top.callsign} {top.frequency:.3f}M dB={top.strength} reporter={top.reporter}"
                )
        finally:
            self.spots_table.setUpdatesEnabled(True)

    def _on_skimmer_spot_line(self, line: str) -> None:
        """Handle SKCC Skimmer console output line"""
        try:
            logger.info(f"[PARSING SPOT] {line}")

            import re

            # Extract callsign
            callsign_match = re.search(r"\s([A-Z0-9]{2,})\s", line)
            if not callsign_match:
                logger.debug(f"  ✗ No callsign found in: {line}")
                return
            callsign = callsign_match.group(1).upper()
            logger.debug(f"  ✓ Callsign: {callsign}")

            # Extract SKCC number if present
            skcc_match = re.search(r"\((\d+[A-Z]*)\)", line)
            skcc_number = skcc_match.group(1) if skcc_match else None
            logger.debug(f"  ✓ SKCC#: {skcc_number if skcc_number else 'None'}")

            # Extract frequency (may not exist in Sked format)
            freq_match = re.search(r"(\d+[.,]?\d*)\s*(kHz|MHz)", line)
            if freq_match:
                freq_str = freq_match.group(1).replace(",", ".")
                freq_mhz = float(freq_str)
                if "kHz" in freq_match.group(2):
                    freq_mhz = freq_mhz / 1000
            else:
                # Sked format entries don't have frequency - use placeholder
                freq_mhz = 0.0
            logger.debug(f"  ✓ Frequency: {freq_mhz if freq_mhz else 'N/A'} MHz")

            # Extract mode (RBN spots have this, Sked entries don't)
            mode_match = re.search(r"\b(CW|SSB|LSB|USB|FM|RTTY|FT8|FT4)\b", line, re.IGNORECASE)
            mode = mode_match.group(1).upper() if mode_match else "CW"
            logger.debug(f"  ✓ Mode: {mode}")

            # Extract signal strength (RBN spots have this)
            signal_match = re.search(r"(\d+)\s*dB", line)
            strength = int(signal_match.group(1)) if signal_match else 0
            logger.debug(f"  ✓ Signal: {strength if strength else 'N/A'} dB")

            # Extract speed (WPM) for CW
            speed_match = re.search(r"(\d+)\s*WPM", line)
            speed = int(speed_match.group(1)) if speed_match else None
            logger.debug(f"  ✓ Speed: {speed if speed else 'None'} WPM")

            # Skip if no frequency AND no SKCC number (not a valid spot)
            if freq_mhz == 0.0 and not skcc_number:
                logger.debug(f"  ✗ Skipping: no frequency and no SKCC number")
                return

            # Create SKCCSpot object
            spot = SKCCSpot(
                callsign=callsign,
                frequency=freq_mhz,
                mode=mode,
                grid=None,
                reporter="SKCC_Skimmer",
                strength=strength,
                speed=speed if mode == "CW" else None,
                timestamp=datetime.now(timezone.utc),
                is_skcc=True,
                skcc_number=skcc_number,
            )

            logger.info(f"  ✅ SPOT CREATED: {callsign} on {freq_mhz if freq_mhz else 'Sked'}")
            self._handle_skimmer_spot(spot)

        except Exception as e:
            logger.error(f"Error parsing SKCC Skimmer spot line '{line}': {e}", exc_info=True)

    def _on_skimmer_state_changed(self, state: SkimmerConnectionState) -> None:
        """Handle SKCC Skimmer state changes"""
        state_str = state.value.upper() if state else "UNKNOWN"
        logger.info(f"SKCC Skimmer state changed: {state_str}")

        if state == SkimmerConnectionState.DISCONNECTED:
            self.status_label.setText(f"Status: SKCC Skimmer disconnected")
        elif state == SkimmerConnectionState.STARTING:
            self.status_label.setText(f"Status: SKCC Skimmer starting...")
        elif state == SkimmerConnectionState.RUNNING:
            self.status_label.setText(f"Status: SKCC Skimmer active (filtering spots)")
        elif state == SkimmerConnectionState.ERROR:
            self.status_label.setText(f"Status: SKCC Skimmer error - check configuration")
        elif state == SkimmerConnectionState.STOPPED:
            self.status_label.setText(f"Status: Stopped")

    def closeEvent(self, event) -> None:
        """Clean up when widget is closed"""
        self._is_shutting_down = True

        try:
            self.cleanup_timer.stop()
            self._filter_debounce_timer.stop()

            # Stop SKCC Skimmer subprocess if running
            if hasattr(self, "skcc_skimmer") and self.skcc_skimmer:
                if self.skcc_skimmer.is_running():
                    logger.info("Stopping SKCC Skimmer subprocess...")
                    self.skcc_skimmer.stop()

        except Exception as e:
            logger.error(f"Error cleaning up spots widget: {e}", exc_info=True)
        super().closeEvent(event)

    def _refresh_spots(self) -> None:
        """Refresh spots display immediately (updates age and applies filters)."""
        try:
            self._apply_filters()
        except Exception as e:
            logger.error(f"Error refreshing spots: {e}", exc_info=True)

    def _on_spot_selected(self) -> None:
        """Handle spot selection in the table and emit spot_selected."""
        try:
            indexes = self.spots_table.selectedIndexes()
            if not indexes:
                return
            row = indexes[0].row()
            item = self.spots_table.item(row, 0)
            if not item:
                return
            spot = item.data(Qt.ItemDataRole.UserRole)
            if not spot:
                return
            # Emit callsign and frequency to populate logging form
            self.spot_selected.emit(spot.callsign, spot.frequency)
        except Exception as e:
            logger.error(f"Error handling spot selection: {e}", exc_info=True)

    def _cleanup_old_spots(self) -> None:
        """Periodic cleanup to remove old spots and shrink duplicate tracking."""
        try:
            # Remove spots older than 10 minutes
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
            before = len(self.spots)
            self.spots = [s for s in self.spots if s.timestamp > cutoff]
            removed = before - len(self.spots)
            if removed > 0:
                logger.info(f"[CLEANUP] Removed {removed} old spots (>{10} minutes)")

            # Trim duplicate tracking older than 2 minutes
            dup_cutoff = datetime.now(timezone.utc) - timedelta(minutes=2)
            to_delete = [k for k, t in self.last_shown_time.items() if t < dup_cutoff]
            for k in to_delete:
                self.last_shown_time.pop(k, None)
            if to_delete:
                logger.debug(f"[CLEANUP] Cleared {len(to_delete)} entries from duplicate tracking")
        except Exception as e:
            logger.error(f"Error in cleanup: {e}", exc_info=True)

    @staticmethod
    def _get_band_freq_range(band: str) -> Optional[tuple[float, float]]:
        """Return (low, high) MHz range for a given amateur HF band."""
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
        }
        return bands.get(band)
