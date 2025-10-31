"""
Previous QSOs Display Widget

Shows a list of previous QSO contacts with the same callsign.
"""

import logging
from typing import List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QLabel
)
from PyQt6.QtCore import Qt, QDateTime, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QFont

from src.database.models import Contact
from src.database.repository import DatabaseRepository
from src.utils.timezone_utils import format_utc_time_for_display

logger = logging.getLogger(__name__)


class ContactLookupWorker(QObject):
    """Worker to perform database lookups in background thread"""

    finished = pyqtSignal(str, list)  # callsign, contacts
    error = pyqtSignal(str, str)  # callsign, error_message

    def __init__(self, db: DatabaseRepository):
        super().__init__()
        self.db = db
        self.callsign = ""

    def lookup_contacts(self, callsign: str):
        """Perform the contact lookup"""
        self.callsign = callsign
        try:
            contacts = self.db.get_contacts_by_callsign(callsign)
            self.finished.emit(callsign, contacts)
        except Exception as e:
            logger.error(f"Error in background contact lookup for {callsign}: {e}", exc_info=True)
            self.error.emit(callsign, str(e))


class PreviousQSOsWidget(QWidget):
    """Widget to display previous QSOs with a specific callsign"""

    def __init__(self, db: DatabaseRepository, parent: Optional[QWidget] = None):
        """
        Initialize previous QSOs widget

        Args:
            db: Database repository instance
            parent: Parent widget

        Raises:
            TypeError: If db is not a DatabaseRepository instance
        """
        try:
            super().__init__(parent)

            # Validate database
            if db is None:
                raise TypeError("db cannot be None")
            if not isinstance(db, DatabaseRepository):
                raise TypeError(f"db must be DatabaseRepository, got {type(db).__name__}")

            self.db = db
            self.current_callsign = ""

            # Setup background thread for database queries
            self.worker_thread = QThread()
            self.worker = ContactLookupWorker(db)
            self.worker.moveToThread(self.worker_thread)

            # Connect signals
            self.worker.finished.connect(self._on_lookup_finished)
            self.worker.error.connect(self._on_lookup_error)

            # Start worker thread
            self.worker_thread.start()

            self._init_ui()
            logger.info("PreviousQSOsWidget initialized successfully with background thread")

        except (TypeError, Exception) as e:
            logger.error(f"Error initializing PreviousQSOsWidget: {e}", exc_info=True)
            raise

    def _init_ui(self) -> None:
        """Initialize UI components"""
        try:
            layout = QVBoxLayout()
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(5)

            # Title label
            title_label = QLabel("Previous QSOs")
            title_font = title_label.font()
            title_font.setPointSize(int(title_font.pointSize() * 1.15))
            title_font.setBold(True)
            title_label.setFont(title_font)
            layout.addWidget(title_label)

            # Create table for previous QSOs
            self.qsos_table = QTableWidget()
            self.qsos_table.setColumnCount(9)
            self.qsos_table.setHorizontalHeaderLabels([
                "Date", "Time (UTC)", "Band", "Mode", "Freq", "RST", "SKCC #", "State", "City/QTH"
            ])

            # Configure table appearance
            self.qsos_table.horizontalHeader().setStretchLastSection(True)
            self.qsos_table.setSelectionBehavior(
                QTableWidget.SelectionBehavior.SelectRows
            )
            self.qsos_table.setAlternatingRowColors(True)
            self.qsos_table.setMaximumHeight(200)  # Limit height to show in sidebar

            # Set column widths
            self.qsos_table.setColumnWidth(0, 100)  # Date (wider for better visibility)
            self.qsos_table.setColumnWidth(1, 85)   # Time
            self.qsos_table.setColumnWidth(2, 55)   # Band
            self.qsos_table.setColumnWidth(3, 50)   # Mode
            self.qsos_table.setColumnWidth(4, 70)   # Frequency
            self.qsos_table.setColumnWidth(5, 50)   # RST
            self.qsos_table.setColumnWidth(6, 70)   # SKCC #
            self.qsos_table.setColumnWidth(7, 60)   # State
            self.qsos_table.setColumnWidth(8, 90)   # City/QTH

            layout.addWidget(self.qsos_table, 1)

            # No QSOs message (shown when no previous QSOs exist)
            self.no_qsos_label = QLabel("No previous QSOs with this callsign")
            self.no_qsos_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.no_qsos_label.setStyleSheet("color: #666666; font-style: italic;")
            layout.addWidget(self.no_qsos_label)
            self.no_qsos_label.hide()

            self.setLayout(layout)
            logger.debug("UI initialization complete")

        except Exception as e:
            logger.error(f"Error initializing UI: {e}", exc_info=True)
            raise

    def update_callsign(self, callsign: str) -> None:
        """
        Update the displayed QSOs for a given callsign (non-blocking)

        Args:
            callsign: The callsign to look up
        """
        try:
            callsign = callsign.strip().upper()
            self.current_callsign = callsign

            if not callsign:
                # Clear the table if callsign is empty
                self.qsos_table.setRowCount(0)
                self.no_qsos_label.setText("No callsign entered")
                self.qsos_table.hide()
                self.no_qsos_label.show()
                logger.debug("Callsign cleared - table cleared")
                return

            # Show loading indicator
            self.qsos_table.setRowCount(0)
            self.no_qsos_label.setText(f"Loading QSOs for {callsign}...")
            self.qsos_table.hide()
            self.no_qsos_label.show()

            # Trigger background lookup
            self.worker.lookup_contacts(callsign)
            logger.debug(f"Background lookup started for {callsign}")

        except Exception as e:
            logger.error(f"Error in update_callsign: {e}", exc_info=True)

    def _on_lookup_finished(self, callsign: str, contacts: List[Contact]) -> None:
        """
        Handle completion of background contact lookup

        Args:
            callsign: The callsign that was looked up
            contacts: List of contacts found
        """
        try:
            # Only update if this is still the current callsign
            if callsign != self.current_callsign:
                logger.debug(f"Ignoring stale lookup result for {callsign} (current: {self.current_callsign})")
                return

            if not contacts:
                # No previous QSOs
                self.qsos_table.setRowCount(0)
                self.no_qsos_label.setText(f"No previous QSOs with {callsign}")
                self.qsos_table.hide()
                self.no_qsos_label.show()
                logger.debug(f"No previous QSOs found for {callsign}")
                return

            # Populate table with contacts
            self._populate_table(contacts)
            self.qsos_table.show()
            self.no_qsos_label.hide()
            logger.debug(f"Populated table with {len(contacts)} QSOs for {callsign}")

        except Exception as e:
            logger.error(f"Error handling lookup result for {callsign}: {e}", exc_info=True)

    def _on_lookup_error(self, callsign: str, error_msg: str) -> None:
        """
        Handle error from background contact lookup

        Args:
            callsign: The callsign that was being looked up
            error_msg: Error message
        """
        # Only update if this is still the current callsign
        if callsign != self.current_callsign:
            return

        self.qsos_table.setRowCount(0)
        self.no_qsos_label.setText("Error loading previous QSOs")
        self.qsos_table.hide()
        self.no_qsos_label.show()
        logger.error(f"Error loading QSOs for {callsign}: {error_msg}")

    def _populate_table(self, contacts: List[Contact]) -> None:
        """
        Populate the table with contact information

        Args:
            contacts: List of Contact objects to display
        """
        try:
            # Sort contacts by date/time (most recent first)
            sorted_contacts = sorted(
                contacts,
                key=lambda c: (c.qso_date or "", c.time_on or ""),
                reverse=True
            )

            self.qsos_table.setRowCount(len(sorted_contacts))

            for row, contact in enumerate(sorted_contacts):
                try:
                    # Date
                    date_text = contact.qso_date if contact.qso_date else "-"
                    if date_text and len(date_text) == 8:  # YYYYMMDD format
                        date_text = f"{date_text[0:4]}-{date_text[4:6]}-{date_text[6:8]}"
                    date_item = QTableWidgetItem(date_text)
                    date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    # Make date bold for better visibility
                    date_font = date_item.font()
                    date_font.setBold(True)
                    date_item.setFont(date_font)
                    self.qsos_table.setItem(row, 0, date_item)

                    # Time
                    time_text = contact.time_on if contact.time_on else "-"
                    if time_text and len(time_text) == 4:  # HHMM format
                        time_text = f"{time_text[0:2]}:{time_text[2:4]}"
                    time_item = QTableWidgetItem(time_text)
                    time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.qsos_table.setItem(row, 1, time_item)

                    # Band
                    band_item = QTableWidgetItem(contact.band or "-")
                    band_item.setFlags(band_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.qsos_table.setItem(row, 2, band_item)

                    # Mode
                    mode_item = QTableWidgetItem(contact.mode or "-")
                    mode_item.setFlags(mode_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.qsos_table.setItem(row, 3, mode_item)

                    # Frequency
                    freq_text = f"{contact.frequency:.5f}" if contact.frequency else "-"
                    freq_item = QTableWidgetItem(freq_text)
                    freq_item.setFlags(freq_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.qsos_table.setItem(row, 4, freq_item)

                    # RST (show sent/received)
                    rst_text = ""
                    if contact.rst_sent:
                        rst_text = f"S:{contact.rst_sent}"
                    if contact.rst_rcvd:
                        if rst_text:
                            rst_text += f" R:{contact.rst_rcvd}"
                        else:
                            rst_text = f"R:{contact.rst_rcvd}"
                    if not rst_text:
                        rst_text = "-"

                    rst_item = QTableWidgetItem(rst_text)
                    rst_item.setFlags(rst_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.qsos_table.setItem(row, 5, rst_item)

                    # SKCC Number
                    skcc_text = contact.skcc_number if contact.skcc_number else "-"
                    skcc_item = QTableWidgetItem(skcc_text)
                    skcc_item.setFlags(skcc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.qsos_table.setItem(row, 6, skcc_item)

                    # State
                    state_text = contact.state if contact.state else "-"
                    state_item = QTableWidgetItem(state_text)
                    state_item.setFlags(state_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.qsos_table.setItem(row, 7, state_item)

                    # City/QTH
                    qth_text = contact.qth if contact.qth else "-"
                    qth_item = QTableWidgetItem(qth_text)
                    qth_item.setFlags(qth_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.qsos_table.setItem(row, 8, qth_item)

                except Exception as e:
                    logger.error(f"Error populating row {row}: {e}", exc_info=True)

            logger.debug(f"Successfully populated table with {len(sorted_contacts)} rows")

        except Exception as e:
            logger.error(f"Error in _populate_table: {e}", exc_info=True)
            raise

    def closeEvent(self, event):
        """Clean up worker thread when widget is closed"""
        try:
            if hasattr(self, 'worker_thread') and self.worker_thread.isRunning():
                self.worker_thread.quit()
                self.worker_thread.wait()
                logger.info("Previous QSOs worker thread stopped")
        except Exception as e:
            logger.error(f"Error stopping worker thread: {e}", exc_info=True)
        finally:
            event.accept()
