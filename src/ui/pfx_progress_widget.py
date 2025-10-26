"""
SKCC PFX Award Progress Widget

Displays PFX award progress tracking unique callsign prefixes and accumulated points.
Points are based on the sum of SKCC numbers for each unique prefix.
When multiple stations share a prefix, only the highest SKCC number counts.
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
from src.awards.pfx import PFXAward
from src.ui.signals import get_app_signals

logger = logging.getLogger(__name__)

# PFX color (dark purple)
PFX_COLOR = "#663399"


class PFXProgressWidget(QWidget):
    """Displays SKCC PFX award progress with prefix tracking and points"""

    def __init__(self, db: DatabaseRepository, parent: Optional[QWidget] = None):
        """
        Initialize PFX progress widget

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

        # Prefix Details Section
        prefix_group = self._create_prefix_section()
        main_layout.addWidget(prefix_group)

        # Statistics Section
        stats_group = self._create_stats_section()
        main_layout.addWidget(stats_group)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_progress_section(self) -> QGroupBox:
        """Create overall progress section"""
        group = QGroupBox("PFX Progress")
        layout = QVBoxLayout()

        # Description
        desc = QLabel(
            "Sum of SKCC numbers for each unique prefix\n"
            "(Multiple stations per prefix: only highest SKCC number counts)"
        )
        desc.setFont(QFont("Arial", 9))
        desc.setStyleSheet("color: #666666;")
        layout.addWidget(desc)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(500000)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v points")
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                height: 28px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {PFX_COLOR};
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

        # Endorsement levels
        endorsement_levels = [
            (500000, "PFX"),
            (1000000, "PFX x2"),
            (1500000, "PFX x3"),
            (2000000, "PFX x4"),
            (2500000, "PFX x5"),
            (3000000, "PFX x6"),
            (3500000, "PFX x7"),
            (4000000, "PFX x8"),
            (4500000, "PFX x9"),
            (5000000, "PFX x10"),
            (7500000, "PFX x15"),
            (10000000, "PFX x20"),
        ]

        self.endorsement_labels = []

        for i, (points, name) in enumerate(endorsement_levels):
            label = QLabel(f"☐ {name} ({points:,} pts)")
            label.setFont(QFont("Arial", 9))
            self.endorsement_labels.append((points, label))

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

    def _create_prefix_section(self) -> QGroupBox:
        """Create prefix details section"""
        group = QGroupBox("Top Prefixes by Points")
        layout = QVBoxLayout()

        # Table for prefix progress
        self.prefix_table = QTableWidget()
        self.prefix_table.setColumnCount(3)
        self.prefix_table.setHorizontalHeaderLabels(["Prefix", "Highest SKCC#", "Points"])
        self.prefix_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.prefix_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.prefix_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.prefix_table.setMaximumHeight(250)

        layout.addWidget(self.prefix_table)

        group.setLayout(layout)
        return group

    def _create_stats_section(self) -> QGroupBox:
        """Create statistics section"""
        group = QGroupBox("Statistics")
        layout = QVBoxLayout()
        layout.setSpacing(6)

        # Stats labels
        stats_layout = QHBoxLayout()

        self.prefixes_label = QLabel("Unique Prefixes: 0")
        self.prefixes_label.setFont(QFont("Arial", 9))
        stats_layout.addWidget(self.prefixes_label)

        self.contacts_label = QLabel("Total Contacts: 0")
        self.contacts_label.setFont(QFont("Arial", 9))
        stats_layout.addWidget(self.contacts_label)

        self.avg_points_label = QLabel("Average Points/Prefix: 0")
        self.avg_points_label.setFont(QFont("Arial", 9))
        stats_layout.addWidget(self.avg_points_label)

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
            contact_dicts = [self._contact_to_dict(c) for c in contacts]
            session.close()

            # Calculate PFX progress
            pfx_award = PFXAward(session)
            progress = pfx_award.calculate_progress(contact_dicts)

            current_points = progress['current']
            required = progress['required']
            level = progress['level']

            # Update main progress bar
            self.progress_bar.setMaximum(max(500000, required))
            self.progress_bar.setValue(current_points)

            # Update status label
            self.status_label.setText(
                f"{level} • {current_points:,} points • {progress['unique_prefixes']} unique prefixes"
            )

            # Update endorsement levels
            self._update_endorsement_display(current_points)

            # Update prefix table
            self._update_prefix_table(progress['prefix_points'], progress['skcc_per_prefix'])

            # Update statistics
            self.prefixes_label.setText(f"Unique Prefixes: {progress['unique_prefixes']}")
            self.contacts_label.setText(f"Total Contacts: {progress['total_contacts']}")

            avg_points = (
                current_points // progress['unique_prefixes']
                if progress['unique_prefixes'] > 0
                else 0
            )
            self.avg_points_label.setText(f"Average Points/Prefix: {avg_points:,}")

        except Exception as e:
            logger.error(f"Error refreshing PFX progress: {e}", exc_info=True)
            self.status_label.setText(f"Error: {str(e)}")

    def _update_endorsement_display(self, points: int) -> None:
        """Update endorsement level visual indicators

        Args:
            points: Current accumulated points
        """
        for level_points, label in self.endorsement_labels:
            if points >= level_points:
                # Achieved
                label.setText(label.text().replace("☐", "☑"))
                label.setStyleSheet(f"color: {PFX_COLOR}; font-weight: bold;")
            else:
                # Not achieved
                label.setText(label.text().replace("☑", "☐"))
                label.setStyleSheet("color: #666666;")

    def _update_prefix_table(self, prefix_points: dict, skcc_per_prefix: dict) -> None:
        """Update prefix progress table

        Args:
            prefix_points: Dictionary of prefix -> points
            skcc_per_prefix: Dictionary of prefix -> highest SKCC number
        """
        # Sort by points descending
        sorted_prefixes = sorted(prefix_points.items(), key=lambda x: x[1], reverse=True)

        self.prefix_table.setRowCount(0)

        for prefix, points in sorted_prefixes[:20]:  # Top 20 prefixes
            row = self.prefix_table.rowCount()
            self.prefix_table.insertRow(row)

            # Prefix name
            prefix_item = QTableWidgetItem(prefix)
            prefix_item.setFont(QFont("Arial", 9))
            self.prefix_table.setItem(row, 0, prefix_item)

            # Highest SKCC number for this prefix
            highest_skcc = skcc_per_prefix.get(prefix, 0)
            skcc_item = QTableWidgetItem(str(highest_skcc))
            skcc_item.setFont(QFont("Arial", 9))
            self.prefix_table.setItem(row, 1, skcc_item)

            # Points for this prefix
            points_item = QTableWidgetItem(f"{points:,}")
            points_item.setFont(QFont("Arial", 9))
            points_item.setForeground(QColor(PFX_COLOR))
            self.prefix_table.setItem(row, 2, points_item)

    def _contact_to_dict(self, contact) -> dict:
        """Convert Contact ORM object to dictionary"""
        return {
            'callsign': contact.callsign,
            'mode': contact.mode,
            'band': contact.band,
            'qso_date': contact.qso_date,
            'qso_time': contact.qso_time,
            'skcc_number': contact.skcc_number,
            'key_type': contact.key_type,
        }
