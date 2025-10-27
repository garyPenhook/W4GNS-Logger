"""
SKCC Rag Chew Award Progress Widget

Displays Rag Chew award progress tracking cumulative duration of CW conversations.
Base Award: 300 minutes
Endorsements: Every 300 minutes up to x10 (3000 min), then 5-minute increments.
Single-band endorsements also tracked separately.
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from src.database.repository import DatabaseRepository
from src.awards.rag_chew import RagChewAward
from src.ui.signals import get_app_signals

logger = logging.getLogger(__name__)

# Rag Chew color (purple)
RAG_CHEW_COLOR = "#9C27B0"


class RagChewProgressWidget(QWidget):
    """Displays SKCC Rag Chew award progress with duration tracking"""

    def __init__(self, db: DatabaseRepository, parent: Optional[QWidget] = None):
        """
        Initialize Rag Chew progress widget

        Args:
            db: Database repository instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.db = db

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

        # Endorsement Levels Section
        endorsement_group = self._create_endorsement_section()
        main_layout.addWidget(endorsement_group)

        # Single-Band Progress Section
        band_group = self._create_band_section()
        main_layout.addWidget(band_group)

        # Stats Section
        stats_group = self._create_stats_section()
        main_layout.addWidget(stats_group)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_progress_section(self) -> QGroupBox:
        """Create overall progress section"""
        group = QGroupBox("Rag Chew Progress")
        layout = QVBoxLayout()

        # Description
        desc = QLabel("Cumulative CW conversation time with SKCC members (30+ min per QSO)")
        desc.setFont(QFont("Arial", 9))
        desc.setStyleSheet("color: #666666;")
        layout.addWidget(desc)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(300)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v minutes")
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                height: 28px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {RAG_CHEW_COLOR};
                border-radius: 3px;
            }}
        """)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Loading...")
        self.status_label.setFont(QFont("Arial", 10))
        layout.addWidget(self.status_label)

        group.setLayout(layout)
        return group

    def _create_endorsement_section(self) -> QGroupBox:
        """Create endorsement levels section"""
        group = QGroupBox("Award Levels")
        layout = QVBoxLayout()
        layout.setSpacing(3)

        # Create 2-column layout for endorsements
        container = QWidget()
        h_layout = QHBoxLayout()
        h_layout.setSpacing(20)

        # Left column
        left_layout = QVBoxLayout()
        left_layout.setSpacing(3)

        # Right column
        right_layout = QVBoxLayout()
        right_layout.setSpacing(3)

        # Endorsement levels: up to x10, then variable
        endorsement_levels = [
            (300, "Rag Chew"),
            (600, "Rag Chew x2"),
            (900, "Rag Chew x3"),
            (1200, "Rag Chew x4"),
            (1500, "Rag Chew x5"),
            (1800, "Rag Chew x6"),
            (2100, "Rag Chew x7"),
            (2400, "Rag Chew x8"),
            (2700, "Rag Chew x9"),
            (3000, "Rag Chew x10"),
            (4500, "Rag Chew x15"),
            (6000, "Rag Chew x20"),
        ]

        self.endorsement_labels = []

        for i, (minutes, name) in enumerate(endorsement_levels):
            label = QLabel(f"☐ {name} ({minutes}m)")
            label.setFont(QFont("Arial", 9))
            self.endorsement_labels.append((minutes, label))

            if i < len(endorsement_levels) // 2:
                left_layout.addWidget(label)
            else:
                right_layout.addWidget(label)

        h_layout.addLayout(left_layout)
        h_layout.addLayout(right_layout)
        h_layout.addStretch()
        layout.addLayout(h_layout)

        group.setLayout(layout)
        return group

    def _create_band_section(self) -> QGroupBox:
        """Create single-band progress section"""
        group = QGroupBox("Single-Band Endorsements (300 minutes per band)")
        layout = QVBoxLayout()

        # Table for band progress
        self.band_table = QTableWidget()
        self.band_table.setColumnCount(3)
        self.band_table.setHorizontalHeaderLabels(["Band", "Minutes", "Status"])
        self.band_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.band_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.band_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.band_table.setMaximumHeight(200)

        layout.addWidget(self.band_table)

        group.setLayout(layout)
        return group

    def _create_stats_section(self) -> QGroupBox:
        """Create statistics section"""
        group = QGroupBox("Statistics")
        layout = QVBoxLayout()
        layout.setSpacing(6)

        # Stats labels
        stats_layout = QHBoxLayout()

        self.total_contacts_label = QLabel("Total Contacts: 0")
        self.total_contacts_label.setFont(QFont("Arial", 9))
        stats_layout.addWidget(self.total_contacts_label)

        self.bands_worked_label = QLabel("Bands: 0")
        self.bands_worked_label.setFont(QFont("Arial", 9))
        stats_layout.addWidget(self.bands_worked_label)

        self.rejected_label = QLabel("Back-to-Back Rejected: 0")
        self.rejected_label.setFont(QFont("Arial", 9))
        self.rejected_label.setStyleSheet("color: #d32f2f;")
        stats_layout.addWidget(self.rejected_label)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        group.setLayout(layout)
        return group

    def refresh(self) -> None:
        """Refresh award progress from database"""
        try:
            session = self.db.get_session()

            # Get all contacts
            from src.database.models import Contact
            contacts = session.query(Contact).all()
            logger.info(f"Rag Chew Award: Fetched {len(contacts)} total contacts from database")
            contact_dicts = [self._contact_to_dict(c) for c in contacts]
            logger.debug(f"Rag Chew Award: Converted {len(contact_dicts)} contacts to dict format")

            # Keep session open - award class may need it
            # session.close()  # REMOVED: Session closed too early

            # Calculate Rag Chew progress
            rag_chew = RagChewAward(session)
            progress = rag_chew.calculate_progress(contact_dicts)

            current_minutes = progress['current_minutes']
            required = progress['required']
            level = progress['level']

            # Update main progress bar
            self.progress_bar.setMaximum(max(300, required))
            self.progress_bar.setValue(current_minutes)

            # Update status label
            self.status_label.setText(
                f"{level} • {current_minutes} minutes accumulated • {progress['total_contacts']} qualifying QSOs"
            )

            # Update endorsement levels
            self._update_endorsement_display(current_minutes)

            # Update band progress table
            self._update_band_progress(progress['band_progress'])

            # Update statistics
            self.total_contacts_label.setText(f"Total Contacts: {progress['total_contacts']}")
            self.bands_worked_label.setText(f"Bands: {progress['bands_worked']}")
            self.rejected_label.setText(f"Back-to-Back Rejected: {progress['back_to_back_rejected']}")

        except Exception as e:
            logger.error(f"Error refreshing Rag Chew progress: {e}", exc_info=True)
            self.status_label.setText(f"Error: {str(e)}")

    def _update_endorsement_display(self, minutes: int) -> None:
        """Update endorsement level visual indicators

        Args:
            minutes: Current accumulated minutes
        """
        for level_minutes, label in self.endorsement_labels:
            if minutes >= level_minutes:
                # Achieved
                label.setText(label.text().replace("☐", "☑"))
                label.setStyleSheet(f"color: {RAG_CHEW_COLOR}; font-weight: bold;")
            else:
                # Not achieved
                label.setText(label.text().replace("☑", "☐"))
                label.setStyleSheet("color: #666666;")

    def _update_band_progress(self, band_progress: dict) -> None:
        """Update band progress table

        Args:
            band_progress: Dictionary of band progress data
        """
        self.band_table.setRowCount(0)

        for band, data in sorted(band_progress.items()):
            row = self.band_table.rowCount()
            self.band_table.insertRow(row)

            # Band name
            band_item = QTableWidgetItem(band)
            band_item.setFont(QFont("Arial", 9))
            self.band_table.setItem(row, 0, band_item)

            # Minutes
            minutes_item = QTableWidgetItem(f"{data['current']}m")
            minutes_item.setFont(QFont("Arial", 9))
            self.band_table.setItem(row, 1, minutes_item)

            # Status
            if data['achieved']:
                status_text = "✓ Base Award"
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(QColor(RAG_CHEW_COLOR))
                status_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            else:
                remaining = data['required'] - data['current']
                status_text = f"{remaining}m to base"
                status_item = QTableWidgetItem(status_text)
                status_item.setFont(QFont("Arial", 9))

            self.band_table.setItem(row, 2, status_item)

    def _calculate_duration(self, time_on: str, time_off: str) -> Optional[int]:
        """
        Calculate QSO duration in minutes from time_on and time_off (HHMM format)

        Args:
            time_on: Start time in HHMM format (e.g., "1430")
            time_off: End time in HHMM format (e.g., "1500")

        Returns:
            Duration in minutes, or None if calculation fails
        """
        try:
            if not time_on or not time_off:
                return None

            # Parse HHMM format
            on_hours = int(time_on[:2])
            on_minutes = int(time_on[2:4])
            off_hours = int(time_off[:2])
            off_minutes = int(time_off[2:4])

            # Convert to total minutes since midnight
            on_total = on_hours * 60 + on_minutes
            off_total = off_hours * 60 + off_minutes

            # Calculate duration
            if off_total >= on_total:
                # Same day
                duration = off_total - on_total
            else:
                # Wrapped to next day (e.g., 2300 to 0030)
                duration = (1440 - on_total) + off_total  # 1440 = 24 * 60 minutes

            # Return duration in minutes (minimum 0)
            return max(0, duration)
        except (ValueError, IndexError):
            logger.debug(f"Failed to calculate duration from {time_on} to {time_off}")
            return None

    def _contact_to_dict(self, contact) -> dict:
        """Convert Contact ORM object to dictionary"""
        # Calculate duration from time_on and time_off
        duration = None
        if contact.time_on and contact.time_off:
            duration = self._calculate_duration(contact.time_on, contact.time_off)

        return {
            'callsign': contact.callsign,
            'mode': contact.mode,
            'band': contact.band,
            'qso_date': contact.qso_date,
            'qso_time': contact.time_on,
            'skcc_number': contact.skcc_number,
            'key_type': contact.key_type,
            'duration': duration,
        }
