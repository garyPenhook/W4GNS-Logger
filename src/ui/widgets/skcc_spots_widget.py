"""
SKCC Spots Widget - Display and manage SKCC member spots

Shows recent SKCC member spots from RBN with filtering and integration
with the logging form.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QComboBox, QCheckBox, QSpinBox, QHeaderView,
    QGroupBox, QGridLayout, QScrollArea
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
        self.frequency = f"{spot.frequency:.3f}"  # 3 decimal places for accurate frequency display
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

        # SKCC Skimmer subprocess for intelligent filtering
        config_manager = get_config_manager()
        adif_file = config_manager.get("skcc.adif_master_file", "")
        self.skcc_skimmer = SkccSkimmerSubprocess(adif_file=adif_file if adif_file else None)

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
            check.stateChanged.connect(self._on_band_selection_changed)  # Save selections when changed
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
        red_label.setStyleSheet("background-color: rgba(255, 0, 0, 120); padding: 2px 5px; border-radius: 3px;")
        legend_layout.addWidget(red_label)
        
        # Orange - HIGH
        orange_label = QLabel(" HIGH (6-20 needed) ")
        orange_label.setStyleSheet("background-color: rgba(255, 100, 0, 100); padding: 2px 5px; border-radius: 3px;")
        legend_layout.addWidget(orange_label)
        
        # Yellow - MEDIUM
        yellow_label = QLabel(" MEDIUM (21-50 needed) ")
        yellow_label.setStyleSheet("background-color: rgba(255, 200, 0, 80); padding: 2px 5px; border-radius: 3px;")
        legend_layout.addWidget(yellow_label)
        
        # Green - LOW
        green_label = QLabel(" LOW (already worked) ")
        green_label.setStyleSheet("background-color: rgba(100, 200, 100, 60); padding: 2px 5px; border-radius: 3px;")
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
        self.spots_table.setHorizontalHeaderLabels([
            "Callsign", "Frequency", "Mode", "Speed", "SKCC#", "Reporter", "Time", "Age"
        ])
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


    def _load_band_selections(self) -> None:
        """Load saved band selections from config and apply them"""
        try:
            # Get saved band selections from config
            saved_bands_str = self.config_manager.get("dx_cluster.band_selections", "")
            if saved_bands_str:
                saved_bands = set(saved_bands_str.split(","))
                # Apply saved selections to checkboxes
                for band, check in self.band_checks.items():
                    check.setChecked(band in saved_bands)
            logger.debug(f"Loaded band selections from config: {saved_bands_str}")
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
        self._filter_debounce_timer.start(self._filter_debounce_ms)

    def _apply_filters_debounced(self) -> None:
        """Apply filters after debounce period (called from timer)"""
        self._apply_filters()

    def _sync_roster(self) -> None:
        """Sync SKCC membership roster - force fresh download in background thread"""
        try:
            self.sync_btn.setEnabled(False)
            self.status_label.setText("Status: Clearing cache and downloading fresh roster... (may take 30 seconds)")

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
                        self.status_label.setText(f"✓ SUCCESS: {roster_count} real SKCC members loaded! Click Start Monitoring for real spots.")
                        logger.info(f"Successfully downloaded real SKCC roster: {roster_count} members")
                    elif roster_count > 0:
                        self.status_label.setText(f"⚠️  Roster has {roster_count} members (expected 1000+). Real roster download may have failed.")
                        logger.warning(f"Roster download returned {roster_count} members - may be test data or partial")
                    else:
                        self.status_label.setText("❌ Roster sync failed - check network connection.")
                        logger.error("Roster sync failed - 0 members")
                except Exception as e:
                    logger.error(f"Error handling roster sync completion: {e}", exc_info=True)
                finally:
                    self.sync_btn.setEnabled(True)
                    if hasattr(self, '_roster_sync_thread'):
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
        """Toggle SKCC Skimmer monitoring on/off"""
        try:
            if self.skcc_skimmer.is_running():
                self.skcc_skimmer.stop()
                self.connect_btn.setText("Start Monitoring")
                self.status_label.setText("Status: Stopped")
            else:
                self.connect_btn.setEnabled(False)
                self.status_label.setText("Status: Starting... (check logs if stuck)")

                # Check roster
                roster_count = len(self.db.skcc_members.get_roster_dict())
                if roster_count == 0:
                    self.status_label.setText(
                        "⚠️  SKCC roster empty! Click 'Sync Roster' button first."
                    )
                    self.connect_btn.setEnabled(True)
                    logger.warning("Cannot start spotting - SKCC roster is empty")
                    return

                # Export ADIF file for SKCC Skimmer (it needs an ADIF file to know what you've already worked)
                logger.info("Exporting ADIF file for SKCC Skimmer...")
                self.status_label.setText("Status: Exporting contacts to ADIF...")
                try:
                    from src.backup.backup_manager import BackupManager
                    from pathlib import Path as PathlibPath

                    all_contacts = self.db.get_all_contacts()
                    if all_contacts and len(all_contacts) > 0:
                        backup_manager = BackupManager()
                        my_skcc = self.config_manager.get("adif.my_skcc_number", "")
                        my_callsign = self.config_manager.get("general.operator_callsign", "")

                        project_root = PathlibPath(__file__).parent.parent.parent.parent
                        adif_path = project_root / "logs" / "contacts.adi"

                        result = backup_manager.export_single_adif(
                            contacts=all_contacts,
                            output_path=adif_path,
                            my_skcc=my_skcc if my_skcc else None,
                            my_callsign=my_callsign if my_callsign and my_callsign != 'MYCALL' else None
                        )

                        if result["success"]:
                            logger.info(f"ADIF exported: {result['message']}")
                        else:
                            logger.warning(f"ADIF export failed: {result['message']}")
                    else:
                        logger.warning("No contacts to export for SKCC Skimmer")
                except Exception as export_error:
                    logger.error(f"Error exporting ADIF: {export_error}", exc_info=True)

                # Start SKCC Skimmer for intelligent spot filtering
                logger.info("Starting SKCC Skimmer subprocess for intelligent spot filtering...")
                self.status_label.setText("Status: Starting SKCC Skimmer...")
                success = self.skcc_skimmer.start()

                if success:
                    self.skcc_skimmer.set_callbacks(
                        on_spot=self._on_skimmer_spot_line,
                        on_state_change=self._on_skimmer_state_changed
                    )
                    self.connect_btn.setText("Stop Monitoring")
                    self.connect_btn.setEnabled(True)
                    self.status_label.setText(f"Status: SKCC Skimmer active (filtering spots)")
                else:
                    logger.error("Failed to start SKCC Skimmer")
                    self.connect_btn.setText("Start Monitoring")
                    self.connect_btn.setEnabled(True)
                    self.status_label.setText(f"Status: Failed to start SKCC Skimmer (check configuration)")

        except Exception as e:
            logger.error(f"Error toggling monitoring: {e}", exc_info=True)
            self.status_label.setText(f"Error: {str(e)}")
            self.connect_btn.setEnabled(True)

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
                    logger.debug(f"Skipping duplicate spot: {callsign} on {spot.frequency:.3f} MHz (shown {time_since_last:.0f}s ago)")
                    return

            # Add to display list and update tracking
            self.last_shown_time[spot_key] = now
            self.spots.insert(0, spot)

            # Keep only recent spots in memory
            if len(self.spots) > 200:
                self.spots = self.spots[:200]

            # Update the display
            self._on_filter_changed()

        except Exception as e:
            logger.error(f"Error handling spot {spot.callsign}: {e}", exc_info=True)

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
            skcc_number = member_info.get('skcc_number') if isinstance(member_info, dict) else member_info

            if not skcc_number:
                return False

            # Ensure skcc_number is a string before checking suffix
            skcc_str = str(skcc_number).strip()
            if len(skcc_str) == 0:
                return False

            return skcc_str[-1] in ('C', 'T', 'S')
        except Exception as e:
            logger.debug(f"Error checking SKCC suffix for {callsign}: {e}")
            return False

    def _apply_filters(self) -> None:
        """Apply filters to spots list (optimized for performance)"""
        # Start with all spots
        filtered_spots = self.spots

        # Build band frequency ranges once (optimization: avoid repeated calls to _get_band_freq_range)
        selected_bands = [band for band, check in self.band_checks.items() if check.isChecked()]
        band_ranges = {}
        if selected_bands:
            for band in selected_bands:
                freq_range = self._get_band_freq_range(band)
                if freq_range:
                    band_ranges[band] = freq_range

        # Apply all filters in a single pass (optimization: avoid multiple list copies)
        min_strength = self.strength_spin.value()
        check_unworked = self.unworked_only_check.isChecked()
        worked_callsigns = self._get_worked_callsigns_cached() if check_unworked else set()

        # Get SKCC roster for suffix filtering (C, T, S only) - using cached version to avoid thread safety issues
        # Critical: Using cached roster prevents repeated database calls during high-volume RBN spot processing
        skcc_roster = self._get_skcc_roster_cached()

        # Single-pass filtering for better performance
        self.filtered_spots = [
            s for s in filtered_spots
            if s.mode == "CW"  # Mode filter
            and s.strength >= min_strength  # Strength filter
            and (not selected_bands or any(  # Band filter
                low <= s.frequency <= high
                for low, high in band_ranges.values()
            ))
            and (not check_unworked or s.callsign not in worked_callsigns)  # Unworked filter
            and self._is_valid_skcc_suffix(s.callsign, skcc_roster)  # SKCC suffix filter (C, T, or S only)
        ]

        self._update_table()

    def _load_startup_caches(self) -> None:
        """Load caches on startup to avoid queries during normal operation"""
        try:
            logger.info("Loading startup caches...")
            self._get_worked_callsigns_cached()  # Pre-load worked callsigns
            self._get_skcc_roster_cached()  # Pre-load SKCC roster for suffix filtering
            logger.info("Startup caches loaded successfully")
        except Exception as e:
            logger.error(f"Error loading startup caches: {e}", exc_info=True)

    def _get_worked_callsigns_cached(self) -> set[str]:
        """Return worked callsigns with a 30-minute TTL to reduce DB queries."""
        now = datetime.now(timezone.utc)
        if (
            self._worked_cache_timestamp is None or
            (now - self._worked_cache_timestamp).total_seconds() > self._worked_cache_ttl_seconds
        ):
            try:
                # Use efficient query - callsigns only, not full Contact objects
                session = self.db.get_session()
                try:
                    from src.database.models import Contact
                    worked_callsigns_result = session.query(Contact.callsign).distinct().all()
                    self._worked_callsigns_cache = {c[0].upper() for c in worked_callsigns_result if c[0]}
                    self._worked_cache_timestamp = now
                finally:
                    session.close()
            except Exception:
                # On error, return existing cache (may be empty)
                pass
        return self._worked_callsigns_cache

    def _get_skcc_roster_cached(self) -> dict:
        """
        Return SKCC roster with a 30-minute TTL to reduce DB queries.

        Critical: This prevents thread safety issues from calling get_roster_dict()
        on every filter operation during high-volume spot processing.

        Returns:
            Dictionary mapping callsigns to SKCC member info
        """
        now = datetime.now(timezone.utc)
        if (
            self._skcc_roster_cache_timestamp is None or
            (now - self._skcc_roster_cache_timestamp).total_seconds() > self._skcc_roster_cache_ttl_seconds
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
        """Clean up old spots from memory"""
        if self._is_shutting_down:
            return

        try:
            # Remove spots older than 10 minutes from memory
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
            old_count = len(self.spots)
            self.spots = [s for s in self.spots if s.timestamp > cutoff]
            if old_count > len(self.spots):
                logger.debug(f"Cleaned up {old_count - len(self.spots)} old spots from memory")

            # Clean up old entries from duplicate tracking - older than 2 minutes
            cutoff_tracking = datetime.now(timezone.utc) - timedelta(minutes=2)
            callsigns_to_remove = [
                callsign for callsign, timestamp in self.last_shown_time.items()
                if timestamp < cutoff_tracking
            ]
            for callsign in callsigns_to_remove:
                self.last_shown_time.pop(callsign, None)
            if callsigns_to_remove:
                logger.debug(f"Cleaned up {len(callsigns_to_remove)} old entries from duplicate tracking")

        except Exception as e:
            logger.error(f"Error in cleanup: {e}", exc_info=True)

    @staticmethod
    def _get_band_freq_range(band: str) -> Optional[tuple]:
        """Get frequency range for band (HF bands only)"""
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


    def _update_table(self) -> None:
        """Update spots table with filtered spots"""
        # NOTE: Spot highlighting disabled - it was causing 5-20 second UI freezes on every table update
        # See commit message for details. Can be re-enabled with background thread processing.

        # Disable updates during table rebuild to prevent flickering and improve scrolling performance
        self.spots_table.setUpdatesEnabled(False)
        try:
            self.spots_table.setRowCount(len(self.filtered_spots))
            self.spot_count_label.setText(f"Spots: {len(self.filtered_spots)}")

            for row, spot in enumerate(self.filtered_spots):
                row_data = SKCCSpotRow(spot)

                # Build SKCC number string - show if available, empty otherwise
                skcc_str = spot.skcc_number if spot.skcc_number else ""

                items = [
                    QTableWidgetItem(row_data.callsign),
                    QTableWidgetItem(row_data.frequency),
                    QTableWidgetItem(row_data.mode),
                    QTableWidgetItem(row_data.speed),
                    QTableWidgetItem(skcc_str),  # SKCC Number
                    QTableWidgetItem(row_data.reporter),
                    QTableWidgetItem(row_data.time),
                    QTableWidgetItem(row_data.get_age_string()),
                ]


                for col, item in enumerate(items):
                    item.setData(Qt.ItemDataRole.UserRole, spot)
                    self.spots_table.setItem(row, col, item)
        finally:
            # Re-enable updates to refresh the display
            self.spots_table.setUpdatesEnabled(True)

    def _on_skimmer_spot_line(self, line: str) -> None:
        """
        Handle SKCC Skimmer console output line (called from subprocess thread)

        Parse SKCC Skimmer's spot format and convert to SKCCSpot
        Format: "HH:MM:SS ± CALLSIGN (SKCC#) on FREQUENCY MHz MODE DETAILS"
        """
        try:
            logger.debug(f"SKCC Skimmer output: {line}")

            # Parse SKCC Skimmer spot line format
            # Example: "14:23:45 + K4ABC (12345T) on 14025.0 MHz CW 23 dB 15 WPM"

            # Basic parsing - extract key elements from the line
            import re

            # Extract callsign (word after + or - or space indicator)
            callsign_match = re.search(r'[\s+\-◆]\s+(\w{2,})\s', line)
            if not callsign_match:
                return
            callsign = callsign_match.group(1).upper()

            # Extract SKCC number if present
            skcc_match = re.search(r'\((\d+[A-Z]*)\)', line)
            skcc_number = skcc_match.group(1) if skcc_match else None

            # Extract frequency
            freq_match = re.search(r'(\d+[.,]?\d*)\s*(kHz|MHz)', line)
            if not freq_match:
                return
            freq_str = freq_match.group(1).replace(',', '.')
            freq_mhz = float(freq_str)
            if 'kHz' in freq_match.group(2):
                freq_mhz = freq_mhz / 1000  # Convert kHz to MHz

            # Extract mode (CW, SSB, etc.)
            mode_match = re.search(r'\b(CW|SSB|LSB|USB|FM|RTTY|FT8|FT4)\b', line, re.IGNORECASE)
            mode = mode_match.group(1).upper() if mode_match else "CW"

            # Extract signal strength
            signal_match = re.search(r'(\d+)\s*dB', line)
            strength = int(signal_match.group(1)) if signal_match else 0

            # Extract speed (WPM) for CW
            speed_match = re.search(r'(\d+)\s*WPM', line)
            speed = int(speed_match.group(1)) if speed_match else None

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
                is_skcc=True,  # SKCC Skimmer only shows SKCC spots
                skcc_number=skcc_number,
            )

            # Handle the spot
            self._handle_skimmer_spot(spot)

        except Exception as e:
            logger.error(f"Error parsing SKCC Skimmer spot line: {e}")

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
            if hasattr(self, 'skcc_skimmer') and self.skcc_skimmer:
                if self.skcc_skimmer.is_running():
                    logger.info("Stopping SKCC Skimmer subprocess...")
                    self.skcc_skimmer.stop()

        except Exception as e:
            logger.error(f"Error cleaning up spots widget: {e}", exc_info=True)
        super().closeEvent(event)
