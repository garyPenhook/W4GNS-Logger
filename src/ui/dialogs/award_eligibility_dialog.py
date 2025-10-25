"""
Award Eligibility Dialog

Shows SKCC award eligibility for a specific member during contact logging.
Displays previous contacts and whether current awards can be obtained.
"""

import logging
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QGroupBox, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtGui import QFont, QColor

from src.database.repository import DatabaseRepository

logger = logging.getLogger(__name__)


class AwardEligibilityDialog(QDialog):
    """Dialog showing SKCC award eligibility for a contact"""

    def __init__(
        self,
        db: DatabaseRepository,
        skcc_number: str,
        parent: Optional[QDialog] = None
    ):
        """
        Initialize award eligibility dialog

        Args:
            db: Database repository instance
            skcc_number: SKCC member number to look up
            parent: Parent widget
        """
        super().__init__(parent)
        self.db = db
        self.skcc_number = skcc_number

        self.setWindowTitle(f"Award Eligibility - SKCC {skcc_number}")
        self.setGeometry(100, 100, 900, 600)

        self._init_ui()
        self._load_data()

    def _init_ui(self) -> None:
        """Initialize UI components"""
        main_layout = QVBoxLayout()

        # Member info section
        info_group = self._create_member_info_section()
        main_layout.addWidget(info_group)

        # Award eligibility section
        awards_group = self._create_awards_section()
        main_layout.addWidget(awards_group)

        # Contact history section
        history_group = self._create_history_section()
        main_layout.addWidget(history_group)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def _create_member_info_section(self) -> QGroupBox:
        """Create member information section"""
        group = QGroupBox("Member Information")
        layout = QVBoxLayout()

        info_layout = QHBoxLayout()

        # Callsign
        callsign_label = QLabel("Callsign:")
        callsign_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.callsign_display = QLabel("")
        self.callsign_display.setFont(QFont("Arial", 11))
        info_layout.addWidget(callsign_label)
        info_layout.addWidget(self.callsign_display)

        info_layout.addSpacing(30)

        # Total contacts
        total_label = QLabel("Total Contacts:")
        total_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.total_display = QLabel("0")
        self.total_display.setFont(QFont("Arial", 11))
        info_layout.addWidget(total_label)
        info_layout.addWidget(self.total_display)

        info_layout.addSpacing(30)

        # Last contact
        last_label = QLabel("Last Contact:")
        last_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.last_display = QLabel("")
        self.last_display.setFont(QFont("Arial", 11))
        info_layout.addWidget(last_label)
        info_layout.addWidget(self.last_display)

        info_layout.addStretch()
        layout.addLayout(info_layout)

        group.setLayout(layout)
        return group

    def _create_awards_section(self) -> QGroupBox:
        """Create award eligibility section"""
        group = QGroupBox("Award Eligibility")
        layout = QVBoxLayout()

        self.awards_text = QLabel("")
        self.awards_text.setFont(QFont("Courier", 9))
        self.awards_text.setWordWrap(True)
        self.awards_text.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        scroll = QScrollArea()
        scroll.setWidget(self.awards_text)
        scroll.setWidgetResizable(True)

        layout.addWidget(scroll)
        group.setLayout(layout)
        return group

    def _create_history_section(self) -> QGroupBox:
        """Create contact history section"""
        group = QGroupBox("Recent Contacts with This Member")
        layout = QVBoxLayout()

        # Create table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "Date", "Time", "Band", "Mode", "SKCC Suffix"
        ])
        self.history_table.setMaximumHeight(200)
        self.history_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        layout.addWidget(self.history_table)
        group.setLayout(layout)
        return group

    def _load_data(self) -> None:
        """Load member data and display"""
        try:
            # Get member summary
            summary = self.db.get_skcc_member_summary(self.skcc_number)

            if not summary.get('found'):
                self.callsign_display.setText("Not found")
                self.awards_text.setText(
                    f"No contacts found for SKCC {self.skcc_number}"
                )
                return

            # Display member info
            self.callsign_display.setText(summary.get('callsign', 'Unknown'))
            self.total_display.setText(str(summary.get('total_contacts', 0)))
            last_date = summary.get('last_contact_date', '')
            last_time = summary.get('last_contact_time', '')
            self.last_display.setText(f"{last_date} {last_time}")

            # Get award eligibility
            eligibility = self.db.analyze_skcc_award_eligibility(self.skcc_number)
            self._display_award_eligibility(eligibility)

            # Get contact history
            history = self.db.get_skcc_contact_history(self.skcc_number)
            self._display_contact_history(history[:10])  # Show last 10

        except Exception as e:
            logger.error(f"Error loading award eligibility data: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load award data: {str(e)}")

    def _display_award_eligibility(self, eligibility: Dict[str, Any]) -> None:
        """Display award eligibility information"""
        try:
            text = "Award Progress:\n\n"

            # Centurion
            c_progress = eligibility.get('centurion', {})
            c_status = "✓" if c_progress.get('qualified') else "○"
            text += f"{c_status} Centurion: {c_progress.get('contact_count', 0)}/100 contacts\n"

            # Tribune
            t_progress = eligibility.get('tribune', {})
            t_status = "✓" if t_progress.get('qualified') else "○"
            text += f"{t_status} Tribune: {t_progress.get('contact_count', 0)}/50 contacts\n"

            # Tribune levels
            tx_progress = eligibility.get('tribune_levels', {})
            for level, data in tx_progress.items():
                level_num = level.replace('Tx', '')
                status = "✓" if data.get('qualified') else "○"
                text += f"  {status} {level}: {data.get('contact_count', 0)}/{data.get('requirement', 0)} contacts\n"

            # Senator
            s_progress = eligibility.get('senator', {})
            s_status = "✓" if s_progress.get('qualified') else "○"
            text += f"{s_status} Senator: {s_progress.get('contact_count', 0)}/200 contacts\n"

            # Triple Key
            tk_progress = eligibility.get('triple_key', {})
            tk_status = "✓" if tk_progress.get('qualified') else "○"
            text += f"\n{tk_status} Triple Key Award:\n"
            text += f"   Total QSOs: {tk_progress.get('total_qsos', 0)}/300\n"
            for key_type, count in tk_progress.get('by_key_type', {}).items():
                text += f"   {key_type}: {count} QSOs\n"

            # Geographic awards
            geo_awards = eligibility.get('geographic_awards', {})
            text += f"\nGeographic Awards:\n"
            for award, data in geo_awards.items():
                status = "✓" if data.get('qualified') else "○"
                text += f"  {status} {award}: {data.get('contact_count', 0)}/{data.get('requirement', 0)}\n"

            self.awards_text.setText(text)

        except Exception as e:
            logger.error(f"Error displaying award eligibility: {e}", exc_info=True)
            self.awards_text.setText(f"Error loading award data: {str(e)}")

    def _display_contact_history(self, history: list) -> None:
        """Display recent contact history"""
        try:
            self.history_table.setRowCount(len(history))

            for row, contact in enumerate(history):
                # Date
                date_item = QTableWidgetItem(contact.get('date', ''))
                self.history_table.setItem(row, 0, date_item)

                # Time
                time_item = QTableWidgetItem(contact.get('time', ''))
                self.history_table.setItem(row, 1, time_item)

                # Band
                band_item = QTableWidgetItem(contact.get('band', ''))
                self.history_table.setItem(row, 2, band_item)

                # Mode
                mode_item = QTableWidgetItem(contact.get('mode', ''))
                self.history_table.setItem(row, 3, mode_item)

                # SKCC Suffix
                suffix_item = QTableWidgetItem(contact.get('skcc_suffix', ''))
                self.history_table.setItem(row, 4, suffix_item)

            # Resize columns
            self.history_table.resizeColumnsToContents()

        except Exception as e:
            logger.error(f"Error displaying contact history: {e}", exc_info=True)
