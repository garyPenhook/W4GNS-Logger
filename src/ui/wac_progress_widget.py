"""
SKCC WAC Award Progress Widget

Displays WAC award progress tracking contacts with SKCC members in all 6 continents:
- North America
- South America
- Europe
- Africa
- Asia
- Oceania
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from src.database.repository import DatabaseRepository
from src.awards.wac import WACAward
from src.ui.signals import get_app_signals

logger = logging.getLogger(__name__)

# WAC color (deep ocean blue)
WAC_COLOR = "#004B87"

# Continent colors for visual distinction
CONTINENT_COLORS = {
    'NA': '#FF6B6B',      # Red for North America
    'SA': '#4ECDC4',      # Teal for South America
    'EU': '#FFE66D',      # Yellow for Europe
    'AF': '#FF9FF3',      # Pink for Africa
    'AS': '#54A0FF',      # Blue for Asia
    'OC': '#48DBFB',      # Light blue for Oceania
}

CONTINENT_NAMES = {
    'NA': 'North America',
    'SA': 'South America',
    'EU': 'Europe',
    'AF': 'Africa',
    'AS': 'Asia',
    'OC': 'Oceania',
}


class WACProgressWidget(QWidget):
    """Displays SKCC WAC award progress with continent tracking"""

    def __init__(self, db: DatabaseRepository, parent: Optional[QWidget] = None):
        """
        Initialize WAC progress widget

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

        # Continents Status Section
        continents_group = self._create_continents_section()
        main_layout.addWidget(continents_group)

        # Per-Continent Details Section
        details_group = self._create_details_section()
        main_layout.addWidget(details_group)

        # Statistics Section
        stats_group = self._create_stats_section()
        main_layout.addWidget(stats_group)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_progress_section(self) -> QGroupBox:
        """Create overall progress section"""
        group = QGroupBox("WAC Progress")
        layout = QVBoxLayout()

        # Description
        desc = QLabel(
            "Contact SKCC members in all six continental areas of the world\n"
            "North America, South America, Europe, Africa, Asia, Oceania"
        )
        desc.setFont(QFont("Arial", 9))
        desc.setStyleSheet("color: #666666;")
        layout.addWidget(desc)

        # Overall progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(6)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v / 6 continents")
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                height: 28px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {WAC_COLOR};
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

    def _create_continents_section(self) -> QGroupBox:
        """Create continents status section"""
        group = QGroupBox("Continental Status")
        layout = QGridLayout()
        layout.setSpacing(10)

        self.continent_labels = {}

        # Create labels for each continent in 2x3 grid
        continents_order = ['NA', 'SA', 'EU', 'AF', 'AS', 'OC']
        row = 0
        col = 0

        for continent_code in continents_order:
            continent_name = CONTINENT_NAMES.get(continent_code, continent_code)
            label = QLabel(f"☐ {continent_name} (0 QSOs)")
            label.setFont(QFont("Arial", 10))
            self.continent_labels[continent_code] = label
            layout.addWidget(label, row, col)

            col += 1
            if col >= 3:
                col = 0
                row += 1

        group.setLayout(layout)
        return group

    def _create_details_section(self) -> QGroupBox:
        """Create per-continent details section"""
        group = QGroupBox("Continent Details")
        layout = QVBoxLayout()

        # Table for continent details
        self.details_table = QTableWidget()
        self.details_table.setColumnCount(2)
        self.details_table.setHorizontalHeaderLabels(["Continent", "Contacts"])
        self.details_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.details_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.details_table.setMaximumHeight(200)

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

        self.continents_worked_label = QLabel("Continents Worked: 0/6")
        self.continents_worked_label.setFont(QFont("Arial", 9))
        stats_layout.addWidget(self.continents_worked_label)

        self.total_contacts_label = QLabel("Total Qualifying Contacts: 0")
        self.total_contacts_label.setFont(QFont("Arial", 9))
        stats_layout.addWidget(self.total_contacts_label)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # Missing continents label
        self.missing_label = QLabel("Missing: All 6 continents")
        self.missing_label.setFont(QFont("Arial", 9))
        self.missing_label.setStyleSheet("color: #666666;")
        layout.addWidget(self.missing_label)

        group.setLayout(layout)
        return group

    def refresh(self) -> None:
        """Refresh award progress from database"""
        try:
            session = self.db.get_session()

            # Get all contacts
            from src.database.models import Contact
            contacts = session.query(Contact).all()
            logger.info(f"WAC Award: Fetched {len(contacts)} total contacts from database")

            contact_dicts = [self._contact_to_dict(c) for c in contacts]
            logger.debug(f"WAC Award: Converted {len(contact_dicts)} contacts to dict format")

            # Keep session open - award class may need it
            # session.close()  # REMOVED: Session closed too early

            # Calculate WAC progress
            wac_award = WACAward(session)
            progress = wac_award.calculate_progress(contact_dicts)

            # Extract progress values
            continents_worked = progress['continents_worked']
            continent_details = progress['continent_details']
            achieved = progress['achieved']
            current = progress['current']

            logger.info(f"WAC Award: Calculated progress - {current}/6 continents worked, achieved={achieved}")
            if current > 0:
                logger.info(f"WAC Award: Continents worked: {', '.join(sorted(continents_worked))}")

            # Update overall progress bar
            self.progress_bar.setValue(current)

            # Update status label
            if achieved:
                status_text = "✅ WAC Award Achieved!"
            else:
                missing = 6 - current
                status_text = f"Working toward WAC - {missing} continent(s) needed"

            self.status_label.setText(
                f"{status_text} • {current}/6 continents worked"
            )

            # Update continent indicators
            for continent_code, continent_name in CONTINENT_NAMES.items():
                count = continent_details.get(continent_code, 0)
                is_worked = continent_code in continents_worked

                indicator = "☑" if is_worked else "☐"
                label_text = f"{indicator} {continent_name} ({count} QSOs)"

                label = self.continent_labels[continent_code]
                label.setText(label_text)

                if is_worked:
                    label.setStyleSheet(
                        f"color: {WAC_COLOR}; font-weight: bold;"
                    )
                else:
                    label.setStyleSheet("")

            # Update details table
            self.details_table.setRowCount(0)

            continents_order = ['NA', 'SA', 'EU', 'AF', 'AS', 'OC']
            for continent_code in continents_order:
                continent_name = CONTINENT_NAMES[continent_code]
                count = continent_details.get(continent_code, 0)

                row = self.details_table.rowCount()
                self.details_table.insertRow(row)

                # Continent name
                name_item = QTableWidgetItem(continent_name)
                name_item.setFont(QFont("Arial", 9))
                self.details_table.setItem(row, 0, name_item)

                # Contact count
                count_item = QTableWidgetItem(str(count))
                count_item.setFont(QFont("Arial", 9))
                if continent_code in continents_worked:
                    count_item.setForeground(QColor(WAC_COLOR))
                self.details_table.setItem(row, 1, count_item)

            # Update statistics
            self.continents_worked_label.setText(f"Continents Worked: {current}/6")

            total_contacts = sum(continent_details.values())
            self.total_contacts_label.setText(f"Total Qualifying Contacts: {total_contacts}")

            # Update missing continents
            if achieved:
                self.missing_label.setText("✅ All continents achieved!")
                self.missing_label.setStyleSheet(f"color: {WAC_COLOR}; font-weight: bold;")
            else:
                missing_continents = [
                    CONTINENT_NAMES[code]
                    for code in continents_order
                    if code not in continents_worked
                ]
                missing_text = "Missing: " + ", ".join(missing_continents)
                self.missing_label.setText(missing_text)
                self.missing_label.setStyleSheet("color: #666666;")

        except Exception as e:
            logger.error(f"Error refreshing WAC progress: {e}", exc_info=True)
            self.status_label.setText(f"Error: {str(e)}")

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
        }
