"""
SKCC Tribune Award Progress Widget

Displays Tribune award progress with visual progress bars and endorsement levels.
The Tribune list is automatically synced daily from SKCC.
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QProgressBar, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from src.database.repository import DatabaseRepository
from src.services.tribune_fetcher import TribuneFetcher

logger = logging.getLogger(__name__)

# Tribune color (steel blue)
TRIBUNE_COLOR = "#1E88E5"


class TribuneProgressWidget(QWidget):
    """Displays SKCC Tribune award progress with auto-updating member list"""

    def __init__(self, db: DatabaseRepository, parent: Optional[QWidget] = None):
        """
        Initialize Tribune progress widget

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

        # Auto-update Tribune list daily
        self.update_list_timer = QTimer()
        self.update_list_timer.timeout.connect(self._update_tribune_list)
        self.update_list_timer.start(3600000)  # Every hour, check if update needed

        # Initial refresh
        self.refresh()
        self._update_tribune_list()

    def _init_ui(self) -> None:
        """Initialize UI components"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Prerequisite Section
        prereq_group = self._create_prerequisite_section()
        main_layout.addWidget(prereq_group)

        # Tribune Progress Section
        tribune_group = self._create_tribune_section()
        main_layout.addWidget(tribune_group)

        # Endorsements Section
        endorsement_group = self._create_endorsement_section()
        main_layout.addWidget(endorsement_group)

        # List Status Section
        status_group = self._create_status_section()
        main_layout.addWidget(status_group)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_prerequisite_section(self) -> QGroupBox:
        """Create Centurion prerequisite progress section"""
        group = QGroupBox("Prerequisite: Centurion Award")
        layout = QVBoxLayout()

        # Progress bar for Centurion
        self.centurion_progress = QProgressBar()
        self.centurion_progress.setMaximum(100)
        self.centurion_progress.setValue(0)
        self.centurion_progress.setTextVisible(True)
        self.centurion_progress.setFormat("%v / 100 members")
        self.centurion_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                height: 24px;
            }}
            QProgressBar::chunk {{
                background-color: #FF6B35;
                border-radius: 3px;
            }}
        """)

        layout.addWidget(self.centurion_progress)

        # Centurion status label
        self.centurion_label = QLabel("Loading...")
        self.centurion_label.setFont(QFont("Arial", 9))
        layout.addWidget(self.centurion_label)

        group.setLayout(layout)
        return group

    def _create_tribune_section(self) -> QGroupBox:
        """Create Tribune award progress section"""
        group = QGroupBox("Tribune Award Progress")
        layout = QVBoxLayout()

        # Progress bar with Tribune blue color
        self.tribune_progress = QProgressBar()
        self.tribune_progress.setMaximum(50)
        self.tribune_progress.setValue(0)
        self.tribune_progress.setTextVisible(True)
        self.tribune_progress.setFormat("%v / 50 Tribune/Senator members")
        self.tribune_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                height: 28px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {TRIBUNE_COLOR};
                border-radius: 3px;
            }}
        """)

        layout.addWidget(self.tribune_progress)

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
            (50, "Tribune"),
            (100, "Tribune x2"),
            (150, "Tribune x3"),
            (200, "Tribune x4"),
            (250, "Tribune x5"),
            (300, "Tribune x6"),
            (350, "Tribune x7"),
            (400, "Tribune x8"),
            (450, "Tribune x9"),
            (500, "Tribune x10"),
            (750, "Tribune x15"),
            (1000, "Tribune x20"),
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
        """Create Tribune list status section"""
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
        refresh_btn.clicked.connect(self._manual_update_tribune_list)
        status_layout.addWidget(refresh_btn)

        status_layout.addStretch()
        layout.addLayout(status_layout)

        group.setLayout(layout)
        return group

    def refresh(self) -> None:
        """Refresh award progress from database"""
        try:
            progress = self.db.analyze_tribune_award_progress()

            tribune_count = progress['unique_tribunes']  # Total unique Tribune members
            tribunes_after = progress['tribunes_after_achievement']  # Tribune members after achievement date
            centurion_count = progress['centurion_count']
            is_centurion = progress['is_centurion']
            endorsement = progress['endorsement']
            next_level = progress['next_level']
            tribunes_to_next = progress['tribunes_to_next']

            # Update Centurion prerequisite progress
            self.centurion_progress.setMaximum(100)
            self.centurion_progress.setValue(centurion_count)

            if is_centurion:
                self.centurion_label.setText(f"✓ Centurion achieved ({centurion_count}/100)")
                self.centurion_label.setStyleSheet("color: #FF6B35; font-weight: bold;")
            else:
                needed = 100 - centurion_count
                self.centurion_label.setText(f"✗ Need {needed} more members for Centurion")
                self.centurion_label.setStyleSheet("color: #D32F2F;")

            # Update Tribune progress bar with endorsement count (contacts AFTER achievement)
            self.tribune_progress.setMaximum(next_level)
            self.tribune_progress.setValue(tribunes_after)

            # Format achievement date for display
            achievement_date = progress.get('tribune_achievement_date', '')
            if achievement_date:
                from datetime import datetime
                try:
                    date_obj = datetime.strptime(achievement_date, "%Y%m%d")
                    achievement_str = date_obj.strftime("%b %d, %Y")
                except:
                    achievement_str = achievement_date

            # Update status label
            if not is_centurion:
                status_text = "Must achieve Centurion first to qualify for Tribune"
            elif tribune_count >= 50:
                # Show Tribune achievement date and count AFTER achievement
                if achievement_date:
                    status_text = f"{endorsement} • Achieved: {achievement_str} • {tribunes_after}/{next_level} toward next level • {tribunes_to_next} more to {next_level}"
                else:
                    status_text = f"{endorsement} • {tribunes_after} members after achievement • {tribunes_to_next} more to {next_level}"
            else:
                status_text = f"Progress: {tribune_count}/50 Tribune members • {50 - tribune_count} more to Tribune"

            self.status_label.setText(status_text)

            # Update endorsement checkboxes based on contacts AFTER achievement
            self._update_endorsement_display(tribunes_after)

        except Exception as e:
            logger.error(f"Error refreshing Tribune progress: {e}")
            self.status_label.setText(f"Error: {str(e)}")

    def _update_endorsement_display(self, tribune_count: int) -> None:
        """Update endorsement level visual indicators

        Args:
            tribune_count: Current number of unique Tribune members contacted
        """
        for level, label in self.endorsement_labels:
            if tribune_count >= level:
                # Achieved - show checkmark
                label.setText(label.text().replace("☐", "☑"))
                label.setStyleSheet(f"color: {TRIBUNE_COLOR}; font-weight: bold;")
            else:
                # Not achieved - show empty box
                label.setText(label.text().replace("☑", "☐"))
                label.setStyleSheet("color: #666666;")

    def _update_tribune_list(self) -> None:
        """Update Tribune member list from SKCC if needed"""
        try:
            session = self.db.get_session()
            success = TribuneFetcher.refresh_tribune_list(session, force=False)
            session.close()

            if success:
                member_count = TribuneFetcher.get_tribune_member_count(session)
                self.list_status_label.setText(f"✓ Member list updated • {member_count} on record")
                logger.info(f"Tribune list refreshed: {member_count} members")
            else:
                self.list_status_label.setText("Member list update failed")

        except Exception as e:
            logger.error(f"Error updating Tribune list: {e}")
            self.list_status_label.setText(f"Error updating list: {str(e)}")

    def _manual_update_tribune_list(self) -> None:
        """Manually trigger Tribune list update"""
        try:
            self.list_status_label.setText("Updating member list...")

            session = self.db.get_session()
            success = TribuneFetcher.refresh_tribune_list(session, force=True)
            session.close()

            if success:
                member_count = TribuneFetcher.get_tribune_member_count(session)
                self.list_status_label.setText(f"✓ List updated • {member_count} members")
                logger.info(f"Manual Tribune list update: {member_count} members")
                self.refresh()  # Refresh the widget to show updated counts
            else:
                self.list_status_label.setText("Update failed - check network connection")

        except Exception as e:
            logger.error(f"Error in manual Tribune list update: {e}")
            self.list_status_label.setText(f"Update error: {str(e)}")

    def closeEvent(self, event):
        """Cleanup timers on close"""
        self.refresh_timer.stop()
        self.update_list_timer.stop()
        super().closeEvent(event)
