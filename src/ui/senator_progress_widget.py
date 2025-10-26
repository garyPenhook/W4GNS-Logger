"""
SKCC Senator Award Progress Widget

Displays Senator award progress with visual progress bars and endorsement levels.
The Senator list is automatically synced daily from SKCC.
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QProgressBar, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from src.database.repository import DatabaseRepository
from src.services.senator_fetcher import SenatorFetcher
from src.ui.signals import get_app_signals

logger = logging.getLogger(__name__)

# Senator color (dark purple)
SENATOR_COLOR = "#6B2C91"


class SenatorProgressWidget(QWidget):
    """Displays SKCC Senator award progress with auto-updating member list"""

    def __init__(self, db: DatabaseRepository, parent: Optional[QWidget] = None):
        """
        Initialize Senator progress widget

        Args:
            db: Database repository instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.db = db

        self._init_ui()
        self.refresh()

        # Connect to signals instead of polling timer for refresh
        signals = get_app_signals()
        signals.contacts_changed.connect(self.refresh)
        signals.contact_added.connect(self.refresh)
        signals.contact_modified.connect(self.refresh)
        signals.contact_deleted.connect(self.refresh)

        # Auto-update Senator list daily (keep as scheduled timer)
        self.update_list_timer = QTimer()
        self.update_list_timer.timeout.connect(self._update_senator_list)
        self.update_list_timer.start(3600000)  # Every hour, check if update needed

        # Initial update of Senator list
        self._update_senator_list()

    def _init_ui(self) -> None:
        """Initialize UI components"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Prerequisite Section
        prereq_group = self._create_prerequisite_section()
        main_layout.addWidget(prereq_group)

        # Senator Progress Section
        senator_group = self._create_senator_section()
        main_layout.addWidget(senator_group)

        # Endorsements Section
        endorsement_group = self._create_endorsement_section()
        main_layout.addWidget(endorsement_group)

        # List Status Section
        status_group = self._create_status_section()
        main_layout.addWidget(status_group)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_prerequisite_section(self) -> QGroupBox:
        """Create Tribune x8 prerequisite progress section"""
        group = QGroupBox("Prerequisite: Tribune x8 (400 members)")
        layout = QVBoxLayout()

        # Progress bar for Tribune x8
        self.tribune_progress = QProgressBar()
        self.tribune_progress.setMaximum(400)
        self.tribune_progress.setValue(0)
        self.tribune_progress.setTextVisible(True)
        self.tribune_progress.setFormat("%v / 400 Tribune/Senator members")
        self.tribune_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                height: 24px;
            }}
            QProgressBar::chunk {{
                background-color: #1E88E5;
                border-radius: 3px;
            }}
        """)

        layout.addWidget(self.tribune_progress)

        # Tribune x8 status label
        self.tribune_label = QLabel("Loading...")
        self.tribune_label.setFont(QFont("Arial", 9))
        layout.addWidget(self.tribune_label)

        group.setLayout(layout)
        return group

    def _create_senator_section(self) -> QGroupBox:
        """Create Senator award progress section"""
        group = QGroupBox("Senator Award Progress")
        layout = QVBoxLayout()

        # Progress bar with Senator purple color
        self.senator_progress = QProgressBar()
        self.senator_progress.setMaximum(200)
        self.senator_progress.setValue(0)
        self.senator_progress.setTextVisible(True)
        self.senator_progress.setFormat("%v / 200 Senator members")
        self.senator_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                height: 28px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {SENATOR_COLOR};
                border-radius: 3px;
            }}
        """)

        layout.addWidget(self.senator_progress)

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
            (200, "Senator"),
            (400, "Senator x2"),
            (600, "Senator x3"),
            (800, "Senator x4"),
            (1000, "Senator x5"),
            (1200, "Senator x6"),
            (1400, "Senator x7"),
            (1600, "Senator x8"),
            (1800, "Senator x9"),
            (2000, "Senator x10"),
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
        """Create Senator list status section"""
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
        refresh_btn.clicked.connect(self._manual_update_senator_list)
        status_layout.addWidget(refresh_btn)

        status_layout.addStretch()
        layout.addLayout(status_layout)

        group.setLayout(layout)
        return group

    def refresh(self) -> None:
        """Refresh award progress from database"""
        try:
            progress = self.db.analyze_senator_award_progress()

            tribune_x8_count = progress['tribune_x8_count']  # Total unique Tribune members
            senators_after = progress['unique_senators']  # Senator members after x8 achievement
            is_tribune_x8 = progress['is_tribune_x8']
            endorsement = progress['endorsement']
            next_level = progress['next_level']
            senators_to_next = progress['senators_to_next']

            # Update Tribune x8 prerequisite progress
            self.tribune_progress.setMaximum(400)
            self.tribune_progress.setValue(tribune_x8_count)

            if is_tribune_x8:
                self.tribune_label.setText(f"✓ Tribune x8 achieved ({tribune_x8_count}/400)")
                self.tribune_label.setStyleSheet("color: #1E88E5; font-weight: bold;")
            else:
                needed = 400 - tribune_x8_count
                self.tribune_label.setText(f"✗ Need {needed} more members for Tribune x8")
                self.tribune_label.setStyleSheet("color: #D32F2F;")

            # Update Senator progress bar with endorsement count (contacts AFTER x8)
            self.senator_progress.setMaximum(next_level)
            self.senator_progress.setValue(senators_after)

            # Format achievement date for display
            achievement_date = progress.get('tribune_x8_achievement_date', '')
            achievement_str = ''
            if achievement_date:
                from datetime import datetime
                try:
                    date_obj = datetime.strptime(achievement_date, "%Y%m%d")
                    achievement_str = date_obj.strftime("%b %d, %Y")
                except ValueError as e:
                    # Date parsing failed, use original string
                    logger.warning(f"Failed to parse Tribune x8 achievement date '{achievement_date}': {e}")
                    achievement_str = achievement_date

            # Update status label
            if not is_tribune_x8:
                status_text = "Must achieve Tribune x8 first (400+ members)"
            elif tribune_x8_count >= 400:
                # Show Tribune x8 achievement date and count AFTER achievement
                if achievement_date:
                    status_text = f"{endorsement} • Achieved: {achievement_str} • {senators_after}/{next_level} toward next level • {senators_to_next} more to {next_level}"
                else:
                    status_text = f"{endorsement} • {senators_after} members after achievement • {senators_to_next} more to {next_level}"
            else:
                status_text = f"Progress: {tribune_x8_count}/400 Tribune members • {400 - tribune_x8_count} more to Tribune x8"

            self.status_label.setText(status_text)

            # Update endorsement checkboxes based on contacts AFTER achievement
            self._update_endorsement_display(senators_after)

        except Exception as e:
            logger.error(f"Error refreshing Senator progress: {e}")
            self.status_label.setText(f"Error: {str(e)}")

    def _update_endorsement_display(self, senator_count: int) -> None:
        """Update endorsement level visual indicators

        Args:
            senator_count: Current number of unique Senator members contacted
        """
        for level, label in self.endorsement_labels:
            if senator_count >= level:
                # Achieved - show checkmark
                label.setText(label.text().replace("☐", "☑"))
                label.setStyleSheet(f"color: {SENATOR_COLOR}; font-weight: bold;")
            else:
                # Not achieved - show empty box
                label.setText(label.text().replace("☑", "☐"))
                label.setStyleSheet("color: #666666;")

    def _update_senator_list(self) -> None:
        """Update Senator member list from SKCC if needed"""
        try:
            session = self.db.get_session()
            success = SenatorFetcher.refresh_senator_list(session, force=False)
            session.close()

            if success:
                member_count = SenatorFetcher.get_senator_member_count(session)
                self.list_status_label.setText(f"✓ Member list updated • {member_count} on record")
                logger.info(f"Senator list refreshed: {member_count} members")
            else:
                self.list_status_label.setText("Member list update failed")

        except Exception as e:
            logger.error(f"Error updating Senator list: {e}")
            self.list_status_label.setText(f"Error updating list: {str(e)}")

    def _manual_update_senator_list(self) -> None:
        """Manually trigger Senator list update"""
        try:
            self.list_status_label.setText("Updating member list...")

            session = self.db.get_session()
            success = SenatorFetcher.refresh_senator_list(session, force=True)
            session.close()

            if success:
                member_count = SenatorFetcher.get_senator_member_count(session)
                self.list_status_label.setText(f"✓ List updated • {member_count} members")
                logger.info(f"Manual Senator list update: {member_count} members")
                self.refresh()  # Refresh the widget to show updated counts
            else:
                self.list_status_label.setText("Update failed - check network connection")

        except Exception as e:
            logger.error(f"Error in manual Senator list update: {e}")
            self.list_status_label.setText(f"Update error: {str(e)}")

    def closeEvent(self, event):
        """Cleanup timers on close"""
        self.update_list_timer.stop()
        super().closeEvent(event)
