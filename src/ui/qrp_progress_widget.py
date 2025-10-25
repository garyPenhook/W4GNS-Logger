"""
QRP Award Progress Widget

Displays QRP x1, QRP x2, and MPW award progress with visual progress bars.
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from src.database.repository import DatabaseRepository

logger = logging.getLogger(__name__)


class QRPProgressWidget(QWidget):
    """Displays QRP award progress with progress bars"""

    def __init__(self, db: DatabaseRepository, parent: Optional[QWidget] = None):
        """
        Initialize QRP progress widget

        Args:
            db: Database repository instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.db = db

        self._init_ui()

        # Auto-refresh every 5 seconds
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(5000)

    def _init_ui(self) -> None:
        """Initialize UI components"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # QRP x1 Award Section
        qrp_x1_group = self._create_qrp_x1_section()
        main_layout.addWidget(qrp_x1_group)

        # QRP x2 Award Section
        qrp_x2_group = self._create_qrp_x2_section()
        main_layout.addWidget(qrp_x2_group)

        # MPW Award Section
        mpw_group = self._create_mpw_section()
        main_layout.addWidget(mpw_group)

        # Power Statistics Section
        stats_group = self._create_statistics_section()
        main_layout.addWidget(stats_group)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_qrp_x1_section(self) -> QGroupBox:
        """Create QRP x1 award progress section"""
        group = QGroupBox("QRP x1 Award (Your Power ≤5W)")
        layout = QVBoxLayout()

        # Progress bar
        self.qrp_x1_progress = QProgressBar()
        self.qrp_x1_progress.setMaximum(300)
        self.qrp_x1_progress.setValue(0)
        self.qrp_x1_progress.setTextVisible(True)
        self.qrp_x1_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)

        layout.addWidget(self.qrp_x1_progress)

        # Stats label
        self.qrp_x1_label = QLabel("Points: 0/300 | Bands: 0 | Contacts: 0")
        self.qrp_x1_label.setFont(QFont("Arial", 9))
        layout.addWidget(self.qrp_x1_label)

        group.setLayout(layout)
        return group

    def _create_qrp_x2_section(self) -> QGroupBox:
        """Create QRP x2 award progress section"""
        group = QGroupBox("QRP x2 Award (Both Stations ≤5W)")
        layout = QVBoxLayout()

        # Progress bar
        self.qrp_x2_progress = QProgressBar()
        self.qrp_x2_progress.setMaximum(150)
        self.qrp_x2_progress.setValue(0)
        self.qrp_x2_progress.setTextVisible(True)
        self.qrp_x2_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 3px;
            }
        """)

        layout.addWidget(self.qrp_x2_progress)

        # Stats label
        self.qrp_x2_label = QLabel("Points: 0/150 | Bands: 0 | Contacts: 0")
        self.qrp_x2_label.setFont(QFont("Arial", 9))
        layout.addWidget(self.qrp_x2_label)

        group.setLayout(layout)
        return group

    def _create_mpw_section(self) -> QGroupBox:
        """Create MPW award section"""
        group = QGroupBox("QRP Miles Per Watt (≥1000 MPW at ≤5W)")
        layout = QVBoxLayout()

        # MPW qualifications count
        self.mpw_label = QLabel("Qualifications: 0")
        self.mpw_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(self.mpw_label)

        # MPW details
        self.mpw_details = QLabel("No MPW qualifications yet")
        self.mpw_details.setFont(QFont("Arial", 9))
        self.mpw_details.setWordWrap(True)
        layout.addWidget(self.mpw_details)

        group.setLayout(layout)
        return group

    def _create_statistics_section(self) -> QGroupBox:
        """Create power statistics section"""
        group = QGroupBox("Power Statistics")
        layout = QVBoxLayout()

        # Stats layout
        stats_layout = QHBoxLayout()

        # QRP count
        qrp_layout = QVBoxLayout()
        qrp_label = QLabel("QRP (≤5W)")
        qrp_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.qrp_count_label = QLabel("0 contacts")
        self.qrp_count_label.setFont(QFont("Arial", 11))
        qrp_layout.addWidget(qrp_label)
        qrp_layout.addWidget(self.qrp_count_label)
        stats_layout.addLayout(qrp_layout)

        # STANDARD count
        std_layout = QVBoxLayout()
        std_label = QLabel("Standard (5-100W)")
        std_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.std_count_label = QLabel("0 contacts")
        self.std_count_label.setFont(QFont("Arial", 11))
        std_layout.addWidget(std_label)
        std_layout.addWidget(self.std_count_label)
        stats_layout.addLayout(std_layout)

        # QRO count
        qro_layout = QVBoxLayout()
        qro_label = QLabel("QRO (>100W)")
        qro_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.qro_count_label = QLabel("0 contacts")
        self.qro_count_label.setFont(QFont("Arial", 11))
        qro_layout.addWidget(qro_label)
        qro_layout.addWidget(self.qro_count_label)
        stats_layout.addLayout(qro_layout)

        # Average power
        avg_layout = QVBoxLayout()
        avg_label = QLabel("Average Power")
        avg_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.avg_power_label = QLabel("0.0 W")
        self.avg_power_label.setFont(QFont("Arial", 11))
        avg_layout.addWidget(avg_label)
        avg_layout.addWidget(self.avg_power_label)
        stats_layout.addLayout(avg_layout)

        layout.addLayout(stats_layout)
        group.setLayout(layout)
        return group

    def refresh(self) -> None:
        """Refresh all QRP progress displays"""
        try:
            # Get QRP award progress
            progress = self.db.analyze_qrp_award_progress()

            # Update QRP x1
            qrp_x1_points = progress['qrp_x1']['points']
            self.qrp_x1_progress.setValue(int(qrp_x1_points))
            bands_x1 = progress['qrp_x1']['unique_bands']
            contacts_x1 = progress['qrp_x1']['contacts']
            qualified_x1 = "✓ QUALIFIED" if progress['qrp_x1']['qualified'] else ""
            self.qrp_x1_label.setText(
                f"Points: {qrp_x1_points}/300 | Bands: {bands_x1} | Contacts: {contacts_x1} {qualified_x1}"
            )
            if progress['qrp_x1']['qualified']:
                self.qrp_x1_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.qrp_x1_label.setStyleSheet("")

            # Update QRP x2
            qrp_x2_points = progress['qrp_x2']['points']
            self.qrp_x2_progress.setValue(int(qrp_x2_points))
            bands_x2 = progress['qrp_x2']['unique_bands']
            contacts_x2 = progress['qrp_x2']['contacts']
            qualified_x2 = "✓ QUALIFIED" if progress['qrp_x2']['qualified'] else ""
            self.qrp_x2_label.setText(
                f"Points: {qrp_x2_points}/150 | Bands: {bands_x2} | Contacts: {contacts_x2} {qualified_x2}"
            )
            if progress['qrp_x2']['qualified']:
                self.qrp_x2_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.qrp_x2_label.setStyleSheet("")

            # Get MPW qualifications
            mpw_quals = self.db.calculate_mpw_qualifications()
            self.mpw_label.setText(f"Qualifications: {len(mpw_quals)}")

            if mpw_quals:
                mpw_text = "Qualifying contacts:\n"
                for qual in mpw_quals[:5]:  # Show first 5
                    mpw_text += f"  • {qual['callsign']}: {qual['mpw']:.0f} MPW\n"
                if len(mpw_quals) > 5:
                    mpw_text += f"  ... and {len(mpw_quals) - 5} more"
                self.mpw_details.setText(mpw_text)
                self.mpw_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.mpw_details.setText("No MPW qualifications yet (need ≥1000 MPW at ≤5W)")
                self.mpw_label.setStyleSheet("")

            # Get power statistics
            stats = self.db.get_power_statistics()
            self.qrp_count_label.setText(f"{stats['qrp_count']} contacts")
            self.std_count_label.setText(f"{stats['standard_count']} contacts")
            self.qro_count_label.setText(f"{stats['qro_count']} contacts")
            self.avg_power_label.setText(f"{stats['average_power']:.1f} W")

        except Exception as e:
            logger.error(f"Error refreshing QRP progress: {e}", exc_info=True)

    def closeEvent(self, event) -> None:
        """Clean up timer on close"""
        self.refresh_timer.stop()
        super().closeEvent(event)
