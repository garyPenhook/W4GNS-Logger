"""
SKCC Centurion Award Progress Widget

Displays Centurion award progress with visual progress bars and endorsement levels.
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QProgressBar, QPushButton
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.database.repository import DatabaseRepository
from src.ui.signals import get_app_signals

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
        self.refresh()

        # Connect to signals for refresh on contact changes
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

        # Centurion Progress Section
        centurion_group = self._create_centurion_section()
        main_layout.addWidget(centurion_group)

        # Endorsements Section
        endorsement_group = self._create_endorsement_section()
        main_layout.addWidget(endorsement_group)

        # Actions Section
        actions_group = self._create_actions_section()
        main_layout.addWidget(actions_group)

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

    def _create_actions_section(self) -> QGroupBox:
        """Create actions section with report and application generation buttons"""
        group = QGroupBox("Actions")
        layout = QHBoxLayout()

        report_btn = QPushButton("Create Award Report")
        report_btn.setToolTip("Generate a Centurion award report to submit to the award manager")
        report_btn.clicked.connect(self._open_award_report_dialog)
        layout.addWidget(report_btn)

        app_btn = QPushButton("Generate Application")
        app_btn.setToolTip("Generate a Centurion award application to submit to the award manager")
        app_btn.clicked.connect(self._open_award_application_dialog)
        layout.addWidget(app_btn)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def _open_award_report_dialog(self) -> None:
        """Open award report dialog"""
        try:
            from src.ui.dialogs.award_report_dialog import AwardReportDialog
            dialog = AwardReportDialog(self.db, award_type='Centurion', parent=self)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error opening award report dialog: {e}", exc_info=True)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to open report dialog: {str(e)}")

    def _open_award_application_dialog(self) -> None:
        """Open award application dialog"""
        try:
            from src.ui.dialogs.award_application_dialog import AwardApplicationDialog
            dialog = AwardApplicationDialog(self.db, parent=self)
            # Pre-select Centurion award
            dialog.award_combo.setCurrentText('Centurion')
            dialog.exec()
        except Exception as e:
            logger.error(f"Error opening award application dialog: {e}", exc_info=True)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to open application dialog: {str(e)}")

