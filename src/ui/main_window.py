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
from src.ui.theme_manager import ThemeManager
from src.backup.backup_manager import BackupManager

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
        try:
            db_path = self.config_manager.get("database.location")
            self.db = DatabaseRepository(db_path)
            logger.info(f"Database initialized at {db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Database Error",
                f"Cannot initialize database at {db_path}:\n{str(e)}\n\n"
                "The application will continue but may not function properly.\n"
                "Please check database permissions and try again."
            )
            self.db = None  # Set to None to prevent further database access attempts

        # Will be set after UI is initialized
        self.status_label = None

        # Setup UI
        self.setWindowTitle("W4GNS Ham Radio Logger")

        # Set initial window size and position (allowing resizing)
        self.setGeometry(100, 100, 1400, 900)

        # Set minimum size to allow resizing but maintain usability
        self.setMinimumSize(800, 600)

        # Make window resizable (restore from saved geometry if available)
        saved_geometry = self.config_manager.get("ui.window_geometry")
        if saved_geometry:
            try:
                # Geometry is stored as list [x, y, width, height]
                if isinstance(saved_geometry, (list, tuple)) and len(saved_geometry) == 4:
                    x, y, w, h = saved_geometry
                    self.setGeometry(int(x), int(y), int(w), int(h))
                else:
                    logger.warning(f"Invalid saved window geometry format: {saved_geometry}")
                    self.setGeometry(100, 100, 1400, 900)
            except (TypeError, ValueError) as e:
                logger.warning(f"Error parsing saved window geometry: {e}")
                self.setGeometry(100, 100, 1400, 900)

        self._create_menu_bar()
        self._create_toolbar()
        self._create_central_widget()
        self._create_status_bar()

        # Start background roster sync (non-blocking)
        self._start_background_roster_sync()

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
        self.theme_action = QAction("&Toggle Dark Mode", self)
        self.theme_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(self.theme_action)

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
        self.tabs.addTab(self._create_space_weather_tab(), "Space Weather")
        self.tabs.addTab(self._create_contacts_tab(), "Contacts")
        self.tabs.addTab(self._create_awards_tab(), "Awards")
        self.tabs.addTab(self._create_settings_tab(), "Settings")

        layout.addWidget(self.tabs)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def _create_logging_tab(self) -> QWidget:
        """Create contact logging tab with logging form and DX cluster spots"""
        from src.ui.logging_form import LoggingForm
        from src.skcc import SKCCSpotManager
        from src.ui.widgets.skcc_spots_widget import SKCCSpotWidget

        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Add logging form (top ~30%)
        self.logging_form = LoggingForm(self.db)
        layout.addWidget(self.logging_form, 0)

        # Add separator
        separator = QWidget()
        separator.setFixedHeight(5)
        separator.setStyleSheet("background-color: #cccccc;")
        layout.addWidget(separator)

        # Add DX Cluster spots (bottom ~70%)
        spot_manager = SKCCSpotManager(self.db)
        spots_widget = SKCCSpotWidget(spot_manager)

        # Connect spot selection to logging form
        spots_widget.spot_selected.connect(self._on_spot_selected)

        layout.addWidget(spots_widget, 1)

        widget.setLayout(layout)

        # Store references for cleanup
        self.spot_manager = spot_manager
        self.spots_widget = spots_widget

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

    def _create_space_weather_tab(self) -> QWidget:
        """Create space weather tab"""
        from src.ui.space_weather_widget import SpaceWeatherWidget
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(SpaceWeatherWidget())
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
        from PyQt6.QtWidgets import QTabWidget, QScrollArea
        from src.ui.centurion_progress_widget import CenturionProgressWidget
        from src.ui.tribune_progress_widget import TribuneProgressWidget
        from src.ui.senator_progress_widget import SenatorProgressWidget
        from src.ui.canadian_maple_progress_widget import CanadianMapleProgressWidget
        from src.ui.dx_award_progress_widget import DXAwardProgressWidget
        from src.ui.rag_chew_progress_widget import RagChewProgressWidget
        from src.ui.pfx_progress_widget import PFXProgressWidget
        from src.ui.triple_key_progress_widget import TripleKeyProgressWidget
        from src.ui.wac_progress_widget import WACProgressWidget

        widget = QWidget()
        layout = QVBoxLayout()

        # Create tab widget for different awards
        awards_tabs = QTabWidget()

        # Centurion Award Tab
        centurion_scroll = QScrollArea()
        centurion_scroll.setWidgetResizable(True)
        centurion_widget = CenturionProgressWidget(self.db)
        centurion_scroll.setWidget(centurion_widget)
        awards_tabs.addTab(centurion_scroll, "Centurion")

        # Tribune Award Tab
        tribune_scroll = QScrollArea()
        tribune_scroll.setWidgetResizable(True)
        tribune_widget = TribuneProgressWidget(self.db)
        tribune_scroll.setWidget(tribune_widget)
        awards_tabs.addTab(tribune_scroll, "Tribune")

        # Senator Award Tab
        senator_scroll = QScrollArea()
        senator_scroll.setWidgetResizable(True)
        senator_widget = SenatorProgressWidget(self.db)
        senator_scroll.setWidget(senator_widget)
        awards_tabs.addTab(senator_scroll, "Senator")

        # Canadian Maple Award Tab
        maple_scroll = QScrollArea()
        maple_scroll.setWidgetResizable(True)
        maple_widget = CanadianMapleProgressWidget(self.db)
        maple_scroll.setWidget(maple_widget)
        awards_tabs.addTab(maple_scroll, "Canadian Maple")

        # DX Award Tab
        dx_scroll = QScrollArea()
        dx_scroll.setWidgetResizable(True)
        dx_widget = DXAwardProgressWidget(self.db)
        dx_scroll.setWidget(dx_widget)
        awards_tabs.addTab(dx_scroll, "DX Award")

        # Rag Chew Award Tab
        ragchew_scroll = QScrollArea()
        ragchew_scroll.setWidgetResizable(True)
        ragchew_widget = RagChewProgressWidget(self.db)
        ragchew_scroll.setWidget(ragchew_widget)
        awards_tabs.addTab(ragchew_scroll, "Rag Chew")

        # PFX Award Tab
        pfx_scroll = QScrollArea()
        pfx_scroll.setWidgetResizable(True)
        pfx_widget = PFXProgressWidget(self.db)
        pfx_scroll.setWidget(pfx_widget)
        awards_tabs.addTab(pfx_scroll, "PFX")

        # Triple Key Award Tab
        triplekey_scroll = QScrollArea()
        triplekey_scroll.setWidgetResizable(True)
        triplekey_widget = TripleKeyProgressWidget(self.db)
        triplekey_scroll.setWidget(triplekey_widget)
        awards_tabs.addTab(triplekey_scroll, "Triple Key")

        # WAC Award Tab
        wac_scroll = QScrollArea()
        wac_scroll.setWidgetResizable(True)
        wac_widget = WACProgressWidget(self.db)
        wac_scroll.setWidget(wac_widget)
        awards_tabs.addTab(wac_scroll, "WAC")

        layout.addWidget(awards_tabs)
        widget.setLayout(layout)
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

    def _start_background_roster_sync(self) -> None:
        """Start SKCC roster sync in background thread (non-blocking)"""
        import threading

        def sync_roster():
            """Background thread function to sync SKCC roster"""
            try:
                self.status_label.showMessage("Syncing SKCC roster... (background)")
                logger.info("Starting background SKCC roster sync...")

                success = self.db.skcc_members.sync_membership_data()
                member_count = self.db.skcc_members.get_member_count()

                if success and member_count > 0:
                    status_msg = f"✓ SKCC roster synced: {member_count} members"
                    logger.info(status_msg)
                elif member_count > 0:
                    status_msg = f"⚠ SKCC roster (cache): {member_count} members available"
                    logger.warning(status_msg)
                else:
                    logger.warning("SKCC roster sync failed, no cached data")
                    if self.db.skcc_members.load_test_data():
                        status_msg = "⚠ Test data loaded - use 'Sync Roster' button to update"
                        logger.warning(status_msg)
                    else:
                        status_msg = "✗ No SKCC data available"

                # Update status bar from background thread
                self.status_label.showMessage(status_msg)

            except Exception as e:
                logger.error(f"Error syncing SKCC roster in background: {e}")
                self.status_label.showMessage(f"✗ Roster sync error: {str(e)}")

        # Start roster sync in daemon thread (won't block main thread)
        roster_thread = threading.Thread(target=sync_roster, daemon=True)
        roster_thread.start()

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

    def _toggle_theme(self) -> None:
        """Toggle between light and dark theme"""
        try:
            # Get current theme
            current_theme = self.config_manager.get("ui.theme", "light")
            new_theme = "dark" if current_theme == "light" else "light"

            # Apply the new theme
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                success = ThemeManager.apply_theme(app, new_theme)
                if success:
                    # Update config
                    self.config_manager.set("ui.theme", new_theme)
                    logger.info(f"Theme changed to: {new_theme}")
                else:
                    QMessageBox.warning(self, "Theme Error", f"Failed to apply {new_theme} theme")
            else:
                logger.error("Could not get QApplication instance")
        except Exception as e:
            logger.error(f"Error toggling theme: {e}", exc_info=True)
            QMessageBox.critical(self, "Theme Error", f"Error changing theme: {str(e)}")

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

        Ensures all background processes are stopped and database connections are properly closed before exit.
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
                # Save window geometry for next session
                try:
                    geometry = self.geometry()
                    # Store as list (YAML-serializable) not tuple
                    geometry_list = [geometry.x(), geometry.y(), geometry.width(), geometry.height()]
                    self.config_manager.set("ui.window_geometry", geometry_list)
                    logger.debug(f"Saved window geometry: {geometry_list}")
                except Exception as geom_error:
                    logger.warning(f"Error saving window geometry: {geom_error}")

                # Stop spot manager BEFORE closing database to prevent background thread errors
                try:
                    if hasattr(self, 'spot_manager') and self.spot_manager:
                        logger.info("Stopping SKCC spot manager...")
                        self.spot_manager.stop()
                except Exception as spot_error:
                    logger.error(f"Error stopping spot manager: {spot_error}", exc_info=True)

                # Perform automatic backup if enabled and destination is configured
                try:
                    auto_backup_enabled = self.config_manager.get("database.auto_backup_on_shutdown", True)
                    backup_destination = self.config_manager.get("database.backup_destination", "")

                    if auto_backup_enabled and backup_destination:
                        backup_dest_path = Path(backup_destination)
                        if backup_dest_path.exists() and backup_dest_path.is_dir():
                            logger.info("Performing automatic backup on shutdown...")
                            db_path = Path(self.config_manager.get("database.location"))

                            backup_manager = BackupManager()
                            result = backup_manager.backup_to_location(
                                database_path=db_path,
                                backup_destination=backup_dest_path
                            )

                            if result["success"]:
                                logger.info(f"Auto-backup completed: {result['backup_dir']}")
                            else:
                                logger.warning(f"Auto-backup failed: {result['message']}")
                        else:
                            logger.warning(f"Backup destination not available or not a directory: {backup_destination}")
                except Exception as backup_error:
                    logger.error(f"Error during auto-backup: {backup_error}", exc_info=True)

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
                # Try to stop spot manager if it exists
                if hasattr(self, 'spot_manager') and self.spot_manager:
                    try:
                        self.spot_manager.stop()
                    except Exception as spot_error:
                        logger.warning(f"Error stopping spot manager during error cleanup: {spot_error}")

                if hasattr(self, 'db') and self.db:
                    self.db.engine.dispose()
            except Exception as cleanup_error:
                logger.warning(f"Error during final cleanup: {cleanup_error}")
                # Continue with exit even if cleanup fails
            event.accept()
