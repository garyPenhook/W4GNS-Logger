"""
Contacts List Widget

Displays all contacts in a searchable, sortable table view.
"""

import logging
from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QComboBox, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from src.database.repository import DatabaseRepository
from src.database.models import Contact
from src.ui.signals import get_app_signals

logger = logging.getLogger(__name__)


class ContactsListWidget(QWidget):
    """Displays all contacts in a table view"""

    def __init__(self, db: DatabaseRepository, parent: Optional[QWidget] = None):
        """
        Initialize contacts list widget

        Args:
            db: Database repository instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.db = db
        self.contacts: List[Contact] = []

        # Pagination state
        self.current_offset = 0
        self.page_size = 10000  # Load all contacts at once (10000 is effectively unlimited for 201 contacts)
        self.total_contacts = 0

        self._init_ui()
        self.refresh()

        # Connect to signals instead of using polling timer
        signals = get_app_signals()
        signals.contacts_changed.connect(self.refresh)
        signals.contact_added.connect(self.refresh)
        signals.contact_modified.connect(self.refresh)
        signals.contact_deleted.connect(self.refresh)

    def _init_ui(self) -> None:
        """Initialize UI components"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)

        # Search and filter section
        search_group = self._create_search_section()
        main_layout.addWidget(search_group)

        # Statistics section
        stats_group = self._create_stats_section()
        main_layout.addWidget(stats_group)

        # Contacts table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Callsign", "Date (UTC)", "Time (UTC)", "Band", "Mode", "SKCC", "Power"
        ])
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(1, 90)
        self.table.setColumnWidth(2, 60)
        self.table.setColumnWidth(3, 70)
        self.table.setColumnWidth(4, 60)
        self.table.setColumnWidth(5, 100)
        self.table.setColumnWidth(6, 70)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        main_layout.addWidget(self.table, 1)  # Give table stretch factor of 1

        # Pagination controls
        pagination_layout = QHBoxLayout()
        self.pagination_label = QLabel("Page 1")
        self.pagination_label.setFont(QFont("Arial", 9))
        self.pagination_label.hide()  # Hide - pagination not needed with all contacts loaded at once
        pagination_layout.addWidget(self.pagination_label)

        self.load_more_btn = QPushButton("Load More Contacts")
        self.load_more_btn.clicked.connect(self.load_next_page)
        self.load_more_btn.hide()  # Hide - all contacts load at once now
        pagination_layout.addWidget(self.load_more_btn)

        pagination_layout.addStretch()
        main_layout.addLayout(pagination_layout)

        self.setLayout(main_layout)

    def _create_search_section(self) -> QGroupBox:
        """Create search and filter section"""
        group = QGroupBox("Search & Filter")
        layout = QHBoxLayout()

        # Callsign search
        layout.addWidget(QLabel("Callsign:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search callsigns...")
        self.search_input.textChanged.connect(self.refresh)
        layout.addWidget(self.search_input)

        # Band filter
        layout.addWidget(QLabel("Band:"))
        self.band_filter = QComboBox()
        self.band_filter.addItem("All Bands", None)
        self.band_filter.addItems(self._get_available_bands())
        self.band_filter.currentIndexChanged.connect(self.refresh)
        layout.addWidget(self.band_filter)

        # Mode filter
        layout.addWidget(QLabel("Mode:"))
        self.mode_filter = QComboBox()
        self.mode_filter.addItem("All Modes", None)
        self.mode_filter.addItems(self._get_available_modes())
        self.mode_filter.currentIndexChanged.connect(self.refresh)
        layout.addWidget(self.mode_filter)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def _create_stats_section(self) -> QGroupBox:
        """Create statistics section"""
        group = QGroupBox("Statistics")
        layout = QHBoxLayout()

        self.total_label = QLabel("Total: 0")
        self.total_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(self.total_label)

        layout.addSpacing(20)

        self.filtered_label = QLabel("Displayed: 0")
        self.filtered_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(self.filtered_label)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def refresh(self) -> None:
        """Refresh the contacts table"""
        try:
            # Reset to first page on refresh
            self.current_offset = 0

            try:
                # Get contacts for current page
                self.contacts = self.db.get_all_contacts(limit=self.page_size, offset=self.current_offset)

                # Get total contact count for statistics
                self.total_contacts = self.db.get_contact_count()
            except Exception as db_error:
                logger.error(f"Database error refreshing contacts: {db_error}", exc_info=True)
                self.contacts = []
                self.total_contacts = 0

            # Apply filters
            filtered = self._apply_filters()

            # Update statistics
            total_pages = (self.total_contacts + self.page_size - 1) // self.page_size if self.total_contacts > 0 else 1
            self.total_label.setText(f"Total: {self.total_contacts}")
            self.filtered_label.setText(f"Displayed: {len(filtered)}")
            self.pagination_label.setText(f"Page 1 of {total_pages}")

            # Update table (clear and reload)
            self._populate_table(filtered, clear_existing=True)

            # Update load more button state
            self._update_load_more_button()

        except Exception as e:
            logger.error(f"Unexpected error refreshing contacts: {e}", exc_info=True)
            # Show error to user if possible
            self.table.setRowCount(0)

    def load_next_page(self) -> None:
        """Load the next page of contacts"""
        try:
            # Move to next page
            self.current_offset += self.page_size

            try:
                # Get contacts for next page
                next_contacts = self.db.get_all_contacts(limit=self.page_size, offset=self.current_offset)
            except Exception as db_error:
                logger.error(f"Database error loading next page: {db_error}", exc_info=True)
                return

            if not next_contacts:
                logger.info("No more contacts to load")
                return

            # Add to existing contacts
            self.contacts.extend(next_contacts)

            # Apply filters (but only display the new page's contacts, not reload old ones)
            # Get current filters
            search_text = self.search_input.text().strip()
            band_filter = self.band_filter.currentData()
            mode_filter = self.mode_filter.currentData()

            # Apply filters only to the new contacts
            filtered_new = next_contacts
            if search_text:
                filtered_new = [c for c in filtered_new if search_text.lower() in c.callsign.lower()]
            if band_filter:
                filtered_new = [c for c in filtered_new if c.band == band_filter]
            if mode_filter:
                filtered_new = [c for c in filtered_new if c.mode == mode_filter]

            # Update pagination label
            current_page = (self.current_offset // self.page_size) + 1
            total_pages = (self.total_contacts + self.page_size - 1) // self.page_size
            self.pagination_label.setText(f"Page {current_page} of {total_pages}")

            # Append only the NEW filtered contacts to table
            self._populate_table(filtered_new, clear_existing=False)

            # Update displayed count
            self.filtered_label.setText(f"Displayed: {self.table.rowCount()}")

            # Update load more button state
            self._update_load_more_button()

        except Exception as e:
            logger.error(f"Unexpected error loading next page: {e}", exc_info=True)

    def _update_load_more_button(self) -> None:
        """Update load more button state"""
        total_displayed = self.table.rowCount()
        can_load_more = self.current_offset + self.page_size < self.total_contacts
        self.load_more_btn.setEnabled(can_load_more)
        if can_load_more:
            remaining = self.total_contacts - total_displayed
            self.load_more_btn.setText(f"Load More ({remaining} remaining)")
        else:
            self.load_more_btn.setText("All Contacts Loaded")

    def _apply_filters(self) -> List[Contact]:
        """Apply search and filter criteria"""
        filtered = self.contacts

        # Callsign search
        search_text = self.search_input.text().strip()
        if search_text:
            filtered = [
                c for c in filtered
                if search_text.lower() in c.callsign.lower()
            ]

        # Band filter
        band_filter = self.band_filter.currentData()
        if band_filter:
            filtered = [c for c in filtered if c.band == band_filter]

        # Mode filter
        mode_filter = self.mode_filter.currentData()
        if mode_filter:
            filtered = [c for c in filtered if c.mode == mode_filter]

        return filtered

    def _populate_table(self, contacts: List[Contact], clear_existing: bool = True) -> None:
        """
        Populate the table with contacts.

        Args:
            contacts: List of contacts to display
            clear_existing: If True, clear existing rows. If False, append new rows.
        """
        if clear_existing:
            self.table.setRowCount(0)
            start_row = 0
        else:
            start_row = self.table.rowCount()
            self.table.setRowCount(start_row + len(contacts))

        for offset, contact in enumerate(contacts):
            row = start_row + offset
            # Callsign
            self.table.setItem(row, 0, QTableWidgetItem(contact.callsign))

            # Date
            date_str = contact.qso_date
            if len(date_str) == 8:
                date_str = f"{date_str[4:6]}/{date_str[6:8]}/{date_str[:4]}"
            self.table.setItem(row, 1, QTableWidgetItem(date_str))

            # Time
            time_str = contact.time_on or ""
            if len(time_str) == 4:
                time_str = f"{time_str[:2]}:{time_str[2:]}"
            self.table.setItem(row, 2, QTableWidgetItem(time_str))

            # Band
            self.table.setItem(row, 3, QTableWidgetItem(contact.band or ""))

            # Mode
            self.table.setItem(row, 4, QTableWidgetItem(contact.mode or ""))

            # SKCC
            skcc_str = contact.skcc_number or ""
            self.table.setItem(row, 5, QTableWidgetItem(skcc_str))

            # Power
            power_str = ""
            if contact.tx_power is not None:
                power_str = f"{contact.tx_power}W"
            self.table.setItem(row, 6, QTableWidgetItem(power_str))

    def _get_available_bands(self) -> List[str]:
        """Get list of available bands from contacts"""
        try:
            bands = set()
            for contact in self.contacts:
                if contact.band:
                    bands.add(contact.band)
            return sorted(list(bands))
        except Exception:
            return []

    def _get_available_modes(self) -> List[str]:
        """Get list of available modes from contacts"""
        try:
            modes = set()
            for contact in self.contacts:
                if contact.mode:
                    modes.add(contact.mode)
            return sorted(list(modes))
        except Exception:
            return []
