"""
QRP Miles Per Watt (MPW) Award Progress Widget

Displays QRP MPW award progress - contacts achieving 1000+ miles per watt.
MPW = Distance (miles) / Transmit Power (watts)

Requirements:
- TX Power ≤ 5W
- Distance / Power ≥ 1000 MPW
- Mode = CW
"""

import logging
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from src.database.repository import DatabaseRepository
from src.ui.signals import get_app_signals

logger = logging.getLogger(__name__)

# QRP MPW color (green for low power)
QRP_MPW_COLOR = "#4CAF50"


class QRPMPWProgressWidget(QWidget):
    """Displays QRP Miles Per Watt award progress"""

    def __init__(self, db: DatabaseRepository, parent: Optional[QWidget] = None):
        """
        Initialize QRP MPW progress widget

        Args:
            db: Database repository instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.db = db
        self.qualifying_contacts: List[Dict[str, Any]] = []

        self._init_ui()
        self.refresh()

        # Connect to signals for auto-refresh
        signals = get_app_signals()
        signals.contacts_changed.connect(self.refresh)
        signals.contact_added.connect(self.refresh)
        signals.contact_modified.connect(self.refresh)
        signals.contact_deleted.connect(self.refresh)

    def _init_ui(self) -> None:
        """Initialize UI components"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Overall Progress Section
        progress_group = self._create_progress_section()
        main_layout.addWidget(progress_group)

        # Stats Section
        stats_group = self._create_stats_section()
        main_layout.addWidget(stats_group)

        # Qualifying Contacts Table
        table_group = self._create_table_section()
        main_layout.addWidget(table_group)

        # Actions Section
        actions_group = self._create_actions_section()
        main_layout.addWidget(actions_group)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_progress_section(self) -> QGroupBox:
        """Create overall progress section"""
        group = QGroupBox("QRP Miles Per Watt Progress")
        layout = QVBoxLayout()

        # Description
        desc = QLabel("Contacts achieving 1000+ miles per watt at 5W or less (CW only)")
        desc.setFont(QFont("Arial", 9))
        desc.setStyleSheet("color: #666666;")
        layout.addWidget(desc)

        # Progress summary
        self.progress_label = QLabel("No qualifying contacts yet")
        self.progress_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.progress_label.setStyleSheet(f"color: {QRP_MPW_COLOR};")
        layout.addWidget(self.progress_label)

        # Info label
        self.info_label = QLabel("MPW = Distance (miles) / Power (watts)")
        self.info_label.setFont(QFont("Arial", 9))
        self.info_label.setStyleSheet("color: #999999;")
        layout.addWidget(self.info_label)

        group.setLayout(layout)
        return group

    def _create_stats_section(self) -> QGroupBox:
        """Create statistics section"""
        group = QGroupBox("Statistics")
        layout = QVBoxLayout()

        # Stats grid
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)

        # Total qualifying
        self.total_label = self._create_stat_label("Total Qualifying:", "0")
        stats_layout.addWidget(self.total_label)

        # Best MPW
        self.best_mpw_label = self._create_stat_label("Best MPW:", "0")
        stats_layout.addWidget(self.best_mpw_label)

        # Average MPW
        self.avg_mpw_label = self._create_stat_label("Average MPW:", "0")
        stats_layout.addWidget(self.avg_mpw_label)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        group.setLayout(layout)
        return group

    def _create_stat_label(self, title: str, value: str) -> QGroupBox:
        """Create a stat display box"""
        box = QGroupBox()
        layout = QVBoxLayout()
        layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 8))
        title_label.setStyleSheet("color: #666666;")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        value_label.setStyleSheet(f"color: {QRP_MPW_COLOR};")
        value_label.setObjectName("value")
        layout.addWidget(value_label)

        box.setLayout(layout)
        return box

    def _create_table_section(self) -> QGroupBox:
        """Create qualifying contacts table"""
        group = QGroupBox("Qualifying Contacts (1000+ MPW)")
        layout = QVBoxLayout()

        # Create table
        self.contacts_table = QTableWidget()
        self.contacts_table.setColumnCount(7)
        self.contacts_table.setHorizontalHeaderLabels([
            "Date", "Callsign", "Band", "Distance (mi)", "Power (W)", "MPW", "SKCC"
        ])

        # Configure table
        header = self.contacts_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Date
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Callsign
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Band
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Distance
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Power
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # MPW
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # SKCC

        self.contacts_table.setAlternatingRowColors(True)
        self.contacts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.contacts_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.contacts_table.setMinimumHeight(300)

        layout.addWidget(self.contacts_table)

        group.setLayout(layout)
        return group

    def _create_actions_section(self) -> QGroupBox:
        """Create actions section"""
        group = QGroupBox("Actions")
        layout = QHBoxLayout()

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn)

        # Export button (placeholder for future)
        export_btn = QPushButton("Export MPW Report")
        export_btn.setEnabled(False)  # Not implemented yet
        export_btn.setToolTip("Feature coming soon")
        layout.addWidget(export_btn)

        layout.addStretch()

        group.setLayout(layout)
        return group

    def refresh(self) -> None:
        """Refresh MPW progress data"""
        try:
            logger.debug("Refreshing QRP MPW progress")

            # Get qualifying contacts from database
            self.qualifying_contacts = self.db.calculate_mpw_qualifications()

            # Update progress label
            count = len(self.qualifying_contacts)
            if count == 0:
                self.progress_label.setText("No qualifying contacts yet")
                self.progress_label.setStyleSheet("color: #999999;")
            elif count == 1:
                self.progress_label.setText("1 qualifying contact!")
                self.progress_label.setStyleSheet(f"color: {QRP_MPW_COLOR}; font-weight: bold;")
            else:
                self.progress_label.setText(f"{count} qualifying contacts!")
                self.progress_label.setStyleSheet(f"color: {QRP_MPW_COLOR}; font-weight: bold;")

            # Update statistics
            self._update_stats()

            # Update table
            self._populate_table()

            logger.info(f"QRP MPW progress refreshed: {count} qualifying contacts")

        except Exception as e:
            logger.error(f"Error refreshing QRP MPW progress: {e}", exc_info=True)
            self.progress_label.setText("Error loading data")
            self.progress_label.setStyleSheet("color: #f44336;")

    def _update_stats(self) -> None:
        """Update statistics display"""
        try:
            count = len(self.qualifying_contacts)

            # Find value labels in stat boxes
            total_box = self.total_label
            best_box = self.best_mpw_label
            avg_box = self.avg_mpw_label

            # Update total
            value_label = total_box.findChild(QLabel, "value")
            if value_label:
                value_label.setText(str(count))

            if count > 0:
                # Calculate best and average MPW
                mpw_values = [c['mpw'] for c in self.qualifying_contacts]
                best_mpw = max(mpw_values)
                avg_mpw = sum(mpw_values) / len(mpw_values)

                # Update best MPW
                value_label = best_box.findChild(QLabel, "value")
                if value_label:
                    value_label.setText(f"{best_mpw:,.0f}")

                # Update average MPW
                value_label = avg_box.findChild(QLabel, "value")
                if value_label:
                    value_label.setText(f"{avg_mpw:,.0f}")
            else:
                # Reset to zero
                value_label = best_box.findChild(QLabel, "value")
                if value_label:
                    value_label.setText("0")

                value_label = avg_box.findChild(QLabel, "value")
                if value_label:
                    value_label.setText("0")

        except Exception as e:
            logger.error(f"Error updating MPW stats: {e}", exc_info=True)

    def _populate_table(self) -> None:
        """Populate qualifying contacts table"""
        try:
            self.contacts_table.setRowCount(0)

            if not self.qualifying_contacts:
                return

            # Sort by MPW descending (best first)
            sorted_contacts = sorted(self.qualifying_contacts, key=lambda x: x['mpw'], reverse=True)

            self.contacts_table.setRowCount(len(sorted_contacts))

            for row, contact in enumerate(sorted_contacts):
                # Date
                date_item = QTableWidgetItem(self._format_date(contact['date']))
                date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.contacts_table.setItem(row, 0, date_item)

                # Callsign
                callsign_item = QTableWidgetItem(contact['callsign'])
                callsign_item.setFont(QFont("Courier", 10, QFont.Weight.Bold))
                callsign_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.contacts_table.setItem(row, 1, callsign_item)

                # Band
                band_item = QTableWidgetItem(contact['band'])
                band_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.contacts_table.setItem(row, 2, band_item)

                # Distance (convert km to miles if needed)
                distance_miles = contact['distance_miles']
                distance_item = QTableWidgetItem(f"{distance_miles:,.0f}")
                distance_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.contacts_table.setItem(row, 3, distance_item)

                # Power
                power_item = QTableWidgetItem(f"{contact['tx_power']:.1f}")
                power_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.contacts_table.setItem(row, 4, power_item)

                # MPW (highlighted)
                mpw = contact['mpw']
                mpw_item = QTableWidgetItem(f"{mpw:,.0f}")
                mpw_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                mpw_item.setForeground(QColor(QRP_MPW_COLOR))
                mpw_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.contacts_table.setItem(row, 5, mpw_item)

                # SKCC Number
                skcc = contact.get('skcc_number', '')
                skcc_item = QTableWidgetItem(str(skcc) if skcc else '')
                skcc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.contacts_table.setItem(row, 6, skcc_item)

        except Exception as e:
            logger.error(f"Error populating MPW table: {e}", exc_info=True)

    def _format_date(self, date_str: str) -> str:
        """Format ADIF date (YYYYMMDD) for display"""
        try:
            if not date_str or len(date_str) != 8:
                return date_str

            year = date_str[0:4]
            month = date_str[4:6]
            day = date_str[6:8]
            return f"{year}-{month}-{day}"

        except Exception:
            return date_str
