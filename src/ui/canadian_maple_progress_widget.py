"""
SKCC Canadian Maple Award Progress Widget

Displays Canadian Maple award progress with 4 award levels:
- Yellow Maple (10 provinces/territories)
- Orange Maple (10 per band)
- Red Maple (90 total, 10 per province, 9 bands)
- Gold Maple (90 QRP ≤5W, 9 bands)
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
from src.ui.signals import get_app_signals

logger = logging.getLogger(__name__)

# Canadian Maple colors
MAPLE_YELLOW = "#FFD700"
MAPLE_ORANGE = "#FF8C00"
MAPLE_RED = "#DC143C"
MAPLE_GOLD = "#FFD700"


class CanadianMapleProgressWidget(QWidget):
    """Displays SKCC Canadian Maple award progress with 4 award levels"""

    def __init__(self, db: DatabaseRepository, parent: Optional[QWidget] = None):
        """
        Initialize Canadian Maple progress widget

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

        # Yellow Maple Section
        yellow_group = self._create_level_section(
            "Yellow Maple", "10 provinces/territories", MAPLE_YELLOW, 10
        )
        main_layout.addWidget(yellow_group)
        self.yellow_progress = yellow_group.findChild(QProgressBar)
        self.yellow_label = yellow_group.findChild(QLabel, "status_label")

        # Orange Maple Section
        orange_group = self._create_level_section(
            "Orange Maple", "10 provinces per band (per band)", MAPLE_ORANGE, 10
        )
        main_layout.addWidget(orange_group)
        self.orange_progress = orange_group.findChild(QProgressBar)
        self.orange_label = orange_group.findChild(QLabel, "status_label")

        # Red Maple Section
        red_group = self._create_level_section(
            "Red Maple", "90 total (10 each from 10 provinces, 9 bands)", MAPLE_RED, 90
        )
        main_layout.addWidget(red_group)
        self.red_progress = red_group.findChild(QProgressBar)
        self.red_label = red_group.findChild(QLabel, "status_label")

        # Gold Maple Section
        gold_group = self._create_level_section(
            "Gold Maple", "90 QRP ≤5W (9 bands)", MAPLE_GOLD, 90
        )
        main_layout.addWidget(gold_group)
        self.gold_progress = gold_group.findChild(QProgressBar)
        self.gold_label = gold_group.findChild(QLabel, "status_label")

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_level_section(
        self, title: str, description: str, color: str, max_value: int
    ) -> QGroupBox:
        """Create a level section with progress bar"""
        group = QGroupBox(title)
        layout = QVBoxLayout()

        # Description
        desc_label = QLabel(description)
        desc_label.setFont(QFont("Arial", 9))
        desc_label.setStyleSheet("color: #666666;")
        layout.addWidget(desc_label)

        # Progress bar
        progress = QProgressBar()
        progress.setMaximum(max_value)
        progress.setValue(0)
        progress.setTextVisible(True)
        progress.setFormat(f"%v / {max_value}")
        progress.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                height: 24px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)
        layout.addWidget(progress)

        # Status label
        status_label = QLabel("Loading...")
        status_label.setObjectName("status_label")
        status_label.setFont(QFont("Arial", 9))
        layout.addWidget(status_label)

        group.setLayout(layout)
        return group

    def refresh(self) -> None:
        """Refresh award progress from database"""
        try:
            progress = self.db.get_canadian_maple_award_progress()

            # Update Yellow Maple
            yellow_current = progress['yellow']['current']
            yellow_required = progress['yellow']['required']
            self.yellow_progress.setMaximum(yellow_required)
            self.yellow_progress.setValue(yellow_current)
            yellow_achieved = "✓" if progress['yellow']['achieved'] else "○"
            self.yellow_label.setText(
                f"{yellow_achieved} {yellow_current}/{yellow_required} provinces/territories"
            )

            # Update Orange Maple
            orange_current = progress['orange']['current']
            orange_required = progress['orange']['required']
            self.orange_progress.setMaximum(orange_required)
            self.orange_progress.setValue(orange_current)
            orange_achieved = "✓" if progress['orange']['achieved'] else "○"
            self.orange_label.setText(
                f"{orange_achieved} {orange_current}/{orange_required} per band"
            )

            # Update Red Maple
            red_current = progress['red']['current']
            red_required = progress['red']['required']
            self.red_progress.setMaximum(red_required)
            self.red_progress.setValue(red_current)
            red_achieved = "✓" if progress['red']['achieved'] else "○"
            self.red_label.setText(
                f"{red_achieved} {red_current}/{red_required} total QSOs"
            )

            # Update Gold Maple
            gold_current = progress['gold']['current']
            gold_required = progress['gold']['required']
            self.gold_progress.setMaximum(gold_required)
            self.gold_progress.setValue(gold_current)
            gold_achieved = "✓" if progress['gold']['achieved'] else "○"
            self.gold_label.setText(
                f"{gold_achieved} {gold_current}/{gold_required} QRP contacts"
            )

        except Exception as e:
            logger.error(f"Error refreshing Canadian Maple progress: {e}", exc_info=True)
            self.yellow_label.setText(f"Error: {str(e)}")
