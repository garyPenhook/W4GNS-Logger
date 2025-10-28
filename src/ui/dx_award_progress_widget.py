"""
SKCC DX Award Progress Widget

Displays DX Award progress with two variants:
- DXQ Award (QSO-based): Each SKCC member per country counts separately
- DXC Award (Country-based): Each country counts only once

Both variants have 3 levels: 10, 25, 50+
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QProgressBar, QTabWidget, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from src.database.repository import DatabaseRepository
from src.awards.skcc_dx import DXQAward, DXCAward
from src.ui.signals import get_app_signals

logger = logging.getLogger(__name__)

# DX Award color (deep blue)
DX_COLOR = "#003366"


class DXAwardProgressWidget(QWidget):
    """Displays SKCC DX Award progress (both DXQ and DXC variants)"""

    def __init__(self, db: DatabaseRepository, parent: Optional[QWidget] = None):
        """
        Initialize DX Award progress widget

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

        # Create tab widget for DXQ and DXC
        tabs = QTabWidget()

        # DXQ Award Tab (QSO-based)
        dxq_widget = self._create_dxq_section()
        tabs.addTab(dxq_widget, "DXQ (QSO-Based)")
        self.dxq_progress = dxq_widget.findChild(QProgressBar, "progress_bar")
        self.dxq_status = dxq_widget.findChild(QLabel, "status_label")

        # DXC Award Tab (Country-based)
        dxc_widget = self._create_dxc_section()
        tabs.addTab(dxc_widget, "DXC (Country-Based)")
        self.dxc_progress = dxc_widget.findChild(QProgressBar, "progress_bar")
        self.dxc_status = dxc_widget.findChild(QLabel, "status_label")

        main_layout.addWidget(tabs)

        # Actions Section
        actions_group = self._create_actions_section()
        main_layout.addWidget(actions_group)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_dxq_section(self) -> QWidget:
        """Create DXQ Award section"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        # Description
        desc = QLabel(
            "DXQ: Each SKCC member per country counts separately (QSO-based)\n"
            "Effective: June 14, 2009 or later"
        )
        desc.setFont(QFont("Arial", 9))
        desc.setStyleSheet("color: #666666;")
        layout.addWidget(desc)

        # Progress section
        progress_group = QGroupBox("DXQ Progress")
        prog_layout = QVBoxLayout()

        progress_bar = QProgressBar()
        progress_bar.setObjectName("progress_bar")
        progress_bar.setMaximum(10)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat("%v countries")
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                height: 28px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {DX_COLOR};
                border-radius: 3px;
            }}
        """)
        prog_layout.addWidget(progress_bar)

        status_label = QLabel("Loading...")
        status_label.setObjectName("status_label")
        status_label.setFont(QFont("Arial", 9))
        prog_layout.addWidget(status_label)

        progress_group.setLayout(prog_layout)
        layout.addWidget(progress_group)

        # Levels section
        levels_group = QGroupBox("Award Levels")
        levels_layout = QVBoxLayout()
        levels_layout.setSpacing(3)

        dxq_levels = [
            (10, "DXQ-10"),
            (25, "DXQ-25"),
            (50, "DXQ-50+"),
        ]

        for count, name in dxq_levels:
            level_label = QLabel(f"☐ {name} ({count} SKCC members/countries)")
            level_label.setFont(QFont("Arial", 9))
            level_label.setObjectName(f"dxq_{count}")
            levels_layout.addWidget(level_label)

        levels_group.setLayout(levels_layout)
        layout.addWidget(levels_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_dxc_section(self) -> QWidget:
        """Create DXC Award section"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        # Description
        desc = QLabel(
            "DXC: Each country counts only once (country-based)\n"
            "Effective: December 19, 2009 or later"
        )
        desc.setFont(QFont("Arial", 9))
        desc.setStyleSheet("color: #666666;")
        layout.addWidget(desc)

        # Progress section
        progress_group = QGroupBox("DXC Progress")
        prog_layout = QVBoxLayout()

        progress_bar = QProgressBar()
        progress_bar.setObjectName("progress_bar")
        progress_bar.setMaximum(10)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat("%v countries")
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                height: 28px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {DX_COLOR};
                border-radius: 3px;
            }}
        """)
        prog_layout.addWidget(progress_bar)

        status_label = QLabel("Loading...")
        status_label.setObjectName("status_label")
        status_label.setFont(QFont("Arial", 9))
        prog_layout.addWidget(status_label)

        progress_group.setLayout(prog_layout)
        layout.addWidget(progress_group)

        # Levels section
        levels_group = QGroupBox("Award Levels")
        levels_layout = QVBoxLayout()
        levels_layout.setSpacing(3)

        dxc_levels = [
            (10, "DXC-10"),
            (25, "DXC-25"),
            (50, "DXC-50+"),
        ]

        for count, name in dxc_levels:
            level_label = QLabel(f"☐ {name} ({count} unique countries)")
            level_label.setFont(QFont("Arial", 9))
            level_label.setObjectName(f"dxc_{count}")
            levels_layout.addWidget(level_label)

        levels_group.setLayout(levels_layout)
        layout.addWidget(levels_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def refresh(self) -> None:
        """Refresh award progress from database"""
        try:
            session = self.db.get_session()

            # Get all contacts
            from src.database.models import Contact
            contacts = session.query(Contact).all()
            logger.info(f"DX Award: Fetched {len(contacts)} total contacts from database")
            contact_dicts = [self._contact_to_dict(c) for c in contacts]
            logger.debug(f"DX Award: Converted {len(contact_dicts)} contacts to dict format")

            # Keep session open - award class may need it
            # session.close()  # REMOVED: Session closed too early

            # Calculate DXQ progress
            dxq_award = DXQAward(session)
            dxq_progress = dxq_award.calculate_progress(contact_dicts)

            dxq_current = dxq_progress['current']
            self.dxq_progress.setMaximum(50)
            self.dxq_progress.setValue(dxq_current)
            self.dxq_status.setText(
                f"{dxq_progress['level']} • {dxq_current} SKCC member/country combinations"
            )

            # Update DXQ level indicators
            for level_name, level_count in [("dxq_10", 10), ("dxq_25", 25), ("dxq_50", 50)]:
                label = self.findChild(QLabel, level_name)
                if label:
                    if dxq_current >= level_count:
                        label.setText(label.text().replace("☐", "☑"))
                        label.setStyleSheet(f"color: {DX_COLOR}; font-weight: bold;")
                    else:
                        label.setText(label.text().replace("☑", "☐"))
                        label.setStyleSheet("color: #666666;")

            # Calculate DXC progress
            dxc_award = DXCAward(session)
            dxc_progress = dxc_award.calculate_progress(contact_dicts)

            dxc_current = dxc_progress['current']
            self.dxc_progress.setMaximum(50)
            self.dxc_progress.setValue(dxc_current)
            self.dxc_status.setText(
                f"{dxc_progress['level']} • {dxc_current} unique countries"
            )

            # Update DXC level indicators
            for level_name, level_count in [("dxc_10", 10), ("dxc_25", 25), ("dxc_50", 50)]:
                label = self.findChild(QLabel, level_name)
                if label:
                    if dxc_current >= level_count:
                        label.setText(label.text().replace("☐", "☑"))
                        label.setStyleSheet(f"color: {DX_COLOR}; font-weight: bold;")
                    else:
                        label.setText(label.text().replace("☑", "☐"))
                        label.setStyleSheet("color: #666666;")

        except Exception as e:
            logger.error(f"Error refreshing DX Award progress: {e}", exc_info=True)
            self.dxq_status.setText(f"Error: {str(e)}")
            self.dxc_status.setText(f"Error: {str(e)}")

    def _create_actions_section(self) -> QGroupBox:
        """Create actions section with report and application generation buttons"""
        group = QGroupBox("Actions")
        layout = QHBoxLayout()

        report_btn = QPushButton("Create Award Report")
        report_btn.setToolTip("Generate a DXCC award report to submit to the award manager")
        report_btn.clicked.connect(self._open_award_report_dialog)
        layout.addWidget(report_btn)

        app_btn = QPushButton("Generate Application")
        app_btn.setToolTip("Generate a DXCC award application to submit to the award manager")
        app_btn.clicked.connect(self._open_award_application_dialog)
        layout.addWidget(app_btn)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def _open_award_report_dialog(self) -> None:
        """Open award report dialog"""
        try:
            from src.ui.dialogs.award_report_dialog import AwardReportDialog
            dialog = AwardReportDialog(self.db, award_type='DXCC', parent=self)
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
            # Pre-select DXCC award
            dialog.award_combo.setCurrentText('DXCC')
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
            'dxcc': contact.dxcc,
            'distance': contact.distance,
        }
