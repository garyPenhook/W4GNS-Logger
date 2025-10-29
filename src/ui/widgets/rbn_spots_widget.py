"""
RBN Spots Widget

Displays real-time Reverse Beacon Network spots with award relevance information.
Includes highlighting of spots that match previously worked contacts.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QSpinBox, QCheckBox, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor

from src.skcc.spot_fetcher import RBNConnectionState, SKCCSpot
from src.skcc.spot_source_adapter import SpotSource
from src.ui.spot_matcher import SpotMatcher

logger = logging.getLogger(__name__)


class RBNSpotsWidget(QWidget):
    """
    Widget for displaying RBN spots

    Shows:
    - Callsign
    - Frequency
    - Time spotted
    - Distance (if grid square available)
    - Relevance (GOAL/TARGET/BOTH)
    - SNR/WPM
    """

    spot_selected = pyqtSignal(str)  # Emits callsign when spot is clicked

    def __init__(self, config_manager, db, parent=None):
        """
        Initialize RBN Spots Widget

        Args:
            config_manager: Configuration manager
            db: Database repository
            parent: Parent widget
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.db = db
        self.spots: List[SKCCSpot] = []
        # Optional reference to the shared spot manager; set by main window after construction
        self._spot_manager_ref = None  # type: ignore[attr-defined]

        # Minimal integration stub to keep legacy code paths functional and prevent attribute errors
        class _IntegrationStub:
            def __init__(self):
                self.spots: List[Any] = []
                self.spot_statistics: Dict[str, Any] = {
                    "total_spots": 0,
                    "goal_spots": 0,
                    "target_spots": 0,
                    "rbn_spots": 0,
                    "sked_spots": 0,
                    "unique_callsigns": set(),
                }

            def is_available(self) -> bool:
                return False

            def get_recent_spots(self, limit: int = 50) -> List[Any]:
                return list(self.spots)[-limit:]

            def get_spot_statistics(self) -> Dict[str, Any]:
                return {
                    "total_spots": len(self.spots),
                    "goal_spots": 0,
                    "target_spots": 0,
                    "rbn_spots": len(self.spots),
                    "sked_spots": 0,
                    "unique_callsigns": len({getattr(s, 'callsign', '') for s in self.spots}),
                }

        self.integration = _IntegrationStub()
        
        # Duplicate filtering - track last seen time for each callsign
        # 3 minute cooldown to avoid back-to-back spots of same station
        self.last_spot_time: Dict[str, datetime] = {}
        self.duplicate_cooldown_seconds = 180  # 3 minutes

        # Initialize spot matcher for highlighting worked contacts
        self.spot_matcher = SpotMatcher(db, config_manager)

        self._init_ui()
        self._setup_auto_refresh()

    def _init_ui(self) -> None:
        """Initialize UI components"""
        main_layout = QVBoxLayout()

        # Status bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("RBN: Connected")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        # Monitoring control buttons
        self.start_monitor_btn = QPushButton("Start Monitoring RBN")
        self.start_monitor_btn.clicked.connect(self._start_monitoring)
        status_layout.addWidget(self.start_monitor_btn)

        self.stop_monitor_btn = QPushButton("Stop Monitoring")
        self.stop_monitor_btn.clicked.connect(self._stop_monitoring)
        self.stop_monitor_btn.setEnabled(False)
        status_layout.addWidget(self.stop_monitor_btn)

        # Controls
        refresh_btn = QPushButton("Refresh Spots")
        refresh_btn.clicked.connect(self.refresh_spots)
        status_layout.addWidget(refresh_btn)

        clear_btn = QPushButton("Clear Spots")
        clear_btn.clicked.connect(self.clear_spots)
        status_layout.addWidget(clear_btn)

        main_layout.addLayout(status_layout)

        # Spot Source Selection
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Spot Source:"))
        
        self.source_label = QLabel("Auto-detecting...")
        self.source_label.setStyleSheet("font-weight: bold; color: blue;")
        source_layout.addWidget(self.source_label)
        
        source_layout.addWidget(QLabel("|"))
        
        self.source_combo = QComboBox()
        self.source_combo.addItem("Direct RBN", "direct_rbn")
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        source_layout.addWidget(self.source_combo)
        
        source_layout.addStretch()
        main_layout.addLayout(source_layout)

        # Spots table
        self.spots_table = QTableWidget()
        self.spots_table.setColumnCount(8)
        self.spots_table.setHorizontalHeaderLabels([
            "Callsign", "Frequency", "Time", "Distance", "Type", "SNR/WPM", "Source", "Spotter"
        ])
        self.spots_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.spots_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.spots_table.itemClicked.connect(self._on_spot_clicked)
        main_layout.addWidget(self.spots_table)

        # Statistics
        stats_group = QGroupBox("Statistics")
        stats_layout = QHBoxLayout()

        self.total_spots_label = QLabel("Total Spots: 0")
        self.unique_calls_label = QLabel("Unique Calls: 0")
        self.goal_spots_label = QLabel("Goal Spots: 0")
        self.target_spots_label = QLabel("Target Spots: 0")
        self.rbn_spots_label = QLabel("RBN: 0")
        self.sked_spots_label = QLabel("Sked: 0")

        stats_layout.addWidget(self.total_spots_label)
        stats_layout.addWidget(self.unique_calls_label)
        stats_layout.addWidget(self.goal_spots_label)
        stats_layout.addWidget(self.target_spots_label)
        stats_layout.addWidget(QLabel("|"))  # Divider
        stats_layout.addWidget(self.rbn_spots_label)
        stats_layout.addWidget(self.sked_spots_label)
        stats_layout.addStretch()

        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QHBoxLayout()

        options_layout.addWidget(QLabel("Auto-refresh (seconds):"))
        self.refresh_spin = QSpinBox()
        self.refresh_spin.setMinimum(5)
        self.refresh_spin.setMaximum(60)
        self.refresh_spin.setValue(10)
        self.refresh_spin.setSuffix("s")
        options_layout.addWidget(self.refresh_spin)

        self.show_goals_check = QCheckBox("Show GOAL spots")
        self.show_goals_check.setChecked(True)
        options_layout.addWidget(self.show_goals_check)

        self.show_targets_check = QCheckBox("Show TARGET spots")
        self.show_targets_check.setChecked(True)
        options_layout.addWidget(self.show_targets_check)

        # Source filtering
        options_layout.addWidget(QLabel("|"))  # Divider
        
        self.show_rbn_check = QCheckBox("Show RBN spots")
        self.show_rbn_check.setChecked(True)
        options_layout.addWidget(self.show_rbn_check)

        self.show_sked_check = QCheckBox("Show Sked spots")
        self.show_sked_check.setChecked(True)
        options_layout.addWidget(self.show_sked_check)

        # Contact highlighting
        options_layout.addWidget(QLabel("|"))  # Divider
        
        self.highlight_worked_check = QCheckBox("Highlight Worked")
        self.highlight_worked_check.setChecked(
            self.config_manager.get("spots.highlight_worked", True)
        )
        self.highlight_worked_check.stateChanged.connect(self._on_highlighting_changed)
        options_layout.addWidget(self.highlight_worked_check)

        options_layout.addWidget(QLabel("Days:"))
        self.highlight_days_spin = QSpinBox()
        self.highlight_days_spin.setMinimum(1)
        self.highlight_days_spin.setMaximum(365)
        self.highlight_days_spin.setValue(
            self.config_manager.get("spots.highlight_recent_days", 30)
        )
        self.highlight_days_spin.setSuffix("d")
        self.highlight_days_spin.valueChanged.connect(self._on_highlighting_changed)
        options_layout.addWidget(self.highlight_days_spin)

        options_layout.addStretch()
        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)

        self.setLayout(main_layout)

    def _setup_auto_refresh(self) -> None:
        """Setup auto-refresh timer"""
        # NOTE: We do NOT call refresh_spots() on a timer anymore!
        # During real-time monitoring, spots come via callbacks (_on_new_spot_received)
        # Only call refresh_spots() manually or when NOT receiving live callbacks
        
        self.refresh_timer = QTimer()
        # OLD: self.refresh_timer.timeout.connect(self.refresh_spots)  <- DON'T DO THIS!
        # Just update the table display
        self.refresh_timer.timeout.connect(self._update_spots_table)
        self.refresh_timer.start(2000)  # Refresh display every 2 seconds
        
        # Add cleanup timer to remove old duplicate tracking entries
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._cleanup_old_duplicates)
        self.cleanup_timer.start(60000)  # Clean up every 60 seconds
        
        # Optionally add sample spots for demonstration when no live connection is available
        if not self.integration.is_available():
            try:
                self._add_sample_spots()
            except Exception:
                # Sample generation is best-effort only
                pass

    def _cleanup_old_duplicates(self) -> None:
        """Clean up old entries from duplicate tracking (older than 10 minutes)"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=10)
            removed_count = 0
            callsigns_to_remove = [
                callsign for callsign, timestamp in self.last_spot_time.items()
                if timestamp < cutoff_time
            ]
            for callsign in callsigns_to_remove:
                del self.last_spot_time[callsign]
                removed_count += 1
            
            if removed_count > 0:
                logger.debug(f"Cleaned up {removed_count} old duplicate tracking entries")
        except Exception as e:
            logger.error(f"Error cleaning up duplicate tracking: {e}", exc_info=True)

    def _start_monitoring(self) -> None:
        """Start RBN spot monitoring"""
        try:
            logger.info("RBN Widget: _start_monitoring called")
            
            # Try to use the SKCCSpotManager if we can access it
            if hasattr(self, '_spot_manager_ref') and self._spot_manager_ref:
                logger.info(f"RBN Widget: spot_manager_ref exists: {self._spot_manager_ref}")
                
                # Connect to spot callbacks FIRST before checking if running
                self._setup_spot_callbacks()
                
                # Check if already running by checking connection state
                if not self._spot_manager_ref.fetcher or self._spot_manager_ref.fetcher.connection_state == RBNConnectionState.DISCONNECTED:
                    # Not running yet, start it
                    logger.info("RBN Widget: Spot manager not running, starting...")
                    self._spot_manager_ref.start()
                    logger.info("RBN Widget: Started RBN monitoring via SKCCSpotManager")
                else:
                    # Already running, just connected callbacks
                    logger.info("RBN Widget: RBN monitoring already running, connected to spot stream")
                
                self.start_monitor_btn.setEnabled(False)
                self.stop_monitor_btn.setEnabled(True)
                self.status_label.setText("RBN Monitoring: Active")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
                
                # Update source indicator
                self._update_source_display()
            else:
                logger.error("RBN Widget: No spot manager reference available")
                self.status_label.setText("Error: No spot manager reference")
            
        except Exception as e:
            logger.error(f"RBN Widget: Failed to start monitoring: {e}", exc_info=True)
            self.status_label.setText(f"Error starting monitoring: {str(e)[:50]}")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")

    def _update_source_display(self) -> None:
        """Update the source display label based on active source"""
        try:
            if not hasattr(self, '_spot_manager_ref') or not self._spot_manager_ref:
                return
            
            active_source = getattr(self._spot_manager_ref, 'active_source', None)
            
            if active_source:
                from src.skcc.spot_source_adapter import SpotSource

                if active_source == SpotSource.DIRECT_RBN:
                    self.source_label.setText("🔵 Direct RBN Connection")
                    self.source_label.setStyleSheet("font-weight: bold; color: #0080FF;")
                    logger.info("RBN Widget: Displaying Direct RBN as active source")
                else:
                    self.source_label.setText("⚠️ Unknown source")
                    self.source_label.setStyleSheet("font-weight: bold; color: orange;")
            else:
                self.source_label.setText("⏳ Auto-detecting...")
                self.source_label.setStyleSheet("font-weight: bold; color: blue;")
                
        except Exception as e:
            logger.error(f"RBN Widget: Error updating source display: {e}", exc_info=True)

    def _setup_spot_callbacks(self) -> None:
        """Setup callbacks to receive spots from the spot manager"""
        if hasattr(self, '_spot_manager_ref') and self._spot_manager_ref:
            logger.info("RBN Widget: _setup_spot_callbacks - Setting on_new_spot callback")
            # Set callback to receive new spots
            old_callback = self._spot_manager_ref.on_new_spot
            self._spot_manager_ref.on_new_spot = self._on_new_spot_received
            logger.info(f"RBN Widget: Connected spot callbacks (old callback: {old_callback}, new callback: {self._on_new_spot_received})")
        else:
            logger.warning("RBN Widget: No spot manager reference for callbacks")

    def _on_new_spot_received(self, spot: Any) -> None:
        """Receive a new spot from the spot manager"""
        try:
            if not spot:
                logger.warning("Received None spot")
                return
            
            # Get spot details for logging
            callsign = getattr(spot, 'callsign', 'UNKNOWN')
            frequency = getattr(spot, 'frequency', 'N/A')
            logger.debug(f"RBN Widget: Received spot callback: {callsign} on {frequency} MHz")
            
            # Check for duplicate - skip if same callsign spotted recently
            if not self._should_show_spot(callsign):
                logger.debug(f"RBN Widget: Duplicate spot filtered: {callsign} (within 3 minutes)")
                return
            
            # Record this spot time for future duplicate checking
            self.last_spot_time[callsign] = datetime.now(timezone.utc)
            logger.debug(f"RBN Widget: Recording {callsign} at {datetime.now(timezone.utc)}")
                
            # Add the spot to our list
            self.spots.append(spot)
            logger.debug(f"RBN Widget: Added {callsign} to spots list (total: {len(self.spots)})")
            
            # Keep only last 100 spots to avoid memory bloat
            if len(self.spots) > 100:
                self.spots = self.spots[-100:]
            
            # Update the table safely
            try:
                self._update_spots_table()
                logger.debug(f"RBN Widget: Updated spots table with {len(self.spots)} spots")
            except Exception as e:
                logger.error(f"RBN Widget: Error updating spots table: {e}", exc_info=True)
            
            # Update statistics safely
            try:
                self._update_statistics()
                logger.debug("RBN Widget: Updated statistics")
            except Exception as e:
                logger.error(f"RBN Widget: Error updating statistics: {e}", exc_info=True)
            
            logger.debug(f"RBN Widget: Successfully processed spot: {callsign}")
        except Exception as e:
            logger.error(f"RBN Widget: Error processing new spot: {e}", exc_info=True)

    def _should_show_spot(self, callsign: str) -> bool:
        """
        Check if spot should be shown (not a duplicate within cooldown period)
        
        Args:
            callsign: The callsign to check
            
        Returns:
            True if spot should be shown, False if it's a duplicate
        """
        if callsign not in self.last_spot_time:
            return True  # First time seeing this callsign
        
        # Check if cooldown period has expired
        last_seen = self.last_spot_time[callsign]
        time_since_last = (datetime.now(timezone.utc) - last_seen).total_seconds()
        
        if time_since_last >= self.duplicate_cooldown_seconds:
            return True  # Cooldown period has expired, show it
        else:
            return False  # Still within cooldown, filter it out

    def _stop_monitoring(self) -> None:
        """Stop receiving RBN spots (doesn't stop DX Cluster tab monitoring)"""
        try:
            # Just disconnect callbacks, don't stop the spot manager
            # since it's shared with the DX Cluster tab
            if hasattr(self, '_spot_manager_ref') and self._spot_manager_ref:
                self._spot_manager_ref.on_new_spot = None
                logger.info("Disconnected from RBN spot stream")
            
            self.start_monitor_btn.setEnabled(True)
            self.stop_monitor_btn.setEnabled(False)
            self.status_label.setText("RBN Monitoring: Disconnected")
            self.status_label.setStyleSheet("color: orange; font-weight: bold;")
            
        except Exception as e:
            logger.error(f"Failed to stop monitoring: {e}", exc_info=True)

    def _on_source_changed(self, index: int) -> None:
        """Handle spot source selection change"""
        try:
            source_value = self.source_combo.currentData()
            logger.info(f"RBN Widget: User selected source: {source_value}")
            
            if not hasattr(self, '_spot_manager_ref') or not self._spot_manager_ref:
                logger.error("RBN Widget: No spot manager reference")
                return
            
            if source_value == "direct_rbn":
                logger.info("RBN Widget: Using Direct RBN source")
                try:
                    self._spot_manager_ref.active_source = None  # Clear to force re-init
                    self._spot_manager_ref.stop()  # Stop current source
                    self._spot_manager_ref.spot_source_adapter.use_direct_rbn()
                    self._spot_manager_ref.active_source = SpotSource.DIRECT_RBN
                    self.status_label.setText("RBN Monitoring: Using Direct RBN")
                    self.source_label.setText("Direct RBN Connection")
                    self.source_label.setStyleSheet("font-weight: bold; color: purple;")
                    self._spot_manager_ref.start()
                except Exception as e:
                    logger.error(f"RBN Widget: Error switching to Direct RBN: {e}", exc_info=True)
                    self.status_label.setText(f"RBN Monitoring: Error - {str(e)[:30]}")
                    self.source_label.setStyleSheet("font-weight: bold; color: red;")
            
        except Exception as e:
            logger.error(f"RBN Widget: Error changing source: {e}", exc_info=True)

    def _on_highlighting_changed(self) -> None:
        """Handle changes to highlighting preferences"""
        try:
            enabled = self.highlight_worked_check.isChecked()
            recent_days = self.highlight_days_spin.value()

            # Update config
            self.config_manager.set("spots.highlight_worked", enabled)
            self.config_manager.set("spots.highlight_recent_days", recent_days)

            # Update spot matcher
            self.spot_matcher.reload_config()

            # Refresh table to apply new highlighting
            self._update_spots_table()

            logger.debug(f"Highlighting updated: enabled={enabled}, recent_days={recent_days}")
        except Exception as e:
            logger.error(f"Error updating highlighting settings: {e}", exc_info=True)

    def refresh_spots(self) -> None:
        """Refresh spots from integration"""
        try:
            # Get recent spots (works whether SKCC Skimmer is installed or we have sample data)
            self.spots = self.integration.get_recent_spots(limit=50)

            # Update table
            self._update_spots_table()

            # Update statistics
            self._update_statistics()

            # Update status
            spot_count = len(self.spots)
            if self.integration.is_available():
                self.status_label.setText(
                    f"RBN: Connected ({spot_count} recent spots)"
                )
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.status_label.setText(
                    f"RBN: Demo mode ({spot_count} sample spots)"
                )
                self.status_label.setStyleSheet("color: orange; font-weight: bold;")

        except Exception as e:
            logger.error(f"Error refreshing spots: {e}", exc_info=True)
            self.status_label.setText(f"SKCC Skimmer: Error - {str(e)[:30]}")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")

    def _update_spots_table(self) -> None:
        """Update the spots table with current spots"""
        try:
            self.spots_table.setRowCount(0)

            for spot in reversed(self.spots):  # Most recent first
                try:
                    # Handle both RBNSpot and SKCCSpot objects
                    goal_type = getattr(spot, 'goal_type', None)
                    source_type = getattr(spot, 'source_type', 'RBN')
                    
                    # Filter based on checkbox states
                    if goal_type == "GOAL" and not self.show_goals_check.isChecked():
                        continue
                    if goal_type == "TARGET" and not self.show_targets_check.isChecked():
                        continue
                    if source_type == "RBN" and not self.show_rbn_check.isChecked():
                        continue
                    if source_type == "SKED" and not self.show_sked_check.isChecked():
                        continue

                    row = self.spots_table.rowCount()
                    self.spots_table.insertRow(row)

                    # Callsign
                    callsign = getattr(spot, 'callsign', '')
                    call_item = QTableWidgetItem(str(callsign))
                    if goal_type == "GOAL":
                        call_item.setBackground(QColor(0, 128, 0, 80))  # Green
                    elif goal_type == "TARGET":
                        call_item.setBackground(QColor(0, 0, 255, 80))  # Blue
                    self.spots_table.setItem(row, 0, call_item)

                    # Frequency
                    frequency = getattr(spot, 'frequency', 0)
                    freq_item = QTableWidgetItem(f"{float(frequency):.3f}")
                    self.spots_table.setItem(row, 1, freq_item)

                    # Time
                    timestamp = getattr(spot, 'timestamp', '')
                    if isinstance(timestamp, str):
                        time_str = timestamp[-8:] if len(timestamp) >= 8 else timestamp
                    else:
                        time_str = timestamp.strftime("%H:%M:%S") if timestamp else "N/A"
                    time_item = QTableWidgetItem(time_str)
                    self.spots_table.setItem(row, 2, time_item)

                    # Distance
                    distance = getattr(spot, 'distance', None)
                    dist_item = QTableWidgetItem(
                        f"{float(distance):.0f} km" if distance else "N/A"
                    )
                    self.spots_table.setItem(row, 3, dist_item)

                    # Type
                    type_item = QTableWidgetItem(goal_type or "Other")
                    self.spots_table.setItem(row, 4, type_item)

                    # SNR/WPM
                    snr = getattr(spot, 'snr', None)
                    wpm = getattr(spot, 'wpm', None) or getattr(spot, 'speed', None)
                    snr_wpm = []
                    if snr:
                        snr_wpm.append(f"{int(snr):+d}dB")
                    if wpm:
                        snr_wpm.append(f"{int(wpm)}wpm")
                    snr_wpm_item = QTableWidgetItem(" ".join(snr_wpm) if snr_wpm else "")
                    self.spots_table.setItem(row, 5, snr_wpm_item)

                    # Source (RBN or Sked) - with visual differentiation using text color only
                    source_item = QTableWidgetItem(str(source_type))
                    if source_type == "RBN":
                        # RBN color: bright yellow/orange text (automated skimmers)
                        source_item.setForeground(QColor(255, 180, 0))  # Bright orange text
                    elif source_type == "SKED":
                        # Sked color: bright magenta/purple text (manual SKCC Sked posts)
                        source_item.setForeground(QColor(200, 120, 255))  # Bright magenta text
                    else:
                        # Unknown: lighter gray text
                        source_item.setForeground(QColor(150, 150, 150))
                    self.spots_table.setItem(row, 6, source_item)

                    # Spotter
                    spotter = getattr(spot, 'spotter', '') or getattr(spot, 'reporter', '')
                    spotter_item = QTableWidgetItem(str(spotter))
                    self.spots_table.setItem(row, 7, spotter_item)
                    
                except Exception as e:
                    logger.error(f"Error adding spot row: {e}", exc_info=True)
                    continue
                    
        except Exception as e:
            logger.error(f"Error updating spots table: {e}", exc_info=True)

    def _update_statistics(self) -> None:
        """Update statistics display"""
        try:
            stats = self.integration.get_spot_statistics()
            self.total_spots_label.setText(f"Total Spots: {stats.get('total_spots', 0)}")
            self.unique_calls_label.setText(f"Unique Calls: {stats.get('unique_callsigns', 0)}")
            self.goal_spots_label.setText(f"Goal Spots: {stats.get('goal_spots', 0)}")
            self.target_spots_label.setText(f"Target Spots: {stats.get('target_spots', 0)}")
            self.rbn_spots_label.setText(f"RBN: {stats.get('rbn_spots', 0)}")
            self.sked_spots_label.setText(f"Sked: {stats.get('sked_spots', 0)}")
        except Exception as e:
            logger.error(f"Error updating statistics: {e}", exc_info=True)

    def _on_spot_clicked(self, item) -> None:
        """Handle spot selection"""
        try:
            row = item.row()
            if 0 <= row < len(self.spots):
                spot = list(reversed(self.spots))[row]  # Match table order
                callsign = getattr(spot, 'callsign', None)
                if callsign:
                    self.spot_selected.emit(str(callsign))
                logger.debug(f"Spot selected: {callsign}")
        except Exception as e:
            logger.error(f"Error handling spot click: {e}", exc_info=True)
            logger.debug(f"Spot selected: {spot.callsign}")

    def clear_spots(self) -> None:
        """Clear all spots"""
        self.spots_table.setRowCount(0)
        try:
            self.integration.spots.clear()
            self.integration.spot_statistics = {
                "total_spots": 0,
                "goal_spots": 0,
                "target_spots": 0,
                "rbn_spots": 0,
                "sked_spots": 0,
                "unique_callsigns": set(),
            }
        except Exception:
            # If integration is a stub, ignore errors
            pass
        self._update_statistics()

    def _add_sample_spots(self) -> None:
        """Populate a few sample spots for demonstration when RBN isn't connected."""
        try:
            now = datetime.now(timezone.utc)
            sample = [
                SKCCSpot(callsign="K4TEST", frequency=14.055, mode="CW", grid=None,
                         reporter="TEST", strength=20, speed=22, timestamp=now, is_skcc=True, skcc_number="12345"),
                SKCCSpot(callsign="W1AW", frequency=7.035, mode="CW", grid=None,
                         reporter="TEST", strength=18, speed=25, timestamp=now - timedelta(minutes=2), is_skcc=True, skcc_number="100T"),
            ]
            self.spots.extend(sample)
        except Exception as e:
            logger.debug(f"Failed generating sample spots: {e}")

    def closeEvent(self, event) -> None:
        """Cleanup on close"""
        try:
            self.refresh_timer.stop()
            self.cleanup_timer.stop()
        except Exception as e:
            logger.error(f"Error stopping timers: {e}")
        super().closeEvent(event)
