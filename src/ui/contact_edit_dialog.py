"""
Contact Edit Dialog

Dialog for editing QSO contact details and saving corrections.
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QPushButton, QMessageBox,
    QDateTimeEdit
)
from PyQt6.QtCore import Qt, QDateTime

from src.database.models import Contact
from src.database.repository import DatabaseRepository
from src.ui.dropdown_data import DropdownData
from src.utils.timezone_utils import get_utc_now

logger = logging.getLogger(__name__)


class ContactEditDialog(QDialog):
    """Dialog for editing contact details"""

    def __init__(self, contact: Contact, db: DatabaseRepository, parent: Optional[QDialog] = None):
        """
        Initialize contact edit dialog

        Args:
            contact: Contact object to edit
            db: Database repository instance
            parent: Parent widget
        """
        try:
            super().__init__(parent)
            self.contact = contact
            self.db = db
            self.dropdown_data = DropdownData()

            self.setWindowTitle(f"Edit QSO - {contact.callsign}")
            self.setGeometry(100, 100, 600, 700)
            self.setModal(True)

            self._init_ui()
            self._populate_fields()
            logger.info(f"ContactEditDialog initialized for {contact.callsign}")

        except Exception as e:
            logger.error(f"Error initializing ContactEditDialog: {e}", exc_info=True)
            raise

    def _init_ui(self) -> None:
        """Initialize UI components"""
        try:
            main_layout = QVBoxLayout()
            main_layout.setContentsMargins(10, 10, 10, 10)
            main_layout.setSpacing(8)

            # Create form grid
            form_layout = QGridLayout()
            form_layout.setSpacing(8)
            row = 0

            # Callsign
            form_layout.addWidget(QLabel("Callsign:"), row, 0)
            self.callsign_input = QLineEdit()
            self.callsign_input.setMinimumWidth(300)
            form_layout.addWidget(self.callsign_input, row, 1)
            row += 1

            # Date (read-only, informational)
            form_layout.addWidget(QLabel("Date (UTC):"), row, 0)
            self.date_input = QLineEdit()
            self.date_input.setReadOnly(True)
            self.date_input.setMinimumWidth(300)
            form_layout.addWidget(self.date_input, row, 1)
            row += 1

            # Time On
            form_layout.addWidget(QLabel("Time On (HHMM UTC):"), row, 0)
            self.time_on_input = QLineEdit()
            self.time_on_input.setPlaceholderText("e.g., 1430")
            self.time_on_input.setMaxLength(4)
            form_layout.addWidget(self.time_on_input, row, 1)
            row += 1

            # Time Off
            form_layout.addWidget(QLabel("Time Off (HHMM UTC):"), row, 0)
            self.time_off_input = QLineEdit()
            self.time_off_input.setPlaceholderText("e.g., 1445")
            self.time_off_input.setMaxLength(4)
            form_layout.addWidget(self.time_off_input, row, 1)
            row += 1

            # Band
            form_layout.addWidget(QLabel("Band:"), row, 0)
            self.band_combo = QComboBox()
            self.band_combo.addItems(self.dropdown_data.get_bands())
            form_layout.addWidget(self.band_combo, row, 1)
            row += 1

            # Mode
            form_layout.addWidget(QLabel("Mode:"), row, 0)
            self.mode_combo = QComboBox()
            self.mode_combo.addItems(self.dropdown_data.get_modes())
            form_layout.addWidget(self.mode_combo, row, 1)
            row += 1

            # Frequency
            form_layout.addWidget(QLabel("Frequency (MHz):"), row, 0)
            self.frequency_input = QDoubleSpinBox()
            self.frequency_input.setRange(0.1, 10000.0)
            self.frequency_input.setDecimals(5)
            self.frequency_input.setSingleStep(0.001)
            form_layout.addWidget(self.frequency_input, row, 1)
            row += 1

            # RST Sent
            form_layout.addWidget(QLabel("RST Sent:"), row, 0)
            self.rst_sent_input = QSpinBox()
            self.rst_sent_input.setRange(111, 599)
            form_layout.addWidget(self.rst_sent_input, row, 1)
            row += 1

            # RST Received
            form_layout.addWidget(QLabel("RST Received:"), row, 0)
            self.rst_rcvd_input = QSpinBox()
            self.rst_rcvd_input.setRange(111, 599)
            form_layout.addWidget(self.rst_rcvd_input, row, 1)
            row += 1

            # Country
            form_layout.addWidget(QLabel("Country:"), row, 0)
            self.country_combo = QComboBox()
            self.country_combo.addItems([""] + self.dropdown_data.get_countries())
            form_layout.addWidget(self.country_combo, row, 1)
            row += 1

            # State
            form_layout.addWidget(QLabel("State:"), row, 0)
            self.state_combo = QComboBox()
            self.state_combo.addItems([""] + self.dropdown_data.get_us_states())
            form_layout.addWidget(self.state_combo, row, 1)
            row += 1

            # Grid
            form_layout.addWidget(QLabel("Grid Square:"), row, 0)
            self.grid_input = QLineEdit()
            form_layout.addWidget(self.grid_input, row, 1)
            row += 1

            # QTH (City)
            form_layout.addWidget(QLabel("QTH/City:"), row, 0)
            self.qth_input = QLineEdit()
            form_layout.addWidget(self.qth_input, row, 1)
            row += 1

            # Operator Name
            form_layout.addWidget(QLabel("Operator Name:"), row, 0)
            self.name_input = QLineEdit()
            form_layout.addWidget(self.name_input, row, 1)
            row += 1

            # SKCC Number
            form_layout.addWidget(QLabel("SKCC Number:"), row, 0)
            self.skcc_number_input = QLineEdit()
            form_layout.addWidget(self.skcc_number_input, row, 1)
            row += 1

            # County
            form_layout.addWidget(QLabel("County:"), row, 0)
            self.county_input = QLineEdit()
            form_layout.addWidget(self.county_input, row, 1)
            row += 1

            # TX Power
            form_layout.addWidget(QLabel("TX Power (Watts):"), row, 0)
            self.power_input = QSpinBox()
            self.power_input.setRange(0, 1000)
            form_layout.addWidget(self.power_input, row, 1)
            row += 1

            # My Rig Make
            form_layout.addWidget(QLabel("My Rig Make:"), row, 0)
            self.my_rig_make_input = QLineEdit()
            self.my_rig_make_input.setPlaceholderText("e.g., Yaesu, Kenwood, ICOM")
            form_layout.addWidget(self.my_rig_make_input, row, 1)
            row += 1

            # My Rig Model
            form_layout.addWidget(QLabel("My Rig Model:"), row, 0)
            self.my_rig_model_input = QLineEdit()
            self.my_rig_model_input.setPlaceholderText("e.g., FT-891, TS-590SG")
            form_layout.addWidget(self.my_rig_model_input, row, 1)
            row += 1

            # My Antenna Make
            form_layout.addWidget(QLabel("My Antenna Make:"), row, 0)
            self.my_antenna_make_input = QLineEdit()
            self.my_antenna_make_input.setPlaceholderText("e.g., Yagi, Dipole, End-fed")
            form_layout.addWidget(self.my_antenna_make_input, row, 1)
            row += 1

            # My Antenna Model
            form_layout.addWidget(QLabel("My Antenna Model:"), row, 0)
            self.my_antenna_model_input = QLineEdit()
            self.my_antenna_model_input.setPlaceholderText("e.g., 3-element 40m, 80m Doublet")
            form_layout.addWidget(self.my_antenna_model_input, row, 1)
            row += 1

            main_layout.addLayout(form_layout)

            # Buttons
            button_layout = QHBoxLayout()
            
            # Delete button on the left
            delete_btn = QPushButton("Delete Contact")
            delete_btn.setStyleSheet("QPushButton { color: red; }")
            delete_btn.clicked.connect(self.delete_contact)
            button_layout.addWidget(delete_btn)
            
            button_layout.addStretch()

            save_btn = QPushButton("Save Changes")
            save_btn.clicked.connect(self.save_changes)
            button_layout.addWidget(save_btn)

            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(self.reject)
            button_layout.addWidget(cancel_btn)

            main_layout.addLayout(button_layout)

            self.setLayout(main_layout)
            logger.debug("UI initialization complete")

        except Exception as e:
            logger.error(f"Error initializing UI: {e}", exc_info=True)
            raise

    def _populate_fields(self) -> None:
        """Populate form fields with contact data"""
        try:
            self.callsign_input.setText(self.contact.callsign or "")
            self.date_input.setText(self._format_date(self.contact.qso_date))
            self.time_on_input.setText(self.contact.time_on or "")
            self.time_off_input.setText(self.contact.time_off or "")
            self.band_combo.setCurrentText(self.contact.band or "")
            self.mode_combo.setCurrentText(self.contact.mode or "")
            self.frequency_input.setValue(self.contact.frequency or 0.0)
            self.rst_sent_input.setValue(int(self.contact.rst_sent) if self.contact.rst_sent else 599)
            self.rst_rcvd_input.setValue(int(self.contact.rst_rcvd) if self.contact.rst_rcvd else 599)
            self.country_combo.setCurrentText(self.contact.country or "")
            self.state_combo.setCurrentText(self.contact.state or "")
            self.grid_input.setText(self.contact.gridsquare or "")
            self.qth_input.setText(self.contact.qth or "")
            self.name_input.setText(self.contact.name or "")
            self.skcc_number_input.setText(self.contact.skcc_number or "")
            self.county_input.setText(self.contact.county or "")
            self.power_input.setValue(int(self.contact.tx_power or 0))
            self.my_rig_make_input.setText(self.contact.my_rig_make or "")
            self.my_rig_model_input.setText(self.contact.my_rig_model or "")
            self.my_antenna_make_input.setText(self.contact.my_antenna_make or "")
            self.my_antenna_model_input.setText(self.contact.my_antenna_model or "")

            logger.debug(f"Form fields populated for {self.contact.callsign}")
        except Exception as e:
            logger.error(f"Error populating fields: {e}", exc_info=True)

    def _format_date(self, qso_date: Optional[str]) -> str:
        """Format date from YYYYMMDD to YYYY-MM-DD"""
        if not qso_date or len(qso_date) != 8:
            return "-"
        return f"{qso_date[0:4]}-{qso_date[4:6]}-{qso_date[6:8]}"

    def save_changes(self) -> None:
        """Save changes to the contact"""
        try:
            # Validate inputs
            if not self.callsign_input.text().strip():
                QMessageBox.warning(self, "Validation Error", "Callsign is required")
                return

            # Prepare updates dictionary
            updates = {
                'callsign': self.callsign_input.text().strip().upper(),
                'time_on': self.time_on_input.text().strip() or None,
                'time_off': self.time_off_input.text().strip() or None,
                'band': self.band_combo.currentText() or None,
                'mode': self.mode_combo.currentText() or None,
                'frequency': self.frequency_input.value() if self.frequency_input.value() > 0 else None,
                'rst_sent': str(self.rst_sent_input.value()) if self.rst_sent_input.value() else None,
                'rst_rcvd': str(self.rst_rcvd_input.value()) if self.rst_rcvd_input.value() else None,
                'country': self.country_combo.currentText() or None,
                'state': self.state_combo.currentText() or None,
                'gridsquare': self.grid_input.text().strip() or None,
                'qth': self.qth_input.text().strip() or None,
                'name': self.name_input.text().strip() or None,
                'skcc_number': self.skcc_number_input.text().strip() or None,
                'county': self.county_input.text().strip() or None,
                'tx_power': self.power_input.value() if self.power_input.value() > 0 else None,
                'my_rig_make': self.my_rig_make_input.text().strip() or None,
                'my_rig_model': self.my_rig_model_input.text().strip() or None,
                'my_antenna_make': self.my_antenna_make_input.text().strip() or None,
                'my_antenna_model': self.my_antenna_model_input.text().strip() or None,
            }

            try:
                # Save to database using contact's ID
                if not self.contact.id:
                    raise ValueError("Contact ID is missing")

                self.db.update_contact(self.contact.id, **updates)
                logger.info(f"Contact saved: {updates['callsign']}")
                QMessageBox.information(self, "Success", "Contact updated successfully")
                self.accept()

            except Exception as e:
                logger.error(f"Error saving contact to database: {e}", exc_info=True)
                QMessageBox.critical(self, "Database Error", f"Failed to save contact: {str(e)}")

        except Exception as e:
            logger.error(f"Error in save_changes: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def delete_contact(self) -> None:
        """Delete the contact after confirmation"""
        try:
            # Confirm deletion
            reply = QMessageBox.question(
                self,
                "Delete Contact",
                f"Are you sure you want to delete this contact?\n\n"
                f"Callsign: {self.contact.callsign}\n"
                f"Date: {self._format_date(self.contact.qso_date)}\n"
                f"Time: {self.contact.time_on}\n"
                f"Band: {self.contact.band}\n"
                f"Mode: {self.contact.mode}\n\n"
                f"This action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                try:
                    if not self.contact.id:
                        raise ValueError("Contact ID is missing")

                    # Delete from database
                    success = self.db.delete_contact(self.contact.id)
                    
                    if success:
                        logger.info(f"Contact deleted: {self.contact.callsign} (ID: {self.contact.id})")
                        QMessageBox.information(self, "Success", "Contact deleted successfully")
                        self.accept()  # Close dialog with success status
                    else:
                        QMessageBox.warning(self, "Error", "Failed to delete contact")

                except Exception as e:
                    logger.error(f"Error deleting contact from database: {e}", exc_info=True)
                    QMessageBox.critical(self, "Database Error", f"Failed to delete contact: {str(e)}")

        except Exception as e:
            logger.error(f"Error in delete_contact: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
