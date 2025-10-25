"""
SKCC Centurion Award Progress Widget

Displays Centurion award progress with visual progress bars and endorsement levels.
The Centurion list is automatically synced daily from SKCC.
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QProgressBar, QTableWidget,
    QTableWidgetItem, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from src.database.repository import DatabaseRepository
from src.services.centurion_fetcher import CenturionFetcher

logger = logging.getLogger(__name__)

# SKCC Orange color
SKCC_ORANGE = "#FF6B35"


class CenturionProgressWidget(QWidget):
    """Displays SKCC Centurion award progress with auto-updating member list"""

    def __init__(self, db: DatabaseRepository, parent: Optional[QWidget] = None):
        """
        Initialize Centurion progress widget

        Args:
            db: Database repository instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.db = db

        self._init_ui()

        # Auto-refresh every 10 seconds
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(10000)

        # Auto-update Centurion list daily
        self.update_list_timer = QTimer()
        self.update_list_timer.timeout.connect(self._update_centurion_list)
        self.update_list_timer.start(3600000)  # Every hour, check if update needed

        # Initial refresh
        self.refresh()
        self._update_centurion_list()

    def _init_ui(self) -> None:
        """Initialize UI components"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Centurion Progress Section
        centurion_group = self._create_centurion_section()
        main_layout.addWidget(centurion_group)

        # Endorsements Section
        endorsement_group = self._create_endorsement_section()
        main_layout.addWidget(endorsement_group)

        # List Status Section
        status_group = self._create_status_section()
        main_layout.addWidget(status_group)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_centurion_section(self) -> QGroupBox:
        """Create Centurion award progress section"""
        group = QGroupBox("Centurion Award Progress")
        layout = QVBoxLayout()

        # Progress bar with SKCC orange color
        self.centurion_progress = QProgressBar()
        self.centurion_progress.setMaximum(100)
        self.centurion_progress.setValue(0)
        self.centurion_progress.setTextVisible(True)
        self.centurion_progress.setFormat("%v / 100 SKCC Members")
        self.centurion_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                height: 28px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {SKCC_ORANGE};
                border-radius: 3px;
            }}
        """)

        layout.addWidget(self.centurion_progress)

        # Status label
        self.status_label = QLabel("Loading...")
        self.status_label.setFont(QFont("Arial", 10))
        layout.addWidget(self.status_label)

        group.setLayout(layout)
        return group

    def _create_endorsement_section(self) -> QGroupBox:
        """Create endorsement levels checklist section"""
        group = QGroupBox("Endorsement Levels")
        layout = QVBoxLayout()
        layout.setSpacing(3)

        # Create label rows for each endorsement level
        self.endorsement_labels = []

        endorsement_levels = [
            (100, "Centurion"),
            (200, "Centurion x2"),
            (300, "Centurion x3"),
            (400, "Centurion x4"),
            (500, "Centurion x5"),
            (600, "Centurion x6"),
            (700, "Centurion x7"),
            (800, "Centurion x8"),
            (900, "Centurion x9"),
            (1000, "Centurion x10"),
            (1500, "Centurion x15"),
            (2000, "Centurion x20"),
        ]

        # Create 2-column layout for endorsements
        endorsement_container = QWidget()
        endorsement_layout = QHBoxLayout()
        endorsement_layout.setSpacing(20)

        # Left column
        left_column = QVBoxLayout()
        left_column.setSpacing(3)

        # Right column
        right_column = QVBoxLayout()
        right_column.setSpacing(3)

        for i, (count, name) in enumerate(endorsement_levels):
            label = QLabel(f"☐ {name} ({count})")
            label.setFont(QFont("Arial", 9))
            self.endorsement_labels.append((count, label))

            if i < len(endorsement_levels) // 2:
                left_column.addWidget(label)
            else:
                right_column.addWidget(label)

        endorsement_layout.addLayout(left_column)
        endorsement_layout.addLayout(right_column)
        endorsement_layout.addStretch()
        layout.addLayout(endorsement_layout)

        group.setLayout(layout)
        return group

    def _create_status_section(self) -> QGroupBox:
        """Create Centurion list status section"""
        group = QGroupBox("Member List Status")
        layout = QVBoxLayout()

        # Status information
        status_layout = QHBoxLayout()

        self.list_status_label = QLabel("Member list: Unknown")
        self.list_status_label.setFont(QFont("Arial", 9))
        status_layout.addWidget(self.list_status_label)

        # Manual refresh button
        refresh_btn = QPushButton("Update List Now")
        refresh_btn.setMaximumWidth(120)
        refresh_btn.clicked.connect(self._manual_update_centurion_list)
        status_layout.addWidget(refresh_btn)

        status_layout.addStretch()
        layout.addLayout(status_layout)

        group.setLayout(layout)
        return group

    def refresh(self) -> None:
        """Refresh award progress from database"""
        try:
            progress = self.db.analyze_centurion_award_progress()

            member_count = progress['unique_members']
            endorsement = progress['endorsement']
            next_level = progress['next_level']
            members_to_next = progress['members_to_next']

            # Update progress bar
            self.centurion_progress.setMaximum(next_level)
            self.centurion_progress.setValue(member_count)

            # Update status label
            if member_count >= 100:
                status_text = f"{endorsement} • {member_count} members • {members_to_next} more to {next_level}"
            else:
                status_text = f"Progress: {member_count}/100 members • {100 - member_count} more to Centurion"

            self.status_label.setText(status_text)

            # Update endorsement checkboxes
            self._update_endorsement_display(member_count)

        except Exception as e:
            logger.error(f"Error refreshing Centurion progress: {e}")
            self.status_label.setText(f"Error: {str(e)}")

    def _update_endorsement_display(self, member_count: int) -> None:
        """Update endorsement level visual indicators

        Args:
            member_count: Current number of unique SKCC members contacted
        """
        for level, label in self.endorsement_labels:
            if member_count >= level:
                # Achieved - show checkmark
                label.setText(label.text().replace("☐", "☑"))
                label.setStyleSheet(f"color: {SKCC_ORANGE}; font-weight: bold;")
            else:
                # Not achieved - show empty box
                label.setText(label.text().replace("☑", "☐"))
                label.setStyleSheet("color: #666666;")

    def _update_centurion_list(self) -> None:
        """Update Centurion member list from SKCC if needed"""
        try:
            session = self.db.get_session()
            success = CenturionFetcher.refresh_centurion_list(session, force=False)
            session.close()

            if success:
                member_count = CenturionFetcher.get_centurion_member_count(session)
                self.list_status_label.setText(f"✓ Member list updated • {member_count} on record")
                logger.info(f"Centurion list refreshed: {member_count} members")
            else:
                self.list_status_label.setText("Member list update failed")

        except Exception as e:
            logger.error(f"Error updating Centurion list: {e}")
            self.list_status_label.setText(f"Error updating list: {str(e)}")

    def _manual_update_centurion_list(self) -> None:
        """Manually trigger Centurion list update"""
        try:
            self.list_status_label.setText("Updating member list...")

            session = self.db.get_session()
            success = CenturionFetcher.refresh_centurion_list(session, force=True)
            session.close()

            if success:
                member_count = CenturionFetcher.get_centurion_member_count(session)
                self.list_status_label.setText(f"✓ List updated • {member_count} members")
                logger.info(f"Manual Centurion list update: {member_count} members")
            else:
                self.list_status_label.setText("Update failed - check network connection")

        except Exception as e:
            logger.error(f"Error in manual Centurion list update: {e}")
            self.list_status_label.setText(f"Update error: {str(e)}")

    def closeEvent(self, event):
        """Cleanup timers on close"""
        self.refresh_timer.stop()
        self.update_list_timer.stop()
        super().closeEvent(event)
