"""
SKCC Spots Widget - Display and manage SKCC member spots

Shows recent SKCC member spots from RBN with filtering and integration
with the logging form.
"""

import logging
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime, timedelta, timezone

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QComboBox, QCheckBox, QSpinBox, QHeaderView,
    QGroupBox, QGridLayout, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
from PyQt6.QtGui import QColor, QFont

from src.skcc import SKCCSpotManager, SKCCSpot, SKCCSpotFilter, RBNConnectionState
from src.config.settings import get_config_manager
from src.database.models import Contact

if TYPE_CHECKING:
    from src.ui.spot_matcher import SpotMatcher

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


class SpotProcessingWorker(QObject):
    """Queue-based worker for processing spots in background thread with batched database writes"""
    spot_processed = pyqtSignal(object, set, str, bool)  # spot, worked_callsigns, goal_type, should_store

    def __init__(self, spot_manager, spot_filter: SKCCSpotFilter):
        super().__init__()
        self.spot_manager = spot_manager
        self.spot_filter = spot_filter
        self.running = True
        self.spot_queue: List[SKCCSpot] = []

        # Batching parameters to reduce database lock contention
        self.batch_write_size = 10  # Write spots in batches of 10
        self.batch_timeout_ms = 500  # Or every 500ms, whichever comes first
        self.pending_spots = []  # Spots waiting to be written
        self.last_batch_time = datetime.now(timezone.utc)

        # Cache worked callsigns to avoid repeated queries
        self._worked_callsigns_cache: Optional[set] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 5  # Refresh cache every 5 seconds

    def add_spot(self, spot: SKCCSpot):
        """Add spot to processing queue with overflow protection"""
        self.spot_queue.append(spot)

        # Safety valve: if queue gets too large, drop oldest spots
        # This prevents memory explosion if processing can't keep up with spots
        max_queue_size = 1000  # Max 1000 pending spots in queue
        if len(self.spot_queue) > max_queue_size:
            overflow_count = len(self.spot_queue) - max_queue_size
            self.spot_queue = self.spot_queue[overflow_count:]
            logger.warning(f"Spot queue overflow: dropped {overflow_count} old spots to prevent memory leak")

    def process_spots(self):
        """Process all queued spots with batched database writes"""
        while self.running:
            # Process all spots in queue
            while self.spot_queue and self.running:
                spot = self.spot_queue.pop(0)
                self._process_single_spot(spot)

            # Check if we should flush pending writes
            time_since_last_batch = (datetime.now(timezone.utc) - self.last_batch_time).total_seconds() * 1000
            if self.pending_spots and time_since_last_batch >= self.batch_timeout_ms:
                self._flush_pending_writes()

            # Sleep briefly to avoid busy-waiting
            QThread.msleep(10)

    def _process_single_spot(self, spot: SKCCSpot):
        """Process a single spot (without writing to database yet)"""
        try:
            # Get worked callsigns with caching to reduce database queries
            worked_callsigns = self._get_worked_callsigns_cached()

            # Apply spot filter
            if not self.spot_filter.matches(spot, worked_callsigns):
                logger.debug(f"Spot {spot.callsign} filtered by spot_filter")
                self.spot_processed.emit(spot, worked_callsigns, "NONE", False)
                return

            # Classify spot as GOAL/TARGET/BOTH
            goal_type = self.spot_manager.spot_classifier.classify_spot(spot.callsign)

            # Prepare spot data for batched write
            spot_data = {
                "frequency": round(spot.frequency, 3),
                "dx_callsign": spot.callsign,
                "de_callsign": spot.reporter,
                "dx_grid": spot.grid,
                "comment": f"Speed: {spot.speed} WPM" if spot.speed else None,
                "received_at": spot.timestamp,
                "spotted_date": spot.timestamp.strftime("%Y%m%d"),
                "spotted_time": spot.timestamp.strftime("%H%M"),
            }

            # Add to pending batch instead of writing immediately
            self.pending_spots.append((spot_data, spot, worked_callsigns, goal_type))

            # Flush if batch is full
            if len(self.pending_spots) >= self.batch_write_size:
                self._flush_pending_writes()

            logger.debug(f"Queued spot {spot.callsign} for batched write (pending: {len(self.pending_spots)})")

        except Exception as e:
            logger.error(f"Error processing spot: {e}", exc_info=True)
            self.spot_processed.emit(spot, set(), "NONE", False)

    def _get_worked_callsigns_cached(self) -> set:
        """Get worked callsigns with caching to reduce database queries"""
        now = datetime.now(timezone.utc)

        # Use cache if still valid
        if (self._worked_callsigns_cache is not None and
            self._cache_timestamp is not None and
            (now - self._cache_timestamp).total_seconds() < self._cache_ttl_seconds):
            return self._worked_callsigns_cache

        # Refresh cache
        session = self.spot_manager.db.get_session()
        try:
            worked_callsigns_result = session.query(Contact.callsign).distinct().all()
            self._worked_callsigns_cache = {c[0].upper() for c in worked_callsigns_result if c[0]}
            self._cache_timestamp = now
            return self._worked_callsigns_cache
        finally:
            session.close()

    def _flush_pending_writes(self):
        """Flush all pending spots to database in a single transaction"""
        if not self.pending_spots:
            return

        session = self.spot_manager.db.get_session()
        try:
            # Batch write all pending spots in a single transaction
            from src.database.models import ClusterSpot
            batch_count = len(self.pending_spots)

            for spot_data, spot, worked_callsigns, goal_type in self.pending_spots:
                db_spot = ClusterSpot(**spot_data)
                session.add(db_spot)
                # Emit signal for UI update (non-blocking)
                self.spot_processed.emit(spot, worked_callsigns, goal_type, True)

            session.commit()
            logger.debug(f"Flushed {batch_count} spots to database in batch write")
            self.pending_spots.clear()
            self.last_batch_time = datetime.now(timezone.utc)
        except Exception as e:
            session.rollback()
            logger.error(f"Error in batch write: {e}", exc_info=True)
            # Emit failure for all pending spots
            for spot_data, spot, worked_callsigns, goal_type in self.pending_spots:
                self.spot_processed.emit(spot, worked_callsigns, "NONE", False)
            self.pending_spots.clear()
        finally:
            session.close()

    def stop(self):
        """Stop processing and flush any pending writes"""
        self.running = False
        # Flush remaining spots before stopping
        self._flush_pending_writes()


class CleanupWorker(QThread):
    """Worker thread for cleaning up old spots"""
    finished = pyqtSignal()

    def __init__(self, spot_manager, spots: List, last_shown_time: Dict):
        super().__init__()
        self.spot_manager = spot_manager
        self.spots = spots
        self.last_shown_time = last_shown_time
        self.new_spots = []
        self.callsigns_to_remove = []

    def run(self):
        """Run cleanup in background thread"""
        try:
            # Remove spots older than 10 minutes from memory (was 30) - more aggressive cleanup
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
            old_count = len(self.spots)
            self.new_spots = [s for s in self.spots if s.timestamp > cutoff]
            if old_count > len(self.new_spots):
                logger.debug(f"Cleaned up {old_count - len(self.new_spots)} old spots from memory")

            # Remove spots older than 24 hours from database
            self.spot_manager.cleanup_old_spots(hours=24)

            # Clean up old entries from duplicate tracking - much more aggressive (was 5 minutes)
            cutoff_tracking = datetime.now(timezone.utc) - timedelta(minutes=2)
            self.callsigns_to_remove = [
                callsign for callsign, timestamp in self.last_shown_time.items()
                if timestamp < cutoff_tracking
            ]

            if self.callsigns_to_remove:
                logger.debug(f"Cleaned up {len(self.callsigns_to_remove)} old entries from duplicate tracking")
        except Exception as e:
            logger.error(f"Error in cleanup worker: {e}", exc_info=True)
        finally:
            self.finished.emit()


class AwardCacheWorker(QThread):
    """Worker thread for refreshing award cache"""
    finished = pyqtSignal(set, set, set)  # worked_skcc, award_critical, all_progress

    def __init__(self, spot_manager):
        super().__init__()
        self.spot_manager = spot_manager

    def run(self):
        """Run award cache refresh in background thread"""
        try:
            from src.database.models import Contact

            # Get SKCC numbers we've worked
            session = self.spot_manager.db.get_session()
            try:
                worked_skcc_numbers = session.query(Contact.skcc_number).filter(
                    Contact.skcc_number.isnot(None)
                ).distinct().all()
                worked_skcc_members = {num[0].upper() for num in worked_skcc_numbers if num[0]}
            finally:
                session.close()

            # Get SKCC roster
            roster = self.spot_manager.db.skcc_members.get_roster_dict()

            # Get current SKCC award progress
            skcc_progress = self.spot_manager.db.get_award_progress("SKCC", "Members")

            # Determine target count
            target_count = self._get_target_skcc_count(skcc_progress)

            # Calculate award-critical members
            if target_count and len(worked_skcc_members) < target_count:
                all_skcc_numbers = set(roster.keys()) if roster else set()
                award_critical_skcc_members = all_skcc_numbers - worked_skcc_members
            else:
                award_critical_skcc_members = set()

            logger.debug(
                f"Award cache updated: worked={len(worked_skcc_members)}, "
                f"critical={len(award_critical_skcc_members)}, "
                f"target={target_count}"
            )

            self.finished.emit(worked_skcc_members, award_critical_skcc_members, set())
        except Exception as e:
            logger.error(f"Error in award cache worker: {e}")
            self.finished.emit(set(), set(), set())

    @staticmethod
    def _get_target_skcc_count(progress: Dict[str, Any]) -> Optional[int]:
        """Get target SKCC member count based on current progress"""
        if not progress:
            return 25  # Default to Centurion (C)

        current = progress.get("current", 0)

        # SKCC award levels
        levels = [25, 50, 100, 200, 500, 1000]
        for level in levels:
            if current < level:
                return level

        return None  # Already at highest level


class SKCCSpotWidget(QWidget):
    """Widget for displaying and managing SKCC spots"""

    # Signal when user clicks on a spot (to populate logging form)
    spot_selected = pyqtSignal(str, float)  # callsign, frequency

    # Internal signal for thread-safe spot handling from background thread
    _new_spot_signal = pyqtSignal(object)  # SKCCSpot object

    def __init__(self, spot_manager: SKCCSpotManager, spot_matcher: Optional['SpotMatcher'] = None, 
                 parent: Optional[QWidget] = None):
        """
        Initialize SKCC spots widget

        Args:
            spot_manager: SKCCSpotManager instance
            spot_matcher: Optional SpotMatcher instance for award eligibility analysis
            parent: Parent widget
        """
        super().__init__(parent)
        self.spot_manager = spot_manager
        self.spot_matcher = spot_matcher
        self.spots: List[SKCCSpot] = []
        self.filtered_spots: List[SKCCSpot] = []

        # Worked callsigns cache for "Unworked only" filter
        # Cache on startup and refresh every 30 minutes (not 60 seconds) to reduce DB load
        self._worked_callsigns_cache: set[str] = set()
        self._worked_cache_timestamp: Optional[datetime] = None
        self._worked_cache_ttl_seconds: int = 1800  # 30 minutes (was 60 seconds)

        # Cache for award-critical spots (legacy, still used as fallback)
        self.award_critical_skcc_members: set = set()
        self.worked_skcc_members: set = set()

        # Load caches on startup (non-blocking) instead of deferring
        QTimer.singleShot(100, self._load_startup_caches)

        # Duplicate detection: track last time each callsign was shown (3-minute cooldown)
        self.last_shown_time: Dict[str, datetime] = {}
        self.duplicate_cooldown_seconds = 180  # 3 minutes

        # Background worker threads
        self._cleanup_worker: Optional[CleanupWorker] = None
        self._award_cache_worker: Optional[AwardCacheWorker] = None
        self._is_shutting_down = False  # Flag to prevent new workers during shutdown

        # Single persistent worker for spot processing
        self._spot_processing_thread = QThread()
        self._spot_processing_worker = SpotProcessingWorker(self.spot_manager, self.spot_manager.spot_filter)
        self._spot_processing_worker.moveToThread(self._spot_processing_thread)
        self._spot_processing_worker.spot_processed.connect(self._on_spot_processed)
        self._spot_processing_thread.started.connect(self._spot_processing_worker.process_spots)
        self._spot_processing_thread.start()

        # Config manager for persisting band selections
        self.config_manager = get_config_manager()

        # Debounce timer to throttle filter changes
        # Prevents excessive table updates when user rapidly changes filters
        self._filter_debounce_timer = QTimer()
        self._filter_debounce_timer.setSingleShot(True)
        self._filter_debounce_timer.timeout.connect(self._apply_filters_debounced)
        self._filter_debounce_ms = 100  # Wait 100ms after last change before updating

        # Set up UI
        self._init_ui()
        self._load_band_selections()  # Load saved band selections
        self._connect_signals()

        # Connect internal signal for thread-safe spot handling
        self._new_spot_signal.connect(self._handle_new_spot_on_main_thread)

        # Auto-cleanup timer (runs periodically to clean up old spots)
        # Frequent cleanup to prevent memory buildup from high-volume RBN spots
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._cleanup_old_spots)
        self.cleanup_timer.start(30000)  # Cleanup every 30 seconds (was 2 minutes)

        # Award cache refresh timer (runs periodically to update award-critical member list)
        # Reduced frequency to avoid excessive database queries and memory pressure
        self.award_cache_timer = QTimer()
        self.award_cache_timer.timeout.connect(self._refresh_award_cache)
        self.award_cache_timer.start(300000)  # Refresh every 5 minutes (was 60s)

        # Note: Spot display refresh is now event-driven via _on_new_spot() callback
        # instead of polling every 5 seconds. This significantly reduces CPU usage.

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

    def _connect_signals(self) -> None:
        """Connect spot manager signals"""
        self.spot_manager.set_callbacks(
            on_new_spot=self._on_new_spot,
            on_connection_state=self._on_connection_state_changed,
        )

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
            self.spot_manager.db.skcc_members.clear_cache()

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
                        self.status_label.setText("❌ Roster sync failed - check network connection. Use Load Test Data to continue.")
                        logger.error("Roster sync failed - 0 members")

                    # Switch to RBN mode when syncing real roster
                    self.spot_manager.use_test_spots = False
                    logger.info("Switched to RBN mode (real spots)")

                    # Refresh award cache with new roster
                    self._refresh_award_cache()
                except Exception as e:
                    logger.error(f"Error handling roster sync completion: {e}", exc_info=True)
                finally:
                    self.sync_btn.setEnabled(True)
                    if hasattr(self, '_roster_sync_thread'):
                        self._roster_sync_thread.deleteLater()
                        self._roster_sync_thread = None

            # Start background thread
            self._roster_sync_thread = RosterSyncThread(self.spot_manager.db)
            self._roster_sync_thread.finished_signal.connect(on_sync_complete)
            self._roster_sync_thread.start()

        except Exception as e:
            logger.error(f"Error starting roster sync: {e}", exc_info=True)
            self.status_label.setText(f"Error syncing roster: {str(e)}")
            self.sync_btn.setEnabled(True)

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
        """
        Handle new spot received from background thread.
        This is called from the RBN thread, so we emit a signal to handle it on the main thread.
        """
        # Emit signal to handle on main UI thread (thread-safe)
        self._new_spot_signal.emit(spot)
    
    def _handle_new_spot_on_main_thread(self, spot: SKCCSpot) -> None:
        """
        Handle new spot on main UI thread (called via signal)

        Checks for duplicates and queues spot for background processing.
        This keeps the main thread responsive for UI operations like callsign input.
        """
        try:
            now = datetime.now(timezone.utc)
            callsign = spot.callsign.upper()

            # Check if this callsign was shown recently (lightweight check on main thread)
            if callsign in self.last_shown_time:
                time_since_last = (now - self.last_shown_time[callsign]).total_seconds()
                if time_since_last < self.duplicate_cooldown_seconds:
                    # Duplicate within cooldown period - skip it
                    logger.debug(f"Skipping duplicate spot: {callsign} (shown {time_since_last:.0f}s ago)")
                    return

            # Add to queue for background processing
            self._spot_processing_worker.add_spot(spot)
            logger.debug(f"Queued spot {callsign} for background processing")

        except Exception as e:
            logger.error(f"Error handling spot {spot.callsign}: {e}", exc_info=True)

    def _on_spot_processed(self, processed_spot: SKCCSpot, worked_callsigns: set, goal_type: str, should_store: bool):
        """
        Handle spot processing completion on main thread

        Args:
            processed_spot: The processed spot
            worked_callsigns: Set of worked callsigns
            goal_type: Classified goal type
            should_store: Whether spot should be stored in display
        """
        try:
            if not should_store:
                # Spot was filtered out
                return

            # Set goal type if classified
            if goal_type and goal_type != "NONE":
                processed_spot.goal_type = goal_type
                logger.debug(f"{processed_spot.callsign} classified as {goal_type}")

            # Update tracking and add spot to display
            now = datetime.now(timezone.utc)
            self.last_shown_time[processed_spot.callsign.upper()] = now
            self.spots.insert(0, processed_spot)

            # Keep only recent spots in memory
            if len(self.spots) > 200:
                self.spots = self.spots[:200]

            # Debounce filter updates to prevent excessive main thread work
            # This throttles table redraws from potentially 100+ spots/min to just a few updates/sec
            self._on_filter_changed()

        except Exception as e:
            logger.error(f"Error in spot processing callback: {e}", exc_info=True)

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
        ]

        self._update_table()

    def _load_startup_caches(self) -> None:
        """Load caches on startup to avoid queries during normal operation"""
        try:
            logger.info("Loading startup caches...")
            self._get_worked_callsigns_cached()  # Pre-load worked callsigns
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
                session = self.spot_manager.db.get_session()
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
        """Clean up old spots from memory and database in background thread"""
        # Don't start new cleanup if shutting down or if one is already running
        if self._is_shutting_down:
            logger.debug("Widget is shutting down, skipping cleanup")
            return

        if hasattr(self, '_cleanup_worker') and self._cleanup_worker and self._cleanup_worker.isRunning():
            logger.debug("Cleanup worker already running, skipping")
            return

        def on_cleanup_finished():
            """Handle cleanup completion on main thread"""
            try:
                # Check if widget is still valid (not being destroyed)
                if not self or not hasattr(self, 'spots'):
                    logger.debug("SKCC spots widget destroyed, skipping cleanup update")
                    if hasattr(self, '_cleanup_worker') and self._cleanup_worker:
                        # Clean up the worker even if widget is being destroyed
                        try:
                            # DO NOT CALL .wait() ON UI THREAD - it blocks the entire GUI!
                            # The thread has already finished (we're in the finished signal), so just schedule deletion
                            self._cleanup_worker.deleteLater()
                        except:
                            pass
                    return

                if self._cleanup_worker:
                    # Update spots list with cleaned spots
                    # NOTE: We're already in the signal callback, so the thread has finished
                    self.spots = self._cleanup_worker.new_spots

                    # Remove tracked callsigns
                    for callsign in self._cleanup_worker.callsigns_to_remove:
                        self.last_shown_time.pop(callsign, None)

                    # Disconnect signal before deletion to prevent double-calls
                    try:
                        self._cleanup_worker.finished.disconnect()
                    except:
                        pass

                    # DO NOT CALL .wait() ON UI THREAD - it blocks the entire GUI!
                    # The thread has already finished (we're in the finished signal), so just schedule deletion
                    self._cleanup_worker.deleteLater()
                    self._cleanup_worker = None
            except Exception as e:
                logger.error(f"Error handling cleanup completion: {e}")

        # Start background cleanup with COPIES of mutable data to avoid race conditions
        # The worker thread will iterate over these copies, not the live references
        self._cleanup_worker = CleanupWorker(
            self.spot_manager,
            self.spots.copy(),  # COPY to avoid race condition while main thread modifies
            self.last_shown_time.copy()  # COPY to avoid race condition while main thread modifies
        )
        self._cleanup_worker.finished.connect(on_cleanup_finished)
        self._cleanup_worker.start()
        logger.debug("Started background cleanup worker")

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

    def _refresh_award_cache(self) -> None:
        """Refresh cached data for award-critical SKCC members in background thread"""
        # Don't start new refresh if shutting down or if one is already running
        if self._is_shutting_down:
            logger.debug("Widget is shutting down, skipping award cache refresh")
            return

        if hasattr(self, '_award_cache_worker') and self._award_cache_worker and self._award_cache_worker.isRunning():
            logger.debug("Award cache worker already running, skipping")
            return

        def on_cache_refresh_finished(worked_skcc: set, award_critical: set, _: set):
            """Handle award cache refresh completion on main thread"""
            try:
                # Check if widget is still valid (not being destroyed)
                if not self or not hasattr(self, 'worked_skcc_members'):
                    logger.debug("SKCC spots widget destroyed, skipping award cache update")
                    if hasattr(self, '_award_cache_worker') and self._award_cache_worker:
                        # Clean up the worker even if widget is being destroyed
                        try:
                            # DO NOT CALL .wait() ON UI THREAD - it blocks the entire GUI!
                            # The thread has already finished (we're in the finished signal), so just schedule deletion
                            self._award_cache_worker.deleteLater()
                        except:
                            pass
                    return

                if self._award_cache_worker:
                    # Update cache with new data
                    self.worked_skcc_members = worked_skcc
                    self.award_critical_skcc_members = award_critical

                    # Disconnect signal before deletion to prevent double-calls
                    try:
                        self._award_cache_worker.finished.disconnect()
                    except:
                        pass

                    # DO NOT CALL .wait() ON UI THREAD - it blocks the entire GUI!
                    # The thread has already finished (we're in the finished signal), so just schedule deletion
                    self._award_cache_worker.deleteLater()
                    self._award_cache_worker = None
            except Exception as e:
                logger.error(f"Error handling award cache completion: {e}")

        # Start background refresh
        self._award_cache_worker = AwardCacheWorker(self.spot_manager)
        self._award_cache_worker.finished.connect(on_cache_refresh_finished)
        self._award_cache_worker.start()
        logger.debug("Started background award cache worker")

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
        from src.ui.spot_eligibility_analyzer import EligibilityLevel

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

                # Use award eligibility analyzer if available
                highlight_color = None
                tooltip_text = ""

                if self.spot_matcher and self.spot_matcher.eligibility_analyzer:
                    try:
                        eligibility = self.spot_matcher.get_spot_eligibility(spot)

                        # Color based on eligibility level
                        color_map = {
                            EligibilityLevel.CRITICAL: QColor(255, 0, 0, 120),      # Red
                            EligibilityLevel.HIGH: QColor(255, 100, 0, 100),        # Orange
                            EligibilityLevel.MEDIUM: QColor(255, 200, 0, 80),       # Yellow
                            EligibilityLevel.LOW: QColor(100, 200, 100, 60),        # Green
                            EligibilityLevel.NONE: None,                             # No highlight
                        }

                        if eligibility and eligibility.eligibility_level in color_map:
                            highlight_color = color_map[eligibility.eligibility_level]
                            tooltip_text = eligibility.tooltip_text or ""

                    except Exception as e:
                        logger.debug(f"Error getting eligibility for {spot.callsign}: {e}")

                # Fallback to legacy award-critical highlighting if no analyzer
                if not highlight_color:
                    is_award_critical = self._is_award_critical_spot(spot)
                    if is_award_critical:
                        highlight_color = QColor("#90EE90")  # Light green
                        tooltip_text = "Award-critical SKCC member"

                # Apply highlighting and tooltip
                if highlight_color:
                    for item in items:
                        item.setBackground(highlight_color)
                        if tooltip_text:
                            item.setData(Qt.ItemDataRole.ToolTipRole, tooltip_text)

                for col, item in enumerate(items):
                    item.setData(Qt.ItemDataRole.UserRole, spot)
                    self.spots_table.setItem(row, col, item)
        finally:
            # Re-enable updates to refresh the display
            self.spots_table.setUpdatesEnabled(True)

    def closeEvent(self, event) -> None:
        """Clean up when widget is closed"""
        # Set shutdown flag FIRST to prevent new workers from being created
        self._is_shutting_down = True

        try:
            self.cleanup_timer.stop()
            self.award_cache_timer.stop()
            self._filter_debounce_timer.stop()

            # Stop receiving new spots from RBN FIRST (before stopping processing thread)
            # This prevents new spots from being queued while we're shutting down
            if hasattr(self, 'spot_manager') and self.spot_manager:
                # Disconnect the new spot signal callback
                try:
                    self._new_spot_signal.disconnect()
                except:
                    pass  # Already disconnected

            # Stop the persistent spot processing thread
            if hasattr(self, '_spot_processing_thread') and self._spot_processing_thread:
                if hasattr(self, '_spot_processing_worker') and self._spot_processing_worker:
                    # Signal the worker to stop
                    self._spot_processing_worker.stop()

                # Quit the thread gracefully
                self._spot_processing_thread.quit()
                if not self._spot_processing_thread.wait(500):  # Wait max 500ms
                    logger.warning("Spot processing thread didn't stop in time, terminating...")
                    self._spot_processing_thread.terminate()
                    self._spot_processing_thread.wait(100)

            # Stop any running spot processing workers
            if hasattr(self, '_spot_processing_workers'):
                for worker in self._spot_processing_workers[:]:  # Copy list to avoid modification during iteration
                    if worker.isRunning():
                        worker.quit()
                        if not worker.wait(200):  # Quick timeout
                            worker.terminate()
                            worker.wait(100)
                    worker.deleteLater()
                self._spot_processing_workers.clear()

            # Stop any running worker threads with quick timeout
            if hasattr(self, '_cleanup_worker') and self._cleanup_worker:
                # Disconnect signal before stopping thread to prevent callbacks
                try:
                    self._cleanup_worker.finished.disconnect()
                except:
                    pass
                # Stop the worker
                if self._cleanup_worker.isRunning():
                    self._cleanup_worker.quit()
                    if not self._cleanup_worker.wait(500):  # Wait max 500ms
                        logger.warning("Cleanup worker didn't stop in time, terminating...")
                        self._cleanup_worker.terminate()
                        self._cleanup_worker.wait(100)
                self._cleanup_worker.deleteLater()
                self._cleanup_worker = None

            if hasattr(self, '_award_cache_worker') and self._award_cache_worker:
                # Disconnect signal before stopping thread to prevent callbacks
                try:
                    self._award_cache_worker.finished.disconnect()
                except:
                    pass
                # Stop the worker
                if self._award_cache_worker.isRunning():
                    self._award_cache_worker.quit()
                    if not self._award_cache_worker.wait(500):  # Wait max 500ms
                        logger.warning("Award cache worker didn't stop in time, terminating...")
                        self._award_cache_worker.terminate()
                        self._award_cache_worker.wait(100)
                self._award_cache_worker.deleteLater()
                self._award_cache_worker = None

            if self.spot_manager.is_running():
                self.spot_manager.stop()
        except Exception as e:
            logger.error(f"Error cleaning up spots widget: {e}", exc_info=True)
        super().closeEvent(event)
