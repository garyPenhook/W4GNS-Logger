"""
Main Application Window

PyQt6 main window with tabbed interface for all application features.
"""

import logging
from pathlib import Path
from typing import Dict, Any
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QMenuBar, QToolBar, QStatusBar, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon

from src.database.repository import DatabaseRepository
from src.config.settings import get_config_manager

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize main window

        Args:
            config: Application configuration dictionary
        """
        super().__init__()

        self.config = config
        self.config_manager = get_config_manager()

        # Initialize database
        db_path = self.config_manager.get("database.location")
        self.db = DatabaseRepository(db_path)

        # Auto-sync SKCC roster on startup (background, non-blocking)
        logger.info("Syncing SKCC membership roster...")
        try:
            success = self.db.skcc_members.sync_membership_data()
            member_count = self.db.skcc_members.get_member_count()
            if success and member_count > 0:
                logger.info(f"SKCC roster synced: {member_count} members available")
            elif member_count > 0:
                logger.warning(f"SKCC roster sync incomplete: {member_count} members in cache")
            else:
                logger.warning("SKCC roster sync failed and no cached data. Loading test data for development...")
                if self.db.skcc_members.load_test_data():
                    logger.warning("Test data loaded - use 'Sync Roster' button to load real roster when ready")
        except Exception as e:
            logger.error(f"Error syncing SKCC roster on startup: {e}")

        # Setup UI
        self.setWindowTitle("W4GNS Ham Radio Logger")
        self.setGeometry(100, 100, 1400, 900)

        self._create_menu_bar()
        self._create_toolbar()
        self._create_central_widget()
        self._create_status_bar()

        logger.info("Main window initialized")

    def _create_menu_bar(self) -> None:
        """Create application menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        new_contact_action = QAction("&New Contact", self)
        new_contact_action.setShortcut("Ctrl+N")
        file_menu.addAction(new_contact_action)

        import_action = QAction("&Import ADIF...", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self._show_import_dialog)
        file_menu.addAction(import_action)

        export_action = QAction("&Export ADIF...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._show_export_dialog)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        settings_action = QAction("&Settings", self)
        settings_action.setShortcut("Ctrl+,")
        edit_menu.addAction(settings_action)

        # View menu
        view_menu = menubar.addMenu("&View")
        theme_action = QAction("&Toggle Dark Mode", self)
        view_menu.addAction(theme_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        verify_awards_action = QAction("&Verify Awards", self)
        tools_menu.addAction(verify_awards_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        help_action = QAction("&Help Contents", self)
        help_action.setShortcut("F1")
        help_action.triggered.connect(self._show_help)
        help_menu.addAction(help_action)

        help_menu.addSeparator()

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_toolbar(self) -> None:
        """Create application toolbar"""
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMovable(False)

        # New contact button
        new_contact_action = QAction("New Contact", self)
        toolbar.addAction(new_contact_action)

        toolbar.addSeparator()

        # Import/Export buttons
        import_action = QAction("Import", self)
        import_action.triggered.connect(self._show_import_dialog)
        toolbar.addAction(import_action)

        export_action = QAction("Export", self)
        export_action.triggered.connect(self._show_export_dialog)
        toolbar.addAction(export_action)

    def _create_central_widget(self) -> None:
        """Create central widget with tabs"""
        central_widget = QWidget()
        layout = QVBoxLayout()

        # Create tab widget
        self.tabs = QTabWidget()

        # Add tabs
        self.tabs.addTab(self._create_logging_tab(), "Logging")
        self.tabs.addTab(self._create_qrp_progress_tab(), "QRP Progress")
        self.tabs.addTab(self._create_power_stats_tab(), "Power Stats")
        self.tabs.addTab(self._create_contacts_tab(), "Contacts")
        self.tabs.addTab(self._create_awards_tab(), "Awards")
        self.tabs.addTab(self._create_cluster_tab(), "DX Cluster")
        self.tabs.addTab(self._create_settings_tab(), "Settings")

        layout.addWidget(self.tabs)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def _create_logging_tab(self) -> QWidget:
        """Create contact logging tab"""
        from src.ui.logging_form import LoggingForm
        widget = QWidget()
        layout = QVBoxLayout()
        self.logging_form = LoggingForm(self.db)
        layout.addWidget(self.logging_form)
        widget.setLayout(layout)
        return widget

    def _create_qrp_progress_tab(self) -> QWidget:
        """Create QRP progress tab"""
        from src.ui.qrp_progress_widget import QRPProgressWidget
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QRPProgressWidget(self.db))
        widget.setLayout(layout)
        return widget

    def _create_power_stats_tab(self) -> QWidget:
        """Create power statistics tab"""
        from src.ui.power_stats_widget import PowerStatsWidget
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(PowerStatsWidget(self.db))
        widget.setLayout(layout)
        return widget

    def _create_contacts_tab(self) -> QWidget:
        """Create contacts list tab"""
        from src.ui.contacts_list_widget import ContactsListWidget
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(ContactsListWidget(self.db))
        widget.setLayout(layout)
        return widget

    def _create_awards_tab(self) -> QWidget:
        """Create awards dashboard tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self._create_placeholder("Awards Dashboard"))
        widget.setLayout(layout)
        return widget

    def _create_cluster_tab(self) -> QWidget:
        """Create DX cluster tab with SKCC spots monitoring"""
        from src.skcc import SKCCSpotManager
        from src.ui.widgets.skcc_spots_widget import SKCCSpotWidget

        widget = QWidget()
        layout = QVBoxLayout()

        # Initialize spot manager and widget
        spot_manager = SKCCSpotManager(self.db)
        spots_widget = SKCCSpotWidget(spot_manager)

        # Connect spot selection to logging form - connect after tabs are created
        # The connection is deferred via slot to ensure logging_form exists
        spots_widget.spot_selected.connect(self._on_spot_selected)

        layout.addWidget(spots_widget)
        widget.setLayout(layout)

        # Store reference for cleanup
        self.spot_manager = spot_manager
        self.spots_widget = spots_widget

        return widget

    def _create_settings_tab(self) -> QWidget:
        """Create settings tab"""
        from src.ui.settings_editor import SettingsEditor
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(SettingsEditor())
        widget.setLayout(layout)
        return widget

    def _create_placeholder(self, text: str) -> QWidget:
        """Create placeholder widget"""
        from PyQt6.QtWidgets import QLabel
        label = QLabel(f"[{text}]")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    def _create_status_bar(self) -> None:
        """Create status bar"""
        self.status_label = self.statusBar()
        self.status_label.showMessage("Ready")

    def _show_help(self) -> None:
        """Show help contents"""
        help_file = Path(__file__).parent.parent.parent / "HELP.md"

        if help_file.exists():
            try:
                with open(help_file, "r") as f:
                    help_text = f.read()

                # Create a dialog with help text
                from PyQt6.QtWidgets import QDialog, QTextEdit
                help_dialog = QDialog(self)
                help_dialog.setWindowTitle("Help - W4GNS Ham Radio Logger")
                help_dialog.setGeometry(100, 100, 700, 600)

                text_edit = QTextEdit()
                text_edit.setMarkdown(help_text)
                text_edit.setReadOnly(True)

                layout = QVBoxLayout()
                layout.addWidget(text_edit)
                help_dialog.setLayout(layout)
                help_dialog.exec()

            except Exception as e:
                logger.error(f"Failed to load help file: {e}")
                QMessageBox.warning(self, "Help", "Could not load help file")
        else:
            QMessageBox.information(
                self,
                "Help",
                "Help file not found. See documentation in project directory."
            )

    def _show_about(self) -> None:
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About W4GNS Ham Radio Logger",
            "W4GNS Ham Radio Logger v1.0.0\n\n"
            "A comprehensive ham radio contact logging application\n"
            "with ADIF support, award tracking, and DX cluster integration.\n\n"
            "Press F1 or go to Help → Help Contents for more information."
        )

    def _show_import_dialog(self) -> None:
        """Show ADIF import dialog"""
        from src.ui.dialogs.import_dialog import ImportDialog

        dialog = ImportDialog(self.db, self)
        dialog.exec()

    def _show_export_dialog(self) -> None:
        """Show ADIF export dialog"""
        from src.ui.dialogs.export_dialog import ExportDialog

        dialog = ExportDialog(self.db, self.config, self)
        dialog.exec()

    def _on_spot_selected(self, callsign: str, frequency: float) -> None:
        """
        Handle SKCC spot selection from DX Cluster tab

        Args:
            callsign: The DX station callsign
            frequency: The operating frequency in MHz
        """
        if hasattr(self, "logging_form") and self.logging_form:
            try:
                # Populate DX field with selected callsign
                if hasattr(self.logging_form, "callsign_input"):
                    self.logging_form.callsign_input.setText(callsign)

                # Set frequency if possible
                if hasattr(self.logging_form, "frequency_input"):
                    self.logging_form.frequency_input.setValue(frequency)

                # Switch to logging tab
                self.tabs.setCurrentIndex(0)

                logger.debug(f"Populated logging form with spot: {callsign} on {frequency} MHz")
            except Exception as e:
                logger.error(f"Error populating logging form from spot: {e}")

    def closeEvent(self, event) -> None:
        """
        Handle window close event with graceful resource cleanup

        Ensures database connections are properly closed before exit.
        """
        try:
            # Ask user confirmation
            reply = QMessageBox.question(
                self,
                "Exit",
                "Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Clean up database resources
                try:
                    if hasattr(self, 'db') and self.db:
                        self.db.engine.dispose()
                        logger.info("Database connection closed gracefully")
                except Exception as db_error:
                    logger.error(f"Error closing database connection: {db_error}", exc_info=True)

                logger.info("Application exiting gracefully")
                event.accept()
            else:
                event.ignore()

        except Exception as e:
            logger.error(f"Error in closeEvent: {e}", exc_info=True)
            # Accept event anyway to allow exit on error
            try:
                if hasattr(self, 'db') and self.db:
                    self.db.engine.dispose()
            except:
                pass
            event.accept()
