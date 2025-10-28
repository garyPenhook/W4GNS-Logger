"""
SKCC WAS Award Progress Widget

Displays WAS award progress tracking contacts with SKCC members in all 50 US states.
Shows state-by-state progress with contact counts and band-specific tracking.
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from src.database.repository import DatabaseRepository
from src.awards.was import WASAward
from src.ui.signals import get_app_signals

logger = logging.getLogger(__name__)

# WAS color (patriotic blue)
WAS_COLOR = "#003366"


class WASProgressWidget(QWidget):
    """Displays SKCC WAS award progress with state tracking"""

    def __init__(self, db: DatabaseRepository, parent: Optional[QWidget] = None):
        """
        Initialize WAS progress widget

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

        # States Status Section
        states_group = self._create_states_section()
        main_layout.addWidget(states_group)

        # Per-State Details Section
        details_group = self._create_details_section()
        main_layout.addWidget(details_group)

        # Statistics Section
        stats_group = self._create_stats_section()
        main_layout.addWidget(stats_group)

        # Actions Section
        actions_group = self._create_actions_section()
        main_layout.addWidget(actions_group)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_progress_section(self) -> QGroupBox:
        """Create overall progress section"""
        group = QGroupBox("WAS Progress")
        layout = QVBoxLayout()

        # Description
        desc = QLabel(
            "Contact SKCC members in all 50 US states\n"
            "Any band, any time - single-band and QRP endorsements available"
        )
        desc.setFont(QFont("Arial", 9))
        desc.setStyleSheet("color: #666666;")
        layout.addWidget(desc)

        # Overall progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(50)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v / 50 states")
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                height: 28px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {WAS_COLOR};
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

    def _create_states_section(self) -> QGroupBox:
        """Create states status section"""
        group = QGroupBox("Award Status")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        # Status indicator labels
        self.states_worked_label = QLabel("States Worked: 0/50")
        self.states_worked_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(self.states_worked_label)

        self.missing_label = QLabel("Missing: All 50 states")
        self.missing_label.setFont(QFont("Arial", 9))
        self.missing_label.setStyleSheet("color: #666666;")
        layout.addWidget(self.missing_label)

        layout.addSpacing(8)

        self.award_status = QLabel("Award Status: Not Yet Achieved")
        self.award_status.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(self.award_status)

        group.setLayout(layout)
        return group

    def _create_details_section(self) -> QGroupBox:
        """Create per-state details section"""
        group = QGroupBox("State Details (All 50 States)")
        layout = QVBoxLayout()

        # Table for state details
        self.details_table = QTableWidget()
        self.details_table.setColumnCount(2)
        self.details_table.setHorizontalHeaderLabels(["State", "Contacts"])
        self.details_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.details_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.details_table.setMaximumHeight(300)

        layout.addWidget(self.details_table)

        group.setLayout(layout)
        return group

    def _create_stats_section(self) -> QGroupBox:
        """Create statistics section"""
        group = QGroupBox("Statistics")
        layout = QVBoxLayout()
        layout.setSpacing(6)

        # Stats labels
        stats_layout = QHBoxLayout()

        self.progress_label = QLabel("Progress: 0%")
        self.progress_label.setFont(QFont("Arial", 9))
        stats_layout.addWidget(self.progress_label)

        self.total_contacts_label = QLabel("Total Qualifying Contacts: 0")
        self.total_contacts_label.setFont(QFont("Arial", 9))
        stats_layout.addWidget(self.total_contacts_label)

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
            logger.info(f"WAS Award: Fetched {len(contacts)} total contacts from database")

            contact_dicts = [self._contact_to_dict(c) for c in contacts]
            logger.debug(f"WAS Award: Converted {len(contact_dicts)} contacts to dict format")

            # Keep session open - some award classes may need it
            # session.close()  # REMOVED: Session closed too early, causing issues

            # Calculate WAS progress
            was_award = WASAward(session)
            progress = was_award.calculate_progress(contact_dicts)

            # Extract progress values
            states_worked = progress['states_worked']
            state_details = progress['state_details']
            achieved = progress['achieved']
            current = progress['current']
            progress_pct = progress['progress_pct']

            logger.info(f"WAS Award: Calculated progress - {current}/50 states worked, achieved={achieved}")
            if current > 0:
                logger.info(f"WAS Award: States worked: {', '.join(sorted(states_worked))}")

            # Update overall progress bar
            self.progress_bar.setValue(current)

            # Update status label
            if achieved:
                status_text = "✅ WAS Award Achieved!"
            else:
                missing = 50 - current
                status_text = f"Working toward WAS - {missing} state(s) needed"

            self.status_label.setText(
                f"{status_text} • {current}/50 states worked"
            )

            # Update states worked indicator
            self.states_worked_label.setText(f"States Worked: {current}/50")

            # Update missing states
            if achieved:
                self.missing_label.setText("✅ All 50 states achieved!")
                self.missing_label.setStyleSheet(f"color: {WAS_COLOR}; font-weight: bold;")
            else:
                missing_states = [
                    state_code
                    for state_code in sorted(state_details.keys())
                    if state_code not in states_worked
                ]
                missing_text = "Missing: " + ", ".join(missing_states)
                self.missing_label.setText(missing_text)
                self.missing_label.setStyleSheet("color: #666666;")

            # Update award status
            if achieved:
                self.award_status.setText("✅ Award Status: WAS ACHIEVED!")
                self.award_status.setStyleSheet(f"color: {WAS_COLOR}; font-weight: bold;")
            else:
                self.award_status.setText(f"Award Status: {current}/50 states")
                self.award_status.setStyleSheet("color: #666666;")

            # Update details table
            self.details_table.setRowCount(0)

            # Get state names from WASAward
            from src.awards.was import US_STATES
            for state_code in sorted(US_STATES.keys()):
                state_name = US_STATES[state_code]
                count = state_details.get(state_code, 0)
                is_worked = state_code in states_worked

                row = self.details_table.rowCount()
                self.details_table.insertRow(row)

                # State name
                name_item = QTableWidgetItem(f"{state_code} - {state_name}")
                name_item.setFont(QFont("Arial", 9))
                if is_worked:
                    name_item.setForeground(QColor(WAS_COLOR))
                self.details_table.setItem(row, 0, name_item)

                # Contact count
                count_item = QTableWidgetItem(str(count))
                count_item.setFont(QFont("Arial", 9))
                if is_worked:
                    count_item.setForeground(QColor(WAS_COLOR))
                self.details_table.setItem(row, 1, count_item)

            # Update statistics
            self.progress_label.setText(f"Progress: {progress_pct:.1f}%")

            total_contacts = sum(state_details.values())
            self.total_contacts_label.setText(f"Total Qualifying Contacts: {total_contacts}")

        except Exception as e:
            logger.error(f"Error refreshing WAS progress: {e}", exc_info=True)
            self.status_label.setText(f"Error: {str(e)}")

    def _create_actions_section(self) -> QGroupBox:
        """Create actions section with report and application generation buttons"""
        group = QGroupBox("Actions")
        layout = QHBoxLayout()

        report_btn = QPushButton("Create Award Report")
        report_btn.setToolTip("Generate a WAS award report to submit to the award manager")
        report_btn.clicked.connect(self._open_award_report_dialog)
        layout.addWidget(report_btn)

        app_btn = QPushButton("Generate Application")
        app_btn.setToolTip("Generate a WAS award application to submit to the award manager")
        app_btn.clicked.connect(self._open_award_application_dialog)
        layout.addWidget(app_btn)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def _open_award_report_dialog(self) -> None:
        """Open award report dialog"""
        try:
            from src.ui.dialogs.award_report_dialog import AwardReportDialog
            dialog = AwardReportDialog(self.db, award_type='WAS', parent=self)
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
            # Pre-select WAS award
            dialog.award_combo.setCurrentText('WAS')
            dialog.exec()
        except Exception as e:
            logger.error(f"Error opening award application dialog: {e}", exc_info=True)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to open application dialog: {str(e)}")

    def _contact_to_dict(self, contact) -> dict:
        """Convert Contact ORM object to dictionary"""
        return {
            'callsign': contact.callsign,
            'mode': contact.mode,
            'band': contact.band,
            'qso_date': contact.qso_date,
            'qso_time': contact.time_on,
            'skcc_number': contact.skcc_number,
            'key_type': contact.key_type,
            'state': getattr(contact, 'state', ''),
            'comments': getattr(contact, 'comments', ''),
        }
