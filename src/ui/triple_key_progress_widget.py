"""
SKCC Triple Key Award Progress Widget

Displays Triple Key award progress tracking contacts with three mechanical key types:
- Straight Key (100 unique members)
- Bug (100 unique members)
- Sideswiper (100 unique members)
- Total: 300 unique members across all three key types
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

from src.database.repository import DatabaseRepository
from src.awards.triple_key import TripleKeyAward
from src.ui.signals import get_app_signals

logger = logging.getLogger(__name__)

# Triple Key color (teal/turquoise - represents three key types)
TRIPLE_KEY_COLOR = "#008B8B"


class TripleKeyRefreshWorker(QThread):
    """Worker thread for refreshing Triple Key award progress - NO DATABASE ACCESS"""
    finished = pyqtSignal(dict)  # Emits progress data

    def __init__(self, contact_dicts: list, session_for_award):
        super().__init__()
        self.contact_dicts = contact_dicts
        self.session_for_award = session_for_award

    def run(self):
        """Run Triple Key calculation in background thread - data already fetched"""
        try:
            logger.debug(f"Triple Key Award: Processing {len(self.contact_dicts)} contacts")

            # Calculate Triple Key progress (using pre-fetched data)
            triple_key_award = TripleKeyAward(self.session_for_award)
            progress = triple_key_award.calculate_progress(self.contact_dicts)

            logger.info(f"Triple Key Award: SK={progress.get('straight_key_members', 0)}, "
                       f"BUG={progress.get('bug_members', 0)}, "
                       f"SS={progress.get('sideswiper_members', 0)}, "
                       f"Total={progress.get('total_unique_members', 0)}, "
                       f"achieved={progress.get('achieved', False)}")

            self.finished.emit(progress)
        except Exception as e:
            logger.error(f"Error in Triple Key refresh worker: {e}", exc_info=True)
            # Emit empty progress on error
            self.finished.emit({
                'current': 0,
                'required': 300,
                'achieved': False,
                'progress_pct': 0.0,
                'level': 'Error',
                'straight_key_members': 0,
                'bug_members': 0,
                'sideswiper_members': 0,
                'total_unique_members': 0,
                'straight_key_progress_pct': 0.0,
                'bug_progress_pct': 0.0,
                'sideswiper_progress_pct': 0.0,
            })


class TripleKeyProgressWidget(QWidget):
    """Displays SKCC Triple Key award progress with three key type tracking"""

    def __init__(self, db: DatabaseRepository, parent: Optional[QWidget] = None):
        """
        Initialize Triple Key progress widget

        Args:
            db: Database repository instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.db = db
        self._refresh_worker: Optional[TripleKeyRefreshWorker] = None

        self._init_ui()
        # Defer initial refresh to avoid blocking GUI startup
        QTimer.singleShot(100, self.refresh)

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

        # Key Type Progress Section
        key_types_group = self._create_key_types_section()
        main_layout.addWidget(key_types_group)

        # Award Status Section
        status_group = self._create_status_section()
        main_layout.addWidget(status_group)

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
        group = QGroupBox("Triple Key Progress")
        layout = QVBoxLayout()

        # Description
        desc = QLabel(
            "Contact unique SKCC members with all three mechanical key types\n"
            "Straight Key (100), Bug (100), Sideswiper (100) = 300 total unique members"
        )
        desc.setFont(QFont("Arial", 9))
        desc.setStyleSheet("color: #666666;")
        layout.addWidget(desc)

        # Overall progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(300)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v / 300 members")
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                height: 28px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {TRIPLE_KEY_COLOR};
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

    def _create_key_types_section(self) -> QGroupBox:
        """Create key type progress section"""
        group = QGroupBox("Progress by Key Type")
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # Straight Key
        sk_layout = QHBoxLayout()
        sk_label = QLabel("Straight Key:")
        sk_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        sk_layout.addWidget(sk_label)

        self.sk_progress = QProgressBar()
        self.sk_progress.setMaximum(100)
        self.sk_progress.setValue(0)
        self.sk_progress.setTextVisible(True)
        self.sk_progress.setFormat("%v / 100")
        self.sk_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #cccccc;
                border-radius: 3px;
                text-align: center;
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {TRIPLE_KEY_COLOR};
            }}
        """)
        sk_layout.addWidget(self.sk_progress)
        self.sk_count_label = QLabel("0%")
        self.sk_count_label.setFont(QFont("Arial", 9))
        sk_layout.addWidget(self.sk_count_label)
        layout.addLayout(sk_layout)

        # Bug
        bug_layout = QHBoxLayout()
        bug_label = QLabel("Bug (Semi-auto):")
        bug_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        bug_layout.addWidget(bug_label)

        self.bug_progress = QProgressBar()
        self.bug_progress.setMaximum(100)
        self.bug_progress.setValue(0)
        self.bug_progress.setTextVisible(True)
        self.bug_progress.setFormat("%v / 100")
        self.bug_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #cccccc;
                border-radius: 3px;
                text-align: center;
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {TRIPLE_KEY_COLOR};
            }}
        """)
        bug_layout.addWidget(self.bug_progress)
        self.bug_count_label = QLabel("0%")
        self.bug_count_label.setFont(QFont("Arial", 9))
        bug_layout.addWidget(self.bug_count_label)
        layout.addLayout(bug_layout)

        # Sideswiper
        ss_layout = QHBoxLayout()
        ss_label = QLabel("Sideswiper:")
        ss_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        ss_layout.addWidget(ss_label)

        self.ss_progress = QProgressBar()
        self.ss_progress.setMaximum(100)
        self.ss_progress.setValue(0)
        self.ss_progress.setTextVisible(True)
        self.ss_progress.setFormat("%v / 100")
        self.ss_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #cccccc;
                border-radius: 3px;
                text-align: center;
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {TRIPLE_KEY_COLOR};
            }}
        """)
        ss_layout.addWidget(self.ss_progress)
        self.ss_count_label = QLabel("0%")
        self.ss_count_label.setFont(QFont("Arial", 9))
        ss_layout.addWidget(self.ss_count_label)
        layout.addLayout(ss_layout)

        group.setLayout(layout)
        return group

    def _create_status_section(self) -> QGroupBox:
        """Create award status section"""
        group = QGroupBox("Award Status")
        layout = QVBoxLayout()

        # Status indicator labels
        self.sk_status = QLabel("☐ Straight Key (0/100)")
        self.sk_status.setFont(QFont("Arial", 10))
        layout.addWidget(self.sk_status)

        self.bug_status = QLabel("☐ Bug (0/100)")
        self.bug_status.setFont(QFont("Arial", 10))
        layout.addWidget(self.bug_status)

        self.ss_status = QLabel("☐ Sideswiper (0/100)")
        self.ss_status.setFont(QFont("Arial", 10))
        layout.addWidget(self.ss_status)

        layout.addSpacing(8)

        self.award_status = QLabel("Award Status: Not Yet Achieved")
        self.award_status.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(self.award_status)

        group.setLayout(layout)
        return group

    def _create_stats_section(self) -> QGroupBox:
        """Create statistics section"""
        group = QGroupBox("Statistics")
        layout = QVBoxLayout()
        layout.setSpacing(6)

        # Stats labels
        stats_layout = QHBoxLayout()

        self.total_unique_label = QLabel("Total Unique Members: 0")
        self.total_unique_label.setFont(QFont("Arial", 9))
        stats_layout.addWidget(self.total_unique_label)

        self.total_contacts_label = QLabel("Total Contacts: 0")
        self.total_contacts_label.setFont(QFont("Arial", 9))
        stats_layout.addWidget(self.total_contacts_label)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        group.setLayout(layout)
        return group

    def refresh(self) -> None:
        """Refresh award progress - fetch data on main thread, calculate in background"""
        # Don't start new refresh if one is already running
        if self._refresh_worker and self._refresh_worker.isRunning():
            logger.debug("Triple Key refresh worker already running, skipping")
            return

        # Fetch data on MAIN THREAD (thread-safe)
        try:
            from src.database.models import Contact
            session = self.db.get_session()
            contacts = session.query(Contact).all()
            logger.info(f"Triple Key Award: Fetched {len(contacts)} total contacts from database")

            # Convert to dictionaries (main thread)
            contact_dicts = []
            for c in contacts:
                contact_dicts.append({
                    'callsign': c.callsign,
                    'mode': c.mode,
                    'band': c.band,
                    'qso_date': c.qso_date,
                    'qso_time': c.time_on,
                    'skcc_number': c.skcc_number,
                    'key_type': c.key_type,
                })
        except Exception as e:
            logger.error(f"Error fetching Triple Key data: {e}", exc_info=True)
            return

        def on_refresh_finished(progress: dict):
            """Handle refresh completion on main thread"""
            try:
                # Check if widget is still valid (not being destroyed)
                if not self or not hasattr(self, 'progress_bar'):
                    logger.debug("Triple Key widget destroyed, skipping UI update")
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
                sk_count = progress['straight_key_members']
                bug_count = progress['bug_members']
                ss_count = progress['sideswiper_members']
                total_unique = progress['total_unique_members']
                achieved = progress['achieved']

                logger.info(f"Triple Key Widget: Updating UI with sk_count={sk_count}, bug_count={bug_count}, ss_count={ss_count}")

                # Update overall progress bar
                self.progress_bar.setMaximum(300)
                self.progress_bar.setValue(total_unique)

                # Update status label
                status_text = "✅ Triple Key Award Achieved!" if achieved else "Working toward Triple Key Award"
                self.status_label.setText(
                    f"{status_text} • {total_unique} unique members • "
                    f"SK: {sk_count}/100, Bug: {bug_count}/100, SS: {ss_count}/100"
                )

                # Update key type progress bars
                # NOTE: QProgressBar ignores setValue() if value > maximum, so we must clamp to 100
                logger.info(f"Triple Key Widget: Setting SK progress to {sk_count}, max={self.sk_progress.maximum()}")
                self.sk_progress.setValue(min(sk_count, 100))
                self.sk_count_label.setText(
                    f"{progress['straight_key_progress_pct']:.0f}%"
                )

                logger.info(f"Triple Key Widget: Setting BUG progress to {bug_count}, max={self.bug_progress.maximum()}")
                self.bug_progress.setValue(min(bug_count, 100))
                logger.info(f"Triple Key Widget: BUG progress value after setValue: {self.bug_progress.value()}")
                self.bug_count_label.setText(
                    f"{progress['bug_progress_pct']:.0f}%"
                )

                logger.info(f"Triple Key Widget: Setting SS progress to {ss_count}, max={self.ss_progress.maximum()}")
                self.ss_progress.setValue(min(ss_count, 100))
                self.ss_count_label.setText(
                    f"{progress['sideswiper_progress_pct']:.0f}%"
                )

                # Update status indicators
                sk_indicator = "☑" if sk_count >= 100 else "☐"
                self.sk_status.setText(f"{sk_indicator} Straight Key ({sk_count}/100)")
                self.sk_status.setStyleSheet(
                    f"color: {TRIPLE_KEY_COLOR}; font-weight: bold;" if sk_count >= 100 else ""
                )

                bug_indicator = "☑" if bug_count >= 100 else "☐"
                self.bug_status.setText(f"{bug_indicator} Bug ({bug_count}/100)")
                self.bug_status.setStyleSheet(
                    f"color: {TRIPLE_KEY_COLOR}; font-weight: bold;" if bug_count >= 100 else ""
                )

                ss_indicator = "☑" if ss_count >= 100 else "☐"
                self.ss_status.setText(f"{ss_indicator} Sideswiper ({ss_count}/100)")
                self.ss_status.setStyleSheet(
                    f"color: {TRIPLE_KEY_COLOR}; font-weight: bold;" if ss_count >= 100 else ""
                )

                # Update award status
                if achieved:
                    self.award_status.setText("✅ Award Status: TRIPLE KEY ACHIEVED!")
                    self.award_status.setStyleSheet(f"color: {TRIPLE_KEY_COLOR}; font-weight: bold;")
                else:
                    missing = []
                    if sk_count < 100:
                        missing.append(f"SK: {100 - sk_count}")
                    if bug_count < 100:
                        missing.append(f"Bug: {100 - bug_count}")
                    if ss_count < 100:
                        missing.append(f"SS: {100 - ss_count}")
                    self.award_status.setText(f"Award Status: Need {', '.join(missing)}")
                    self.award_status.setStyleSheet("color: #666666;")

                # Update statistics
                self.total_unique_label.setText(f"Total Unique Members: {total_unique}")
                total_qualifying = progress.get('current', total_unique)
                self.total_contacts_label.setText(f"Total Qualifying Contacts: {total_qualifying}")

            except Exception as e:
                logger.error(f"Error handling Triple Key refresh completion: {e}", exc_info=True)
                self.status_label.setText(f"Error: {str(e)}")

        # Start background worker with pre-fetched data (no DB access in worker)
        self._refresh_worker = TripleKeyRefreshWorker(contact_dicts, session)
        self._refresh_worker.finished.connect(on_refresh_finished)
        self._refresh_worker.start()
        logger.debug("Started background Triple Key refresh worker with pre-fetched data")

    def _create_actions_section(self) -> QGroupBox:
        """Create actions section with report and application generation buttons"""
        group = QGroupBox("Actions")
        layout = QHBoxLayout()

        report_btn = QPushButton("Create Award Report")
        report_btn.setToolTip("Generate a Triple Key award report to submit to the award manager")
        report_btn.clicked.connect(self._open_award_report_dialog)
        layout.addWidget(report_btn)

        app_btn = QPushButton("Generate Application")
        app_btn.setToolTip("Generate a Triple Key award application to submit to the award manager")
        app_btn.clicked.connect(self._open_award_application_dialog)
        layout.addWidget(app_btn)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def _open_award_report_dialog(self) -> None:
        """Open award report dialog"""
        try:
            from src.ui.dialogs.award_report_dialog import AwardReportDialog
            dialog = AwardReportDialog(self.db, award_type='Triple Key', parent=self)
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
            # Pre-select Triple Key award
            dialog.award_combo.setCurrentText('Triple Key')
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
                    logger.warning("Triple Key refresh worker didn't stop in time, terminating...")
                    self._refresh_worker.terminate()
                    self._refresh_worker.wait(100)
        except Exception as e:
            logger.error(f"Error cleaning up Triple Key widget: {e}", exc_info=True)
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
