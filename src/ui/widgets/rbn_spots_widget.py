"""
RBN Spots Widget for SKCC Skimmer Integration

Displays real-time Reverse Beacon Network spots from SKCC Skimmer with
award relevance information.
"""

import logging
from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QSpinBox, QCheckBox, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor

from src.integrations.skcc_skimmer import RBNSpot

logger = logging.getLogger(__name__)


class RBNSpotsWidget(QWidget):
    """
    Widget for displaying RBN spots from SKCC Skimmer

    Shows:
    - Callsign
    - Frequency
    - Time spotted
    - Distance (if grid square available)
    - Relevance (GOAL/TARGET/BOTH)
    - SNR/WPM
    """

    spot_selected = pyqtSignal(str)  # Emits callsign when spot is clicked

    def __init__(self, integration, config_manager, db, parent=None):
        """
        Initialize RBN Spots Widget

        Args:
            integration: SKCCSkimmerIntegration instance
            config_manager: Configuration manager
            db: Database repository
            parent: Parent widget
        """
        super().__init__(parent)
        self.integration = integration
        self.config_manager = config_manager
        self.db = db
        self.spots: List[RBNSpot] = []

        self._init_ui()
        self._setup_auto_refresh()

    def _init_ui(self) -> None:
        """Initialize UI components"""
        main_layout = QVBoxLayout()

        # Status bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("SKCC Skimmer: Not Connected")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        # Controls
        refresh_btn = QPushButton("Refresh Spots")
        refresh_btn.clicked.connect(self.refresh_spots)
        status_layout.addWidget(refresh_btn)

        clear_btn = QPushButton("Clear Spots")
        clear_btn.clicked.connect(self.clear_spots)
        status_layout.addWidget(clear_btn)

        main_layout.addLayout(status_layout)

        # Spots table
        self.spots_table = QTableWidget()
        self.spots_table.setColumnCount(7)
        self.spots_table.setHorizontalHeaderLabels([
            "Callsign", "Frequency", "Time", "Distance", "Type", "SNR/WPM", "Spotter"
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

        stats_layout.addWidget(self.total_spots_label)
        stats_layout.addWidget(self.unique_calls_label)
        stats_layout.addWidget(self.goal_spots_label)
        stats_layout.addWidget(self.target_spots_label)
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

        options_layout.addStretch()
        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)

        self.setLayout(main_layout)

    def _setup_auto_refresh(self) -> None:
        """Setup auto-refresh timer"""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_spots)
        self.refresh_timer.start(10000)  # Start at 10 seconds

    def refresh_spots(self) -> None:
        """Refresh spots from integration"""
        try:
            if not self.integration.is_available():
                self.status_label.setText("SKCC Skimmer: Not Installed")
                self.status_label.setStyleSheet("color: red; font-weight: bold;")
                return

            # Get recent spots
            self.spots = self.integration.get_recent_spots(limit=50)

            # Update table
            self._update_spots_table()

            # Update statistics
            self._update_statistics()

            # Update status
            spot_count = len(self.spots)
            self.status_label.setText(
                f"SKCC Skimmer: Connected ({spot_count} recent spots)"
            )
            self.status_label.setStyleSheet("color: green; font-weight: bold;")

        except Exception as e:
            logger.error(f"Error refreshing spots: {e}", exc_info=True)
            self.status_label.setText(f"SKCC Skimmer: Error - {str(e)[:30]}")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")

    def _update_spots_table(self) -> None:
        """Update the spots table with current spots"""
        self.spots_table.setRowCount(0)

        for spot in reversed(self.spots):  # Most recent first
            # Filter based on checkbox states
            if spot.goal_type == "GOAL" and not self.show_goals_check.isChecked():
                continue
            if spot.goal_type == "TARGET" and not self.show_targets_check.isChecked():
                continue

            row = self.spots_table.rowCount()
            self.spots_table.insertRow(row)

            # Callsign
            call_item = QTableWidgetItem(spot.callsign)
            if spot.goal_type == "GOAL":
                call_item.setBackground(QColor(0, 128, 0, 80))  # Green
            elif spot.goal_type == "TARGET":
                call_item.setBackground(QColor(0, 0, 255, 80))  # Blue
            self.spots_table.setItem(row, 0, call_item)

            # Frequency
            freq_item = QTableWidgetItem(f"{spot.frequency:.3f}")
            self.spots_table.setItem(row, 1, freq_item)

            # Time
            time_item = QTableWidgetItem(spot.timestamp[-8:])  # HH:MM:SS
            self.spots_table.setItem(row, 2, time_item)

            # Distance
            dist_item = QTableWidgetItem(
                f"{spot.distance:.0f} km" if spot.distance else "N/A"
            )
            self.spots_table.setItem(row, 3, dist_item)

            # Type
            type_item = QTableWidgetItem(spot.goal_type or "Other")
            self.spots_table.setItem(row, 4, type_item)

            # SNR/WPM
            snr_wpm = []
            if spot.snr:
                snr_wpm.append(f"{spot.snr:+d}dB")
            if spot.wpm:
                snr_wpm.append(f"{spot.wpm}wpm")
            snr_wpm_item = QTableWidgetItem(" ".join(snr_wpm) if snr_wpm else "")
            self.spots_table.setItem(row, 5, snr_wpm_item)

            # Spotter
            spotter_item = QTableWidgetItem(spot.spotter)
            self.spots_table.setItem(row, 6, spotter_item)

    def _update_statistics(self) -> None:
        """Update statistics display"""
        stats = self.integration.get_spot_statistics()
        self.total_spots_label.setText(f"Total Spots: {stats['total_spots']}")
        self.unique_calls_label.setText(f"Unique Calls: {stats['unique_callsigns']}")
        self.goal_spots_label.setText(f"Goal Spots: {stats['goal_spots']}")
        self.target_spots_label.setText(f"Target Spots: {stats['target_spots']}")

    def _on_spot_clicked(self, item) -> None:
        """Handle spot selection"""
        row = item.row()
        if 0 <= row < len(self.spots):
            spot = list(reversed(self.spots))[row]  # Match table order
            self.spot_selected.emit(spot.callsign)
            logger.debug(f"Spot selected: {spot.callsign}")

    def clear_spots(self) -> None:
        """Clear all spots"""
        self.spots_table.setRowCount(0)
        self.integration.spots.clear()
        self.integration.spot_statistics = {
            "total_spots": 0,
            "goal_spots": 0,
            "target_spots": 0,
            "unique_callsigns": set(),
        }
        self._update_statistics()

    def closeEvent(self, event) -> None:
        """Cleanup on close"""
        self.refresh_timer.stop()
        super().closeEvent(event)
