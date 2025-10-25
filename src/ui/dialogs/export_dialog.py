"""
ADIF Export Dialog

Handles exporting contacts to ADIF files.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QCheckBox, QGroupBox, QFileDialog, QMessageBox, QSpinBox,
    QDateEdit, QComboBox, QProgressBar, QTextEdit
)
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from src.database.repository import DatabaseRepository
from src.adif.exporter import ADIFExporter

logger = logging.getLogger(__name__)


class ExportWorkerThread(QThread):
    """Worker thread for exporting contacts to ADIF"""

    progress = pyqtSignal(int)  # Progress percentage
    status = pyqtSignal(str)  # Status message
    finished = pyqtSignal(bool, str)  # Success flag and message

    def __init__(
        self,
        file_path: str,
        db: DatabaseRepository,
        my_skcc: Optional[str],
        filters: Dict[str, Any]
    ):
        super().__init__()
        self.file_path = file_path
        self.db = db
        self.my_skcc = my_skcc
        self.filters = filters

    def run(self):
        """Run the export process"""
        try:
            self.status.emit("Retrieving contacts...")
            self.progress.emit(10)

            # Get contacts based on filters
            contacts = self._get_filtered_contacts()

            if not contacts:
                self.finished.emit(False, "No contacts to export.")
                return

            self.progress.emit(30)
            self.status.emit(f"Exporting {len(contacts)} contacts...")

            # Export to ADIF
            exporter = ADIFExporter()
            exporter.export_to_file(
                self.file_path,
                contacts,
                my_skcc=self.my_skcc
            )

            self.progress.emit(90)
            self.status.emit("Export complete!")
            self.progress.emit(100)

            self.finished.emit(
                True,
                f"Successfully exported {len(contacts)} contacts to {self.file_path}"
            )

        except Exception as e:
            logger.error(f"Export error: {e}")
            self.finished.emit(False, f"Export failed: {str(e)}")

    def _get_filtered_contacts(self) -> List[Any]:
        """Get contacts based on filter criteria

        Returns:
            List of Contact objects
        """
        contacts = self.db.get_all_contacts(limit=10000)

        # Apply filters
        filtered = contacts

        # Filter by date range
        if self.filters.get('date_from'):
            date_from = self.filters['date_from']
            filtered = [c for c in filtered if c.qso_date >= date_from]

        if self.filters.get('date_to'):
            date_to = self.filters['date_to']
            filtered = [c for c in filtered if c.qso_date <= date_to]

        # Filter by band
        if self.filters.get('band'):
            band = self.filters['band']
            filtered = [c for c in filtered if c.band == band]

        # Filter by mode
        if self.filters.get('mode'):
            mode = self.filters['mode']
            filtered = [c for c in filtered if c.mode == mode]

        # Filter by country
        if self.filters.get('country'):
            country = self.filters['country']
            filtered = [c for c in filtered if c.country and country.lower() in c.country.lower()]

        # Filter by SKCC only
        if self.filters.get('skcc_only'):
            filtered = [c for c in filtered if c.skcc_number]

        return filtered


class ExportDialog(QDialog):
    """Dialog for exporting contacts to ADIF"""

    def __init__(
        self,
        db: DatabaseRepository,
        config: Dict[str, Any],
        parent: Optional[QDialog] = None
    ):
        """
        Initialize export dialog

        Args:
            db: Database repository instance
            config: Application configuration dictionary
            parent: Parent widget
        """
        super().__init__(parent)
        self.db = db
        self.config = config
        self.export_file = None
        self.export_thread = None

        self.setWindowTitle("Export ADIF Contacts")
        self.setGeometry(100, 100, 700, 700)
        self.setModal(True)

        self._init_ui()
        self._load_config()

    def _init_ui(self) -> None:
        """Initialize UI components"""
        main_layout = QVBoxLayout()

        # Operator SKCC section
        skcc_layout = QHBoxLayout()
        skcc_label = QLabel("Your SKCC Number:")
        self.skcc_input = QLineEdit()
        self.skcc_input.setPlaceholderText("e.g., 14276T")
        skcc_layout.addWidget(skcc_label)
        skcc_layout.addWidget(self.skcc_input)
        main_layout.addLayout(skcc_layout)

        # File selection section
        file_layout = QHBoxLayout()
        file_label = QLabel("Export File:")
        self.file_output = QLabel("(No file selected)")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_save_file)
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_output, 1)
        file_layout.addWidget(browse_btn)
        main_layout.addLayout(file_layout)

        # Filters section
        filters_group = QGroupBox("Export Filters")
        filters_layout = QVBoxLayout()

        # Date range
        date_layout = QHBoxLayout()
        date_label = QLabel("Date Range:")
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addMonths(-12))
        date_range_label = QLabel("to")
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_range_enabled = QCheckBox("Enabled")
        self.date_range_enabled.setChecked(False)
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.date_from)
        date_layout.addWidget(date_range_label)
        date_layout.addWidget(self.date_to)
        date_layout.addWidget(self.date_range_enabled)
        filters_layout.addLayout(date_layout)

        # Band filter
        band_layout = QHBoxLayout()
        band_label = QLabel("Band:")
        self.band_combo = QComboBox()
        self.band_combo.addItem("(All bands)")
        for band in ["160M", "80M", "60M", "40M", "30M", "20M", "17M", "15M", "12M", "10M", "6M", "2M", "70cm"]:
            self.band_combo.addItem(band)
        self.band_filter_enabled = QCheckBox("Enabled")
        self.band_filter_enabled.setChecked(False)
        band_layout.addWidget(band_label)
        band_layout.addWidget(self.band_combo, 1)
        band_layout.addWidget(self.band_filter_enabled)
        filters_layout.addLayout(band_layout)

        # Mode filter
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Mode:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("(All modes)")
        for mode in ["CW", "SSB", "FM", "RTTY", "PSK31", "JT65", "FT8"]:
            self.mode_combo.addItem(mode)
        self.mode_filter_enabled = QCheckBox("Enabled")
        self.mode_filter_enabled.setChecked(False)
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo, 1)
        mode_layout.addWidget(self.mode_filter_enabled)
        filters_layout.addLayout(mode_layout)

        # SKCC only filter
        self.skcc_only_checkbox = QCheckBox("SKCC Contacts Only")
        self.skcc_only_checkbox.setChecked(False)
        filters_layout.addWidget(self.skcc_only_checkbox)

        filters_group.setLayout(filters_layout)
        main_layout.addWidget(filters_group)

        # Progress section
        progress_group = QGroupBox("Export Progress")
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.status_label = QLabel("Ready to export")
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)

        # Buttons section
        button_layout = QHBoxLayout()
        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self._start_export)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.export_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def _load_config(self) -> None:
        """Load configuration values"""
        my_skcc = self.config.get('adif', {}).get('my_skcc_number', '')
        if my_skcc:
            self.skcc_input.setText(my_skcc)

    def _browse_save_file(self) -> None:
        """Open file dialog to select save location"""
        # Default to logs folder in project root
        project_root = Path(__file__).parent.parent.parent
        logs_dir = project_root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        file_filter = "ADIF Files (*.adif *.adi);;All Files (*)"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export ADIF File",
            str(logs_dir / "contacts.adif"),
            file_filter
        )

        if file_path:
            self.export_file = file_path
            self.file_output.setText(Path(file_path).name)
            self.progress_bar.setValue(0)

    def _start_export(self) -> None:
        """Start the export process"""
        if not self.export_file:
            QMessageBox.warning(self, "No File", "Please select an export file location first.")
            return

        # Disable export button during export
        self.export_btn.setEnabled(False)
        self.progress_bar.setValue(0)

        # Build filters
        filters = {}

        if self.date_range_enabled.isChecked():
            filters['date_from'] = self.date_from.date().toString("yyyyMMdd")
            filters['date_to'] = self.date_to.date().toString("yyyyMMdd")

        if self.band_filter_enabled.isChecked() and self.band_combo.currentText() != "(All bands)":
            filters['band'] = self.band_combo.currentText()

        if self.mode_filter_enabled.isChecked() and self.mode_combo.currentText() != "(All modes)":
            filters['mode'] = self.mode_combo.currentText()

        if self.skcc_only_checkbox.isChecked():
            filters['skcc_only'] = True

        # Create and start worker thread
        self.export_thread = ExportWorkerThread(
            self.export_file,
            self.db,
            self.skcc_input.text() or None,
            filters
        )
        self.export_thread.progress.connect(self._on_progress)
        self.export_thread.status.connect(self._on_status)
        self.export_thread.finished.connect(self._on_export_finished)
        self.export_thread.start()

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

    def _on_export_finished(self, success: bool, message: str) -> None:
        """Handle export completion

        Args:
            success: Whether export succeeded
            message: Status message
        """
        self.export_btn.setEnabled(True)

        if success:
            self.progress_bar.setValue(100)
            QMessageBox.information(self, "Export Complete", message)
            self.accept()
        else:
            QMessageBox.critical(self, "Export Failed", message)
            self.progress_bar.setValue(0)
