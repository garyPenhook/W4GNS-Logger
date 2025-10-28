"""
Award Report Dialog

Dialog for generating and exporting award reports for submission to award managers.
Supports Tribune, Centurion, Senator, and other SKCC awards.
"""

import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QGroupBox, QFileDialog, QMessageBox, QRadioButton, QButtonGroup,
    QCheckBox, QSpinBox, QDateEdit, QProgressBar, QTextEdit, QWidget
)
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from src.database.repository import DatabaseRepository
from src.adif.award_report_generator import AwardReportGenerator
from src.config.settings import get_config_manager

logger = logging.getLogger(__name__)


class ReportGeneratorWorkerThread(QThread):
    """Worker thread for generating award reports"""

    progress = pyqtSignal(int)  # Progress percentage
    status = pyqtSignal(str)  # Status message
    finished = pyqtSignal(bool, str, str)  # Success, message, report_text

    def __init__(
        self,
        generator: AwardReportGenerator,
        award_type: str,
        report_format: str,
        include_summary: bool = True,
        achievement_date: Optional[str] = None
    ):
        super().__init__()
        self.generator = generator
        self.award_type = award_type
        self.report_format = report_format
        self.include_summary = include_summary
        self.achievement_date = achievement_date

    def run(self):
        """Run the report generation process"""
        try:
            self.status.emit("Generating report...")
            self.progress.emit(25)

            # Use universal report generation
            report_text = self.generator.generate_report(
                award_name=self.award_type,
                format=self.report_format,
                include_summary=self.include_summary,
                achievement_date=self.achievement_date
            )

            self.progress.emit(75)
            self.status.emit("Report generated successfully")
            self.progress.emit(100)

            self.finished.emit(True, "Report generated successfully", report_text)

        except Exception as e:
            logger.error(f"Report generation error: {e}", exc_info=True)
            self.finished.emit(False, f"Report generation failed: {str(e)}", "")


class AwardReportDialog(QDialog):
    """Dialog for generating and exporting award reports"""

    def __init__(
        self,
        db: DatabaseRepository,
        award_type: str = 'Tribune',
        parent: Optional[QWidget] = None
    ):
        """
        Initialize award report dialog

        Args:
            db: DatabaseRepository instance
            award_type: Type of award ('Tribune', 'Centurion', 'Senator')
            parent: Parent widget
        """
        super().__init__(parent)
        self.db = db
        self.selected_award = award_type
        self.report_text: Optional[str] = None
        self.generator: Optional[AwardReportGenerator] = None

        self._init_ui()
        self._setup_generator()

        self.setWindowTitle("Generate Award Report")
        self.setGeometry(100, 100, 700, 800)

    def _init_ui(self) -> None:
        """Initialize UI components"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Award Selection Group
        award_group = self._create_award_selection_group()
        main_layout.addWidget(award_group)

        # Report Format Group
        format_group = self._create_format_group()
        main_layout.addWidget(format_group)

        # Options Group
        options_group = self._create_options_group()
        main_layout.addWidget(options_group)

        # Achievement Date Group (for endorsements)
        self.achievement_date_group = self._create_achievement_date_group()
        self.achievement_date_group.setVisible(self.selected_award in ['Tribune', 'Senator', 'Centurion'])
        main_layout.addWidget(self.achievement_date_group)

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

        generate_btn = QPushButton("Generate Report")
        generate_btn.clicked.connect(self._generate_report)
        button_layout.addWidget(generate_btn)

        export_btn = QPushButton("Export Report")
        export_btn.clicked.connect(self._export_report)
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
        group = QGroupBox("Award Type")
        layout = QVBoxLayout()

        # Create dropdown for award selection
        dropdown_layout = QHBoxLayout()
        dropdown_layout.addWidget(QLabel("Select Award:"))

        self.award_combo = QComboBox()
        # Awards will be populated in _populate_award_combo() after generator is ready
        self.award_combo.currentTextChanged.connect(self._on_award_changed)
        dropdown_layout.addWidget(self.award_combo)
        dropdown_layout.addStretch()

        layout.addLayout(dropdown_layout)

        # Description label showing award requirements
        self.award_desc_label = QLabel()
        self.award_desc_label.setFont(QFont("Arial", 9))
        self.award_desc_label.setWordWrap(True)
        layout.addWidget(self.award_desc_label)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def _on_award_changed(self, award_name: str) -> None:
        """Handle award selection change"""
        self.selected_award = award_name
        
        # Update achievement date visibility
        if hasattr(self, 'achievement_date_group'):
            # Show achievement date for endorsement-eligible awards
            show_date = award_name in ['Tribune', 'Senator', 'Centurion']
            self.achievement_date_group.setVisible(show_date)

        # Update description
        award_descriptions = {
            'Centurion': '100+ unique SKCC members (no date restriction)',
            'Tribune': '50+ Tribune/Senator members (valid from 2007-03-01)',
            'Senator': '200+ Tribune/Senator members (valid from 2013-08-01)',
            'WAS': 'All 50 US States (valid from 2011-10-09)',
            'WAC': 'All 6 continents (valid from 2011-10-09)',
            'DXCC': '100+ confirmed DXCC entities',
            'CanadianMaple': 'All Canadian provinces and territories',
            'RagChew': '300+ minutes of CW conversation (valid from 2013-07-01)',
            'PFX': 'Prefix collection tracking',
            'TripleKey': 'SSB + CW + Digital modes',
            'SKCCDx': 'DX (outside USA) contacts',
        }
        
        desc = award_descriptions.get(award_name, 'Award requirements')
        self.award_desc_label.setText(f"Requirements: {desc}")

    def _create_format_group(self) -> QGroupBox:
        """Create report format selection group"""
        group = QGroupBox("Report Format")
        layout = QHBoxLayout()

        layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            'Text',
            'CSV (Spreadsheet)',
            'TSV (Tab-Separated)',
            'HTML'
        ])
        self.format_combo.setCurrentIndex(0)  # Default to Text
        layout.addWidget(self.format_combo)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def _create_options_group(self) -> QGroupBox:
        """Create report options group"""
        group = QGroupBox("Report Options")
        layout = QVBoxLayout()

        self.summary_checkbox = QCheckBox("Include Summary Statistics")
        self.summary_checkbox.setChecked(True)
        layout.addWidget(self.summary_checkbox)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def _create_achievement_date_group(self) -> QGroupBox:
        """Create achievement date group for Tribune/Senator"""
        group = QGroupBox("Achievement Date Filter")
        layout = QVBoxLayout()

        desc_label = QLabel(
            "For endorsement applications, filter contacts to only those\n"
            "made after the award achievement date:"
        )
        desc_label.setFont(QFont("Arial", 9))
        layout.addWidget(desc_label)

        date_layout = QHBoxLayout()

        self.use_achievement_date = QCheckBox("Filter by achievement date")
        self.use_achievement_date.setChecked(False)
        date_layout.addWidget(self.use_achievement_date)

        date_layout.addWidget(QLabel("Date (YYYYMMDD):"))

        self.achievement_date_edit = QDateEdit()
        self.achievement_date_edit.setDate(QDate.currentDate())
        self.achievement_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.achievement_date_edit.setEnabled(False)
        date_layout.addWidget(self.achievement_date_edit)

        self.use_achievement_date.toggled.connect(
            self.achievement_date_edit.setEnabled
        )

        date_layout.addStretch()
        layout.addLayout(date_layout)

        group.setLayout(layout)
        return group

    def _create_preview_group(self) -> QGroupBox:
        """Create preview area group"""
        group = QGroupBox("Preview")
        layout = QVBoxLayout()

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlaceholderText("Generate a report to see preview here...")
        self.preview_text.setMaximumHeight(150)
        layout.addWidget(self.preview_text)

        group.setLayout(layout)
        return group

    def _setup_generator(self) -> None:
        """Set up the report generator"""
        try:
            config_manager = get_config_manager()
            my_callsign = config_manager.get('general', {}).get('operator_callsign', 'UNKNOWN')
            my_skcc = config_manager.get('adif', {}).get('my_skcc_number', 'UNKNOWN')

            self.generator = AwardReportGenerator(
                self.db,
                my_callsign,
                my_skcc
            )
            
            # Populate award combo now that generator is ready
            self._populate_award_combo()
        except Exception as e:
            logger.error(f"Failed to initialize report generator: {e}")
            self.status_label.setText(f"Error: {str(e)}")

    def _populate_award_combo(self) -> None:
        """Populate award combo with available awards"""
        if self.generator:
            available_awards = self.generator.get_available_awards()
            self.award_combo.addItems(available_awards)
            # Set to selected award if available
            idx = self.award_combo.findText(self.selected_award)
            if idx >= 0:
                self.award_combo.setCurrentIndex(idx)

    def _get_report_format(self) -> str:
        """Get selected report format"""
        format_map = {
            'Text': 'text',
            'CSV (Spreadsheet)': 'csv',
            'TSV (Tab-Separated)': 'tsv',
            'HTML': 'html'
        }
        return format_map.get(self.format_combo.currentText(), 'text')

    def _get_achievement_date(self) -> Optional[str]:
        """Get achievement date if selected"""
        if self.use_achievement_date.isChecked():
            date = self.achievement_date_edit.date()
            return date.toString("yyyyMMdd")
        return None

    def _generate_report(self) -> None:
        """Generate the report"""
        if not self.generator:
            QMessageBox.warning(self, "Error", "Report generator not initialized")
            return

        # Get selected award from combo box
        self.selected_award = self.award_combo.currentText()

        report_format = self._get_report_format()
        include_summary = self.summary_checkbox.isChecked()
        achievement_date = self._get_achievement_date() if hasattr(self, 'achievement_date_edit') else None

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Generating report...")

        # Create and start worker thread
        self.worker = ReportGeneratorWorkerThread(
            self.generator,
            self.selected_award,
            report_format,
            include_summary,
            achievement_date
        )
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self._on_report_generated)
        self.worker.start()

    def _on_report_generated(self, success: bool, message: str, report_text: str) -> None:
        """Handle report generation completion"""
        self.progress_bar.setVisible(False)

        if success:
            self.report_text = report_text
            self.status_label.setText(message)
            self.export_btn.setEnabled(True)
            self.copy_btn.setEnabled(True)

            # Show preview (first 1000 characters)
            preview = report_text[:1000]
            if len(report_text) > 1000:
                preview += "\n\n[Preview truncated - full report available on export]"
            self.preview_text.setText(preview)

        else:
            QMessageBox.critical(self, "Error", message)
            self.status_label.setText(f"Error: {message}")

    def _export_report(self) -> None:
        """Export report to file"""
        if not self.report_text:
            QMessageBox.warning(self, "No Report", "Please generate a report first")
            return

        # Determine file extension based on format
        format_map = {
            'text': 'txt',
            'csv': 'csv',
            'tsv': 'tsv',
            'html': 'html'
        }
        extension = format_map.get(self._get_report_format(), 'txt')

        # Create suggested filename
        award_name = self.selected_award.lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suggested_name = f"{award_name}_report_{timestamp}.{extension}"

        # Default to award_applications folder in project root
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent.parent
        award_apps_dir = project_root / "award_applications"
        award_apps_dir.mkdir(parents=True, exist_ok=True)

        # Get save path (default to award_applications folder)
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Report",
            str(award_apps_dir / suggested_name),
            f"Report Files (*.{extension});;All Files (*.*)"
        )

        if not file_path:
            return

        # Export
        if self.generator.export_report_to_file(self.report_text, file_path, self._get_report_format()):
            QMessageBox.information(
                self,
                "Success",
                f"Report exported to:\n{file_path}"
            )
        else:
            QMessageBox.critical(
                self,
                "Export Failed",
                "Failed to export report. Check logs for details."
            )

    def _copy_to_clipboard(self) -> None:
        """Copy report to clipboard"""
        if not self.report_text:
            QMessageBox.warning(self, "No Report", "Please generate a report first")
            return

        from PyQt6.QtGui import QClipboard
        from PyQt6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        clipboard.setText(self.report_text)

        QMessageBox.information(
            self,
            "Copied",
            "Report copied to clipboard"
        )
