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
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
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


class WACRefreshWorker(QThread):
    """Worker thread for refreshing WAC award progress - NO DATABASE ACCESS"""
    finished = pyqtSignal(dict)  # Emits progress data

    def __init__(self, contact_dicts: list, session_for_award):
        super().__init__()
        self.contact_dicts = contact_dicts
        self.session_for_award = session_for_award

    def run(self):
        """Run WAC calculation in background thread - data already fetched"""
        try:
            logger.debug(f"WAC Award: Processing {len(self.contact_dicts)} contacts")

            # Calculate WAC progress (using pre-fetched data)
            wac_award = WACAward(self.session_for_award)
            progress = wac_award.calculate_progress(self.contact_dicts)

            logger.info(f"WAC Award: Calculated progress - {progress['current']}/6 continents worked")

            self.finished.emit(progress)
        except Exception as e:
            logger.error(f"Error in WAC refresh worker: {e}", exc_info=True)
            # Emit empty progress on error
            self.finished.emit({
                'current': 0,
                'required': 6,
                'achieved': False,
                'progress_pct': 0.0,
                'level': 'Error',
                'continents_worked': [],
                'continent_details': {},
                'band_details': {},
            })


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
        self._refresh_worker: Optional[WACRefreshWorker] = None

        self._init_ui()
        # Defer initial refresh to avoid blocking GUI startup
        QTimer.singleShot(450, self.refresh)

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

        # Actions Section
        actions_group = self._create_actions_section()
        main_layout.addWidget(actions_group)

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
        """Refresh award progress - fetch data on main thread, calculate in background"""
        # Don't start new refresh if one is already running
        if self._refresh_worker and self._refresh_worker.isRunning():
            logger.debug("WAC refresh worker already running, skipping")
            return

        # Fetch data on MAIN THREAD (thread-safe)
        try:
            from src.database.models import Contact
            session = self.db.get_session()
            contacts = session.query(Contact).all()
            logger.info(f"WAC Award: Fetched {len(contacts)} total contacts from database")

            # Convert to dictionaries (main thread)
            contact_dicts = []
            for c in contacts:
                contact_dicts.append({
                    'callsign': c.callsign,
                    'mode': c.mode,
                    'skcc_number': c.skcc_number,
                    'key_type': c.key_type,
                    'qso_date': c.qso_date,
                    'band': c.band,
                })
        except Exception as e:
            logger.error(f"Error fetching WAC data: {e}", exc_info=True)
            return

        def on_refresh_finished(progress: dict):
            """Handle refresh completion on main thread"""
            try:
                # Check if widget is still valid (not being destroyed)
                if not self or not hasattr(self, 'progress_bar'):
                    logger.debug("WAC widget destroyed, skipping UI update")
                    if hasattr(self, '_refresh_worker') and self._refresh_worker:
                        try:
                            self._refresh_worker.wait(100)
                            self._refresh_worker.deleteLater()
                        except:
                            pass
                    return

                if self._refresh_worker:
                    # Wait for thread to fully exit before deletion
                    self._refresh_worker.wait(500)

                    # Disconnect signal before deletion
                    try:
                        self._refresh_worker.finished.disconnect()
                    except:
                        pass

                    self._refresh_worker.deleteLater()
                    self._refresh_worker = None

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
                logger.error(f"Error handling WAC refresh completion: {e}", exc_info=True)
                self.status_label.setText(f"Error: {str(e)}")

        # Start background worker with pre-fetched data (no DB access in worker)
        self._refresh_worker = WACRefreshWorker(contact_dicts, session)
        self._refresh_worker.finished.connect(on_refresh_finished)
        self._refresh_worker.start()
        logger.debug("Started background WAC refresh worker with pre-fetched data")

    def _create_actions_section(self) -> QGroupBox:
        """Create actions section with report and application generation buttons"""
        group = QGroupBox("Actions")
        layout = QHBoxLayout()

        report_btn = QPushButton("Create Award Report")
        report_btn.setToolTip("Generate a WAC award report to submit to the award manager")
        report_btn.clicked.connect(self._open_award_report_dialog)
        layout.addWidget(report_btn)

        app_btn = QPushButton("Generate Application")
        app_btn.setToolTip("Generate a WAC award application to submit to the award manager")
        app_btn.clicked.connect(self._open_award_application_dialog)
        layout.addWidget(app_btn)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def _open_award_report_dialog(self) -> None:
        """Open award report dialog"""
        try:
            from src.ui.dialogs.award_report_dialog import AwardReportDialog
            dialog = AwardReportDialog(self.db, award_type='WAC', parent=self)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error opening award report dialog: {e}", exc_info=True)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to open report dialog: {str(e)}")

    def _open_award_application_dialog(self) -> None:
        """Open award application dialog"""
        try:
            from src.ui.dialogs.award_application_dialog import AwardApplicationDialog
            dialog = AwardApplicationDialog(self.db, parent=self)
            # Pre-select WAC award
            dialog.award_combo.setCurrentText('WAC')
            dialog.exec()
        except Exception as e:
            logger.error(f"Error opening award application dialog: {e}", exc_info=True)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to open application dialog: {str(e)}")

    def closeEvent(self, event) -> None:
        """Clean up when widget is closed"""
        try:
            # Stop any running worker thread with quick timeout
            if self._refresh_worker and self._refresh_worker.isRunning():
                self._refresh_worker.quit()
                if not self._refresh_worker.wait(500):  # Wait max 500ms
                    logger.warning("WAC refresh worker didn't stop in time, terminating...")
                    self._refresh_worker.terminate()
                    self._refresh_worker.wait(100)
        except Exception as e:
            logger.error(f"Error cleaning up WAC widget: {e}", exc_info=True)
        super().closeEvent(event)

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
