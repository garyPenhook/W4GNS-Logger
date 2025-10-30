"""
Award Application Dialog

Dialog for generating award applications for all SKCC awards.
Users can select award type, format, and generate applications for submission.
"""

import logging
from typing import Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QGroupBox, QFileDialog, QMessageBox, QCheckBox, QDateEdit, QProgressBar,
    QTextEdit, QWidget, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from src.database.repository import DatabaseRepository
from src.adif.award_application_generator import AwardApplicationGenerator
from src.config.settings import get_config_manager

logger = logging.getLogger(__name__)


class ApplicationGeneratorWorkerThread(QThread):
    """Worker thread for generating award applications"""

    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str, str)  # Success, message, application_text

    def __init__(
        self,
        generator: AwardApplicationGenerator,
        award_type: str,
        app_format: str,
        achievement_date: Optional[str] = None
    ):
        super().__init__()
        self.generator = generator
        self.award_type = award_type
        self.app_format = app_format
        self.achievement_date = achievement_date

    def run(self):
        """Run the application generation process"""
        try:
            self.status.emit("Generating application...")
            self.progress.emit(25)

            # Use universal generate_application method
            app_text = self.generator.generate_application(
                award_name=self.award_type,
                format=self.app_format,
                achievement_date=self.achievement_date
            )

            self.progress.emit(75)
            self.status.emit("Application generated successfully")
            self.progress.emit(100)

            self.finished.emit(True, "Application generated successfully", app_text)

        except Exception as e:
            logger.error(f"Application generation error: {e}", exc_info=True)
            self.finished.emit(False, f"Application generation failed: {str(e)}", "")


class AwardApplicationDialog(QDialog):
    """Dialog for generating award applications"""

    AWARDS = [
        'Centurion',
        'Tribune',
        'Senator',
        'WAS',
        'WAC',
        'Rag Chew',
        'DXCC',
        'Canadian Maple',
        'PFX',
        'Triple Key',
        'SKCC DX',
    ]

    AWARD_DESCRIPTIONS = {
        'Centurion': '100+ unique SKCC members (prerequisite for Tribune)',
        'Tribune': '50+ Tribune/Senator members (requires Centurion)',
        'Senator': '200+ Tribune/Senator after Tribune x8 (requires Tribune x8)',
        'WAS': 'All 50 US states',
        'WAC': 'All 6 continents',
        'Rag Chew': '300+ minutes of CW conversation',
        'DXCC': '100+ countries worked',
        'Canadian Maple': 'All Canadian provinces and territories',
        'PFX': 'Unique amateur radio call sign prefixes',
        'Triple Key': 'CW with three different key types',
        'SKCC DX': 'DX SKCC members (non-US/Canada)',
    }

    def __init__(
        self,
        db: DatabaseRepository,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.db = db
        self.application_text: Optional[str] = None
        self.generator: Optional[AwardApplicationGenerator] = None

        self._init_ui()
        self._setup_generator()

        self.setWindowTitle("Generate Award Application")
        self.setGeometry(100, 100, 700, 800)

    def _init_ui(self) -> None:
        """Initialize UI components"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Award Selection Group
        award_group = self._create_award_selection_group()
        main_layout.addWidget(award_group)

        # Award Description
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setFont(QFont("Arial", 9))
        self.description_label.setStyleSheet("color: #666; background-color: #f0f0f0; padding: 10px; border-radius: 3px;")
        main_layout.addWidget(self.description_label)

        # Format Group
        format_group = self._create_format_group()
        main_layout.addWidget(format_group)

        # Options Group
        options_group = self._create_options_group()
        main_layout.addWidget(options_group)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Arial", 9))
        main_layout.addWidget(self.status_label)

        # Preview
        preview_group = self._create_preview_group()
        main_layout.addWidget(preview_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        generate_btn = QPushButton("Generate Application")
        generate_btn.clicked.connect(self._generate_application)
        button_layout.addWidget(generate_btn)

        export_btn = QPushButton("Export Application")
        export_btn.clicked.connect(self._export_application)
        self.export_btn = export_btn
        self.export_btn.setEnabled(False)
        button_layout.addWidget(export_btn)

        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self._copy_to_clipboard)
        self.copy_btn = copy_btn
        self.copy_btn.setEnabled(False)
        button_layout.addWidget(copy_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def _create_award_selection_group(self) -> QGroupBox:
        """Create award type selection group"""
        group = QGroupBox("Select Award")
        layout = QVBoxLayout()

        self.award_combo = QComboBox()
        self.award_combo.addItems(self.AWARDS)
        self.award_combo.currentTextChanged.connect(self._on_award_changed)
        layout.addWidget(self.award_combo)

        group.setLayout(layout)
        return group

    def _create_format_group(self) -> QGroupBox:
        """Create application format selection group"""
        group = QGroupBox("Application Format")
        layout = QHBoxLayout()

        layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            'Text',
            'SKCC Official',
            'CSV (Spreadsheet)',
            'HTML'
        ])
        self.format_combo.setCurrentIndex(1)  # Default to SKCC Official
        layout.addWidget(self.format_combo)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def _create_options_group(self) -> QGroupBox:
        """Create application options group"""
        group = QGroupBox("Options")
        layout = QVBoxLayout()

        self.include_all_checkbox = QCheckBox("Include all contacts")
        self.include_all_checkbox.setChecked(True)
        layout.addWidget(self.include_all_checkbox)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def _create_preview_group(self) -> QGroupBox:
        """Create preview area group"""
        group = QGroupBox("Preview")
        layout = QVBoxLayout()

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlaceholderText("Generate an application to see preview here...")
        self.preview_text.setMaximumHeight(200)
        layout.addWidget(self.preview_text)

        group.setLayout(layout)
        return group

    def _setup_generator(self) -> None:
        """Set up the application generator"""
        try:
            config_manager = get_config_manager()
            my_callsign = config_manager.get('general', {}).get('operator_callsign', 'UNKNOWN')
            my_skcc = config_manager.get('adif', {}).get('my_skcc_number', 'UNKNOWN')

            self.generator = AwardApplicationGenerator(
                self.db,
                my_callsign,
                my_skcc
            )
        except Exception as e:
            logger.error(f"Failed to initialize application generator: {e}")
            self.status_label.setText(f"Error: {str(e)}")

    def _on_award_changed(self, award_name: str) -> None:
        """Handle award type change"""
        self.description_label.setText(self.AWARD_DESCRIPTIONS.get(award_name, ''))

    def _get_application_format(self) -> str:
        """Get selected application format"""
        format_map = {
            'Text': 'text',
            'SKCC Official': 'skcc',
            'CSV (Spreadsheet)': 'csv',
            'HTML': 'html'
        }
        return format_map.get(self.format_combo.currentText(), 'text')



    def _generate_application(self) -> None:
        """Generate the application"""
        if not self.generator:
            QMessageBox.warning(self, "Error", "Application generator not initialized")
            return

        award_type = self.award_combo.currentText()
        app_format = self._get_application_format()

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Generating application...")

        self.worker = ApplicationGeneratorWorkerThread(
            self.generator,
            award_type,
            app_format,
            None  # No user-selected date - use official achievement dates from database
        )
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self._on_application_generated)
        self.worker.start()

    def _on_application_generated(self, success: bool, message: str, app_text: str) -> None:
        """Handle application generation completion"""
        self.progress_bar.setVisible(False)

        if success:
            self.application_text = app_text
            self.status_label.setText(message)
            self.export_btn.setEnabled(True)
            self.copy_btn.setEnabled(True)

            # Show preview
            preview = app_text[:1500]
            if len(app_text) > 1500:
                preview += "\n\n[Preview truncated - full application available on export]"
            self.preview_text.setText(preview)

        else:
            QMessageBox.critical(self, "Error", message)
            self.status_label.setText(f"Error: {message}")

    def _export_application(self) -> None:
        """Export application to file"""
        if not self.application_text:
            QMessageBox.warning(self, "No Application", "Please generate an application first")
            return

        format_map = {
            'text': 'txt',
            'csv': 'csv',
            'html': 'html'
        }
        extension = format_map.get(self._get_application_format(), 'txt')

        award_name = self.award_combo.currentText().lower().replace(' ', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suggested_name = f"{award_name}_application_{timestamp}.{extension}"

        # Default to award_applications folder in project root
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent.parent
        award_apps_dir = project_root / "award_applications"
        award_apps_dir.mkdir(parents=True, exist_ok=True)

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Award Application",
            str(award_apps_dir / suggested_name),
            f"Application Files (*.{extension});;All Files (*.*)"
        )

        if not file_path:
            return

        if self.generator.export_application_to_file(self.application_text, file_path):
            QMessageBox.information(
                self,
                "Success",
                f"Application exported to:\n{file_path}"
            )
        else:
            QMessageBox.critical(
                self,
                "Export Failed",
                "Failed to export application. Check logs for details."
            )

    def _copy_to_clipboard(self) -> None:
        """Copy application to clipboard"""
        if not self.application_text:
            QMessageBox.warning(self, "No Application", "Please generate an application first")
            return

        from PyQt6.QtGui import QClipboard
        from PyQt6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        clipboard.setText(self.application_text)

        QMessageBox.information(
            self,
            "Copied",
            "Application copied to clipboard"
        )
