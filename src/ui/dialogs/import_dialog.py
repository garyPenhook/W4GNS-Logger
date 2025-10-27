"""
ADIF Import Dialog

Handles importing contacts from ADIF files.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QProgressBar, QTextEdit, QGroupBox, QFileDialog,
    QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from src.database.repository import DatabaseRepository
from src.adif.parser import ADIFParser

logger = logging.getLogger(__name__)


class ImportWorkerThread(QThread):
    """Worker thread for importing ADIF files"""

    progress = pyqtSignal(int)  # Progress percentage
    status = pyqtSignal(str)  # Status message
    finished = pyqtSignal(dict)  # Import statistics

    def __init__(
        self,
        file_path: str,
        db: DatabaseRepository,
        conflict_strategy: str,
        clear_db: bool = False
    ):
        super().__init__()
        self.file_path = file_path
        self.db = db
        self.conflict_strategy = conflict_strategy
        self.clear_db = clear_db

    def run(self):
        """Run the import process"""
        try:
            # Clear database if requested
            if self.clear_db:
                self.status.emit("Clearing existing contacts...")
                self.progress.emit(5)
                self._clear_database()

            self.status.emit("Parsing ADIF file...")
            self.progress.emit(10)

            # Parse ADIF file - returns tuple of (records, header)
            parser = ADIFParser()
            records, header = parser.parse_file(self.file_path)

            if not records:
                errors = parser.errors if hasattr(parser, 'errors') else []
                self.finished.emit({
                    "imported": 0,
                    "updated": 0,
                    "skipped": 0,
                    "failed": len(errors),
                    "errors": [str(e) for e in errors]
                })
                return

            self.progress.emit(30)
            self.status.emit(f"Found {len(records)} records. Importing...")

            # Convert ADIF records to contact format
            # The parser returns records as dictionaries with ADIF field names
            # We need to map them back to database field names
            records = self._map_adif_records(records)

            self.progress.emit(50)
            self.status.emit(f"Cleaning {len(records)} records...")

            # Import into database
            # The repository's import_contacts_from_adif will automatically clean the data
            stats = self.db.import_contacts_from_adif(
                records,
                conflict_strategy=self.conflict_strategy
            )

            self.progress.emit(90)
            self.status.emit("Import complete!")
            self.progress.emit(100)

            self.finished.emit(stats)

        except Exception as e:
            logger.error(f"Import error: {e}")
            self.finished.emit({
                "imported": 0,
                "updated": 0,
                "skipped": 0,
                "failed": 1,
                "errors": [str(e)]
            })

    def _clear_database(self) -> None:
        """Clear all contacts from the database"""
        try:
            session = self.db.get_session()
            from src.database.models import Contact
            session.query(Contact).delete()
            session.commit()
            logger.info("Database cleared - all contacts removed")
        except Exception as e:
            logger.error(f"Error clearing database: {e}")
            raise
        finally:
            session.close()

    def _map_adif_records(self, adif_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Map ADIF field names to database field names

        Args:
            adif_records: List of records with ADIF field names (uppercase)

        Returns:
            List of records with database field names (lowercase)
        """
        # Map ADIF field names to database field names (reverse of exporter)
        adif_to_db = {
            'CALL': 'callsign',
            'QSO_DATE': 'qso_date',
            'TIME_ON': 'time_on',
            'TIME_OFF': 'time_off',
            'BAND': 'band',
            'FREQ': 'frequency',
            'FREQ_RX': 'freq_rx',
            'MODE': 'mode',
            'RST_SENT': 'rst_sent',
            'RST_RCVD': 'rst_rcvd',
            'TX_PWR': 'tx_power',
            'RX_PWR': 'rx_power',

            'MY_GRIDSQUARE': 'my_gridsquare',
            'GRIDSQUARE': 'gridsquare',
            'MY_CITY': 'my_city',
            'MY_COUNTRY': 'my_country',
            'MY_STATE': 'my_state',
            'NAME': 'name',
            'QTH': 'qth',
            'COUNTRY': 'country',

            'DXCC': 'dxcc',
            'CQZ': 'cqz',
            'ITUZ': 'ituz',
            'STATE': 'state',
            'COUNTY': 'county',
            'ARRL_SECT': 'arrl_sect',
            'IOTA': 'iota',
            'IOTA_ISLAND_ID': 'iota_island_id',
            'SOTA_REF': 'sota_ref',
            'POTA_REF': 'pota_ref',
            'VUCC_GRIDS': 'vucc_grids',

            'OPERATOR': 'operator',
            'STATION_CALLSIGN': 'station_callsign',
            'MY_RIG': 'my_rig',
            'MY_RIG_MAKE': 'my_rig_make',
            'MY_RIG_MODEL': 'my_rig_model',
            'RIG_MAKE': 'rig_make',
            'RIG_MODEL': 'rig_model',
            'MY_ANTENNA': 'my_antenna',
            'MY_ANTENNA_MAKE': 'my_antenna_make',
            'MY_ANTENNA_MODEL': 'my_antenna_model',
            'ANT_MAKE': 'antenna_make',
            'ANT_MODEL': 'antenna_model',

            'SKCC': 'skcc_number',
            'KEY_TYPE': 'key_type',
            'APP_SKCCLOGGER_KEYTYPE': 'key_type',  # Custom SKCC Logger field for key type

            'PROPAGATION_MODE': 'propagation_mode',
            'SAT_NAME': 'sat_name',
            'SAT_MODE': 'sat_mode',
            'A_INDEX': 'a_index',
            'K_INDEX': 'k_index',
            'SFI': 'sfi',
            'ANTENNA_AZ': 'antenna_az',
            'ANTENNA_EL': 'antenna_el',
            'DISTANCE': 'distance',
            'LATITUDE': 'latitude',
            'LONGITUDE': 'longitude',

            'QSL_RCVD': 'qsl_rcvd',
            'QSL_SENT': 'qsl_sent',
            'QSL_RCVD_DATE': 'qsl_rcvd_date',
            'QSL_SENT_DATE': 'qsl_sent_date',
            'QSL_VIA': 'qsl_via',
            'LOTW_QSL_RCVD': 'lotw_qsl_rcvd',
            'LOTW_QSL_SENT': 'lotw_qsl_sent',
            'EQSL_QSL_RCVD': 'eqsl_qsl_rcvd',
            'EQSL_QSL_SENT': 'eqsl_qsl_sent',
            'CLUBLOG_QSO_UPLOAD_STATUS': 'clublog_status',

            'NOTES': 'notes',
            'COMMENT': 'comment',
            'QSLMSG': 'qslmsg',

            'CONTEST_ID': 'contest_id',
            'CLASS': 'class_field',
            'CHECK': 'check',
        }

        mapped_records = []
        for record in adif_records:
            mapped = {}
            for adif_key, value in record.items():
                db_key = adif_to_db.get(adif_key)
                if db_key:
                    mapped[db_key] = value
                else:
                    # Include unmapped fields as-is (might be custom fields)
                    mapped[adif_key.lower()] = value

            # Normalize key_type field: convert SKCC Logger abbreviations to standard names
            if 'key_type' in mapped and mapped['key_type']:
                key_type = mapped['key_type'].upper().strip()
                # SKCC Logger uses: SK, BUG, SS
                # Standard uses: STRAIGHT, BUG, SIDESWIPER
                if key_type == 'SK':
                    mapped['key_type'] = 'STRAIGHT'
                elif key_type == 'SS':
                    mapped['key_type'] = 'SIDESWIPER'
                elif key_type == 'BUG':
                    mapped['key_type'] = 'BUG'  # Already correct
                else:
                    mapped['key_type'] = key_type.upper()  # Keep other values as-is

            mapped_records.append(mapped)

        return mapped_records


class ImportDialog(QDialog):
    """Dialog for importing ADIF files"""

    def __init__(
        self,
        db: DatabaseRepository,
        parent: Optional[QDialog] = None
    ):
        """
        Initialize import dialog

        Args:
            db: Database repository instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.db = db
        self.import_file = None
        self.import_thread = None

        self.setWindowTitle("Import ADIF Contacts")
        self.setGeometry(100, 100, 600, 500)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize UI components"""
        main_layout = QVBoxLayout()

        # File selection section
        file_layout = QHBoxLayout()
        file_label = QLabel("ADIF File:")
        self.file_input = QLabel("(No file selected)")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_input, 1)
        file_layout.addWidget(browse_btn)
        main_layout.addLayout(file_layout)

        # Conflict strategy section
        strategy_layout = QVBoxLayout()
        strategy_label = QLabel("If duplicates found:")
        strategy_combo_layout = QHBoxLayout()
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItem("Skip duplicates", "skip")
        self.strategy_combo.addItem("Update existing", "update")
        self.strategy_combo.addItem("Add all", "append")
        self.strategy_combo.setCurrentIndex(1)  # Default to "Update existing"
        strategy_combo_layout.addWidget(strategy_label)
        strategy_combo_layout.addWidget(self.strategy_combo, 1)
        strategy_layout.addLayout(strategy_combo_layout)

        # Strategy info
        strategy_info = QLabel(
            "• Skip: Don't import duplicates (same callsign, date, time, band)\n"
            "• Update: Overwrite existing contacts with new data\n"
            "• Add all: Import everything, even duplicates"
        )
        strategy_info.setStyleSheet("color: gray; font-size: 10px;")
        strategy_layout.addWidget(strategy_info)

        # Clear database checkbox
        self.clear_db_checkbox = QCheckBox("Clear all existing contacts before importing")
        strategy_layout.addWidget(self.clear_db_checkbox)

        main_layout.addLayout(strategy_layout)

        # Progress section
        progress_group = QGroupBox("Import Progress")
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.status_label = QLabel("Ready to import")
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)

        # Results section
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout()
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(150)
        results_layout.addWidget(self.results_text)
        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)

        # Buttons section
        button_layout = QHBoxLayout()
        self.import_btn = QPushButton("Import")
        self.import_btn.clicked.connect(self._start_import)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.import_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def _browse_file(self) -> None:
        """Open file browser to select ADIF file"""
        file_filter = "ADIF Files (*.adif *.adi *.adx);;Text Files (*.txt);;All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ADIF File",
            "",
            file_filter
        )

        if file_path:
            self.import_file = file_path
            self.file_input.setText(Path(file_path).name)
            self.results_text.clear()
            self.progress_bar.setValue(0)

    def _start_import(self) -> None:
        """Start the import process"""
        if not self.import_file:
            QMessageBox.warning(self, "No File", "Please select an ADIF file first.")
            return

        # Check if clearing database
        if self.clear_db_checkbox.isChecked():
            reply = QMessageBox.warning(
                self,
                "Clear Database?",
                "This will delete ALL existing contacts. Are you sure?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # Disable import button during import
        self.import_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.results_text.clear()

        # Get conflict strategy and clear flag
        strategy = self.strategy_combo.currentData()
        clear_db = self.clear_db_checkbox.isChecked()

        # Create and start worker thread
        self.import_thread = ImportWorkerThread(
            self.import_file,
            self.db,
            strategy,
            clear_db=clear_db
        )
        self.import_thread.progress.connect(self._on_progress)
        self.import_thread.status.connect(self._on_status)
        self.import_thread.finished.connect(self._on_import_finished)
        self.import_thread.start()

    def _on_progress(self, value: int) -> None:
        """Handle progress update

        Args:
            value: Progress percentage (0-100)
        """
        self.progress_bar.setValue(value)

    def _on_status(self, message: str) -> None:
        """Handle status update

        Args:
            message: Status message
        """
        self.status_label.setText(message)

    def _on_import_finished(self, stats: Dict[str, Any]) -> None:
        """Handle import completion

        Args:
            stats: Import statistics dictionary
        """
        self.import_btn.setEnabled(True)
        self.progress_bar.setValue(100)

        # Format results
        results = []
        results.append(f"Imported: {stats['imported']}")
        results.append(f"Updated: {stats['updated']}")
        results.append(f"Skipped: {stats['skipped']}")
        results.append(f"Failed: {stats['failed']}")

        if stats.get('errors'):
            results.append("\nErrors:")
            for error in stats['errors'][:10]:  # Show first 10 errors
                results.append(f"  - {error}")
            if len(stats['errors']) > 10:
                results.append(f"  ... and {len(stats['errors']) - 10} more errors")

        self.results_text.setText('\n'.join(results))

        # Show summary message
        total = stats['imported'] + stats['updated']
        QMessageBox.information(
            self,
            "Import Complete",
            f"Successfully imported/updated {total} contacts.\n"
            f"Skipped: {stats['skipped']}, Failed: {stats['failed']}"
        )
