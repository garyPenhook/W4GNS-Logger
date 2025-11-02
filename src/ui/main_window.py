"""
Main Application Window

PyQt6 main window with tabbed interface for all application features.
"""

import logging
from pathlib import Path
from typing import Dict, Any
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QMenuBar, QToolBar, QStatusBar, QMessageBox, QProgressDialog, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QIcon

from src.database.repository import DatabaseRepository
from src.config.settings import get_config_manager
from src.ui.theme_manager import ThemeManager
from src.backup.backup_manager import BackupManager

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window"""
    
    # Signal for thread-safe status bar updates
    status_message = pyqtSignal(str)

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
        self.setWindowTitle("W4GNS SKCC Logger")

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
        
        # Connect status signal for thread-safe updates
        self.status_message.connect(self._update_status_bar)

        # Defer roster sync to after window is shown (non-blocking)
        QTimer.singleShot(1000, self._start_background_roster_sync)

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

        # Track which tabs have been created (for lazy loading)
        self.tabs_created = {}

        # Add tabs - Logging tab created immediately, others lazy-loaded
        self.tabs.addTab(self._create_logging_tab(), "Logging")
        self.tabs_created[0] = True  # Logging tab is created

        # Add placeholder widgets for other tabs (will be created on first view)
        self.tabs.addTab(self._create_placeholder("QRP Progress - Loading..."), "QRP Progress")
        self.tabs_created[1] = False

        self.tabs.addTab(self._create_placeholder("Power Stats - Loading..."), "Power Stats")
        self.tabs_created[2] = False

        self.tabs.addTab(self._create_placeholder("Space Weather - Loading..."), "Space Weather")
        self.tabs_created[3] = False

        self.tabs.addTab(self._create_placeholder("Contacts - Loading..."), "Contacts")
        self.tabs_created[4] = False

        self.tabs.addTab(self._create_placeholder("Awards - Loading..."), "Awards")
        self.tabs_created[5] = False

        self.tabs.addTab(self._create_placeholder("Settings - Loading..."), "Settings")
        self.tabs_created[6] = False

        # Connect tab change signal to lazy-load tabs on first access
        self.tabs.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self.tabs)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def _create_logging_tab(self) -> QWidget:
        """Create contact logging tab with logging form and DX cluster spots"""
        from src.ui.logging_form import LoggingForm
        from src.skcc import SKCCSpotManager
        from src.ui.widgets.skcc_spots_widget import SKCCSpotWidget
        from src.ui.spot_matcher import SpotMatcher

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
        # Using SKCC Skimmer's proven RBN connection (fixes segmentation faults)
        spot_manager = SKCCSpotManager(self.db)
        
        # Get user's callsign and SKCC number for award eligibility analysis
        my_callsign = self.config_manager.get("general.operator_callsign", "")
        my_skcc_number = self.config_manager.get("adif.my_skcc_number", "")
        
        # Create spot matcher with award eligibility analyzer
        spot_matcher = SpotMatcher(self.db, self.config_manager, my_callsign, my_skcc_number)
        
        # Enable award eligibility analysis if we have SKCC number
        if my_callsign and my_skcc_number:
            spot_matcher.enable_award_eligibility(my_callsign, my_skcc_number)
        
        spots_widget = SKCCSpotWidget(spot_manager, spot_matcher)

        # Connect spot selection to logging form
        spots_widget.spot_selected.connect(self._on_spot_selected)

        layout.addWidget(spots_widget, 1)

        widget.setLayout(layout)

        # Store references for cleanup
        self.spot_manager = spot_manager
        self.spot_matcher = spot_matcher
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
        """Create awards dashboard tab with lazy-loaded sub-tabs"""
        from PyQt6.QtWidgets import QTabWidget, QPushButton, QScrollArea
        from src.ui.centurion_progress_widget import CenturionProgressWidget

        widget = QWidget()
        layout = QVBoxLayout()

        # Add application button toolbar
        toolbar_layout = QHBoxLayout()
        app_button = QPushButton("Generate Award Application")
        app_button.setToolTip("Create award application form for submission to award manager")
        app_button.clicked.connect(self._open_award_application_dialog)
        toolbar_layout.addWidget(app_button)
        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)

        # Create tab widget for different awards
        awards_tabs = QTabWidget()

        # Track which award sub-tabs have been created
        self.award_tabs_created = {}

        # Create first tab (Centurion) immediately so it's visible when Awards tab opens
        centurion_scroll = QScrollArea()
        centurion_scroll.setWidgetResizable(True)
        centurion_scroll.setWidget(CenturionProgressWidget(self.db))
        awards_tabs.addTab(centurion_scroll, "Centurion")
        self.award_tabs_created[0] = True

        # Add placeholder tabs for remaining awards (lazy-loaded on first view)
        award_names = [
            "Tribune", "Senator", "Canadian Maple",
            "DX Award", "Rag Chew", "PFX", "Triple Key",
            "WAC", "WAS", "QRP MPW"
        ]

        for i, name in enumerate(award_names, start=1):
            awards_tabs.addTab(self._create_placeholder(f"{name} - Loading..."), name)
            self.award_tabs_created[i] = False

        # Connect tab change signal for lazy loading
        awards_tabs.currentChanged.connect(self._on_award_tab_changed)

        # Store reference to awards tabs widget
        self.awards_tabs = awards_tabs

        layout.addWidget(awards_tabs)
        widget.setLayout(layout)
        return widget

    def _on_award_tab_changed(self, index: int) -> None:
        """Handle award sub-tab change - lazy-load on first access"""
        try:
            # Ignore invalid indices
            if index < 0 or index > 10:
                return

            # Check if this award tab has already been created
            if self.award_tabs_created.get(index, False):
                return  # Tab already created

            logger.info(f"Lazy-loading award tab {index} on first access...")

            # Block signals to prevent recursion during tab manipulation
            self.awards_tabs.blockSignals(True)

            try:
                from PyQt6.QtWidgets import QScrollArea

                # Create the appropriate award widget based on index
                scroll = None
                tab_name = ""

                if index == 0:  # Centurion
                    from src.ui.centurion_progress_widget import CenturionProgressWidget
                    scroll = QScrollArea()
                    scroll.setWidgetResizable(True)
                    scroll.setWidget(CenturionProgressWidget(self.db))
                    tab_name = "Centurion"
                elif index == 1:  # Tribune
                    from src.ui.tribune_progress_widget import TribuneProgressWidget
                    scroll = QScrollArea()
                    scroll.setWidgetResizable(True)
                    scroll.setWidget(TribuneProgressWidget(self.db))
                    tab_name = "Tribune"
                elif index == 2:  # Senator
                    from src.ui.senator_progress_widget import SenatorProgressWidget
                    scroll = QScrollArea()
                    scroll.setWidgetResizable(True)
                    scroll.setWidget(SenatorProgressWidget(self.db))
                    tab_name = "Senator"
                elif index == 3:  # Canadian Maple
                    from src.ui.canadian_maple_progress_widget import CanadianMapleProgressWidget
                    scroll = QScrollArea()
                    scroll.setWidgetResizable(True)
                    scroll.setWidget(CanadianMapleProgressWidget(self.db))
                    tab_name = "Canadian Maple"
                elif index == 4:  # DX Award
                    from src.ui.dx_award_progress_widget import DXAwardProgressWidget
                    scroll = QScrollArea()
                    scroll.setWidgetResizable(True)
                    scroll.setWidget(DXAwardProgressWidget(self.db))
                    tab_name = "DX Award"
                elif index == 5:  # Rag Chew
                    from src.ui.rag_chew_progress_widget import RagChewProgressWidget
                    scroll = QScrollArea()
                    scroll.setWidgetResizable(True)
                    scroll.setWidget(RagChewProgressWidget(self.db))
                    tab_name = "Rag Chew"
                elif index == 6:  # PFX
                    from src.ui.pfx_progress_widget import PFXProgressWidget
                    scroll = QScrollArea()
                    scroll.setWidgetResizable(True)
                    scroll.setWidget(PFXProgressWidget(self.db))
                    tab_name = "PFX"
                elif index == 7:  # Triple Key
                    from src.ui.triple_key_progress_widget import TripleKeyProgressWidget
                    scroll = QScrollArea()
                    scroll.setWidgetResizable(True)
                    scroll.setWidget(TripleKeyProgressWidget(self.db))
                    tab_name = "Triple Key"
                elif index == 8:  # WAC
                    from src.ui.wac_progress_widget import WACProgressWidget
                    scroll = QScrollArea()
                    scroll.setWidgetResizable(True)
                    scroll.setWidget(WACProgressWidget(self.db))
                    tab_name = "WAC"
                elif index == 9:  # WAS
                    from src.ui.was_progress_widget import WASProgressWidget
                    scroll = QScrollArea()
                    scroll.setWidgetResizable(True)
                    scroll.setWidget(WASProgressWidget(self.db))
                    tab_name = "WAS"
                elif index == 10:  # QRP MPW
                    from src.ui.qrp_mpw_progress_widget import QRPMPWProgressWidget
                    scroll = QScrollArea()
                    scroll.setWidgetResizable(True)
                    scroll.setWidget(QRPMPWProgressWidget(self.db))
                    tab_name = "QRP MPW"

                if scroll:
                    # Replace placeholder with actual widget
                    self.awards_tabs.removeTab(index)
                    self.awards_tabs.insertTab(index, scroll, tab_name)
                    self.awards_tabs.setCurrentIndex(index)
                    self.award_tabs_created[index] = True
                    logger.info(f"Award tab {index} ({tab_name}) created successfully")

            finally:
                # Re-enable signals
                self.awards_tabs.blockSignals(False)

        except Exception as e:
            logger.error(f"Error lazy-loading award tab {index}: {e}", exc_info=True)

    def _create_settings_tab(self) -> QWidget:
        """Create settings tab"""
        from src.ui.settings_editor import SettingsEditor
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(SettingsEditor())
        widget.setLayout(layout)
        return widget

    def _on_tab_changed(self, index: int) -> None:
        """Handle tab change - lazy-load tab content on first access"""
        try:
            # Check if this tab has already been created
            if self.tabs_created.get(index, False):
                return  # Tab already created, nothing to do

            logger.info(f"Lazy-loading tab {index} on first access...")

            # Block signals to prevent recursion during tab manipulation
            self.tabs.blockSignals(True)

            try:
                # Create the appropriate tab content based on index
                if index == 1:  # QRP Progress
                    self.tabs.removeTab(index)
                    self.tabs.insertTab(index, self._create_qrp_progress_tab(), "QRP Progress")
                    self.tabs_created[index] = True
                elif index == 2:  # Power Stats
                    self.tabs.removeTab(index)
                    self.tabs.insertTab(index, self._create_power_stats_tab(), "Power Stats")
                    self.tabs_created[index] = True
                elif index == 3:  # Space Weather
                    self.tabs.removeTab(index)
                    self.tabs.insertTab(index, self._create_space_weather_tab(), "Space Weather")
                    self.tabs_created[index] = True
                elif index == 4:  # Contacts
                    self.tabs.removeTab(index)
                    self.tabs.insertTab(index, self._create_contacts_tab(), "Contacts")
                    self.tabs_created[index] = True
                elif index == 5:  # Awards
                    self.tabs.removeTab(index)
                    self.tabs.insertTab(index, self._create_awards_tab(), "Awards")
                    self.tabs_created[index] = True
                elif index == 6:  # Settings
                    self.tabs.removeTab(index)
                    self.tabs.insertTab(index, self._create_settings_tab(), "Settings")
                    self.tabs_created[index] = True

                # Switch back to the newly created tab
                self.tabs.setCurrentIndex(index)

                logger.info(f"Tab {index} created successfully")

            finally:
                # Re-enable signals
                self.tabs.blockSignals(False)

        except Exception as e:
            logger.error(f"Error lazy-loading tab {index}: {e}", exc_info=True)

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
    
    def _update_status_bar(self, message: str) -> None:
        """Thread-safe status bar update (called via signal)"""
        if self.status_label:
            self.status_label.showMessage(message)

    def _start_background_roster_sync(self) -> None:
        """Start SKCC roster sync in background thread (non-blocking)"""
        import threading

        def sync_roster():
            """Background thread function to sync SKCC roster"""
            try:
                # Use signal for thread-safe status update
                self.status_message.emit("Syncing SKCC roster... (background)")
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

                # Use signal for thread-safe status update
                self.status_message.emit(status_msg)

            except Exception as e:
                logger.error(f"Error syncing SKCC roster in background: {e}")
                # Use signal for thread-safe status update
                self.status_message.emit(f"✗ Roster sync error: {str(e)}")

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
                help_dialog.setWindowTitle("Help - W4GNS SKCC Logger")
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
            "About W4GNS SKCC Logger",
            "W4GNS SKCC Logger v1.8\n\n"
            "A comprehensive SKCC-focused ham radio contact logging application\n"
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

    def _open_award_application_dialog(self) -> None:
        """Open award application dialog"""
        try:
            from src.ui.dialogs.award_application_dialog import AwardApplicationDialog
            dialog = AwardApplicationDialog(self.db, self)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error opening award application dialog: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to open award application dialog: {str(e)}")

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
                # Set up emergency shutdown timer - force exit after 5 seconds if something hangs
                from PyQt6.QtCore import QTimer
                emergency_timer = QTimer()
                emergency_timer.setSingleShot(True)
                emergency_timer.timeout.connect(lambda: (
                    logger.warning("Emergency shutdown timeout reached - forcing exit"),
                    QApplication.quit()
                ))
                emergency_timer.start(5000)  # 5 second hard timeout

                # Create progress dialog for backup operations
                progress = QProgressDialog("Preparing to exit...", None, 0, 100, self)
                progress.setWindowTitle("Closing Application")
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.setMinimumDuration(0)  # Show immediately
                progress.setCancelButton(None)  # Can't cancel shutdown
                progress.setValue(0)

                # Save window geometry for next session
                try:
                    progress.setLabelText("Saving window settings...")
                    progress.setValue(5)
                    
                    geometry = self.geometry()
                    # Store as list (YAML-serializable) not tuple
                    geometry_list = [geometry.x(), geometry.y(), geometry.width(), geometry.height()]
                    self.config_manager.set("ui.window_geometry", geometry_list)
                    logger.debug(f"Saved window geometry: {geometry_list}")
                except Exception as geom_error:
                    logger.warning(f"Error saving window geometry: {geom_error}")

                # Stop all background threads and services
                try:
                    progress.setLabelText("Stopping background services...")
                    progress.setValue(10)

                    # Stop spot manager first
                    if hasattr(self, 'spot_manager') and self.spot_manager:
                        logger.info("Stopping SKCC spot manager...")
                        self.spot_manager.stop()
                        QApplication.processEvents()

                    # Close all tab widgets to trigger their closeEvent handlers
                    # This ensures all worker threads are stopped
                    logger.info("Closing all tab widgets...")
                    from PyQt6.QtCore import QThread

                    for i in range(self.tabs.count()):
                        widget = self.tabs.widget(i)
                        if widget:
                            widget.close()

                    # Give widgets time to close their threads
                    QApplication.processEvents()

                    # Wait for any remaining QThreads to finish (with timeout)
                    import time
                    max_wait = 1.0  # 1 second max
                    start_time = time.time()
                    while time.time() - start_time < max_wait:
                        active_threads = [obj for obj in self.findChildren(QThread) if obj.isRunning()]
                        if not active_threads:
                            break
                        QApplication.processEvents()
                        time.sleep(0.05)  # 50ms

                    # Force terminate any remaining threads
                    remaining_threads = [obj for obj in self.findChildren(QThread) if obj.isRunning()]
                    if remaining_threads:
                        logger.warning(f"Force terminating {len(remaining_threads)} remaining threads")
                        for thread in remaining_threads:
                            thread.terminate()
                            thread.wait(100)

                except Exception as spot_error:
                    logger.error(f"Error stopping background services: {spot_error}", exc_info=True)

                # Create ADIF backup on shutdown (with timeout protection)
                progress.setLabelText("Creating ADIF backup...")
                progress.setValue(20)
                QApplication.processEvents()  # Keep UI responsive

                try:
                    logger.info("Creating ADIF backup on shutdown...")
                    if hasattr(self, 'db') and self.db:
                        # Get all contacts from database
                        all_contacts = self.db.get_all_contacts()
                        if all_contacts and len(all_contacts) > 0:
                            backup_manager = BackupManager()
                            my_skcc = self.config_manager.get("adif.my_skcc_number", "")
                            my_callsign = self.config_manager.get("general.operator_callsign", "")

                            result = backup_manager.create_adif_backup(
                                contacts=all_contacts,
                                my_skcc=my_skcc if my_skcc else None,
                                my_callsign=my_callsign if my_callsign and my_callsign != 'MYCALL' else None,
                                backup_location=None,  # Uses default: ~/.w4gns_logger/Logs
                                max_backups=5
                            )

                            if result["success"]:
                                logger.info(f"ADIF backup created on shutdown: {result['message']}")
                            else:
                                logger.warning(f"ADIF backup on shutdown failed: {result['message']}")
                        else:
                            logger.warning("No contacts found for ADIF backup")
                except Exception as adif_backup_error:
                    logger.error(f"Error creating ADIF backup on shutdown (continuing anyway): {adif_backup_error}", exc_info=True)

                # Create database backup on shutdown (with timeout protection)
                progress.setLabelText("Creating database backup...")
                progress.setValue(40)
                QApplication.processEvents()  # Keep UI responsive

                try:
                    logger.info("Creating database backup on shutdown...")
                    db_path = Path(self.config_manager.get("database.location"))
                    backup_manager = BackupManager()

                    result = backup_manager.create_database_backup(
                        database_path=db_path,
                        backup_location=None,  # Uses default: ~/.w4gns_logger/Logs
                        max_backups=5
                    )

                    if result["success"]:
                        logger.info(f"Database backup created on shutdown: {result['message']}")
                    else:
                        logger.warning(f"Database backup on shutdown failed: {result['message']}")
                except Exception as db_backup_error:
                    logger.error(f"Error creating database backup on shutdown (continuing anyway): {db_backup_error}", exc_info=True)

                # Perform additional USB/external backup if destination is configured
                try:
                    auto_backup_enabled = self.config_manager.get("database.auto_backup_on_shutdown", True)
                    backup_destination = self.config_manager.get("database.backup_destination", "")

                    if auto_backup_enabled and backup_destination:
                        backup_dest_path = Path(backup_destination)
                        if backup_dest_path.exists() and backup_dest_path.is_dir():
                            progress.setLabelText("Backing up to external location...")
                            progress.setValue(60)
                            
                            logger.info("Performing additional backup to USB/external destination...")
                            backup_manager = BackupManager()

                            # Backup database to secondary location
                            try:
                                db_path = Path(self.config_manager.get("database.location"))
                                result = backup_manager.backup_to_location(
                                    database_path=db_path,
                                    backup_destination=backup_dest_path
                                )

                                if result["success"]:
                                    logger.info(f"Database backup to secondary location completed: {result['backup_dir']}")
                                else:
                                    logger.warning(f"Database backup to secondary location failed: {result['message']}")
                            except Exception as db_backup_error:
                                logger.error(f"Error backing up database to secondary location: {db_backup_error}", exc_info=True)

                            # Backup most recent ADIF to secondary location
                            progress.setLabelText("Backing up ADIF to external location...")
                            progress.setValue(80)
                            
                            try:
                                result = backup_manager.backup_adif_to_secondary(
                                    adif_source_dir=None,  # Uses default: ~/.w4gns_logger/Logs
                                    backup_destination=backup_dest_path,
                                    max_backups=5
                                )

                                if result["success"]:
                                    logger.info(f"ADIF backup to secondary location completed: {result['message']}")
                                else:
                                    logger.warning(f"ADIF backup to secondary location failed: {result['message']}")
                            except Exception as adif_backup_error:
                                logger.error(f"Error backing up ADIF to secondary location: {adif_backup_error}", exc_info=True)
                        else:
                            logger.warning(f"USB/external backup destination not available: {backup_destination}")
                except Exception as backup_error:
                    logger.error(f"Error during USB/external backup: {backup_error}", exc_info=True)

                # Clean up database resources
                progress.setLabelText("Closing database connection...")
                progress.setValue(90)

                try:
                    if hasattr(self, 'db') and self.db:
                        try:
                            self.db.engine.dispose()
                            logger.info("Database connection closed gracefully")
                        except Exception as dispose_error:
                            # Suppress "Cannot operate on a closed database" errors during cleanup
                            # These are harmless and occur when SQLAlchemy tries to clean up connections
                            # that were already closed or are in the process of closing
                            error_msg = str(dispose_error).lower()
                            if "closed database" in error_msg or "database is locked" in error_msg:
                                logger.debug(f"Harmless database cleanup error during shutdown: {dispose_error}")
                            else:
                                logger.error(f"Error closing database connection: {dispose_error}", exc_info=True)
                except Exception as db_error:
                    logger.error(f"Unexpected error during database cleanup: {db_error}", exc_info=True)

                progress.setLabelText("Finishing up...")
                progress.setValue(100)
                QApplication.processEvents()  # Final UI update

                # Cancel emergency timer - we completed successfully
                emergency_timer.stop()

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
                    try:
                        self.db.engine.dispose()
                    except Exception as dispose_error:
                        # Suppress harmless database cleanup errors
                        error_msg = str(dispose_error).lower()
                        if "closed database" not in error_msg and "database is locked" not in error_msg:
                            logger.warning(f"Error closing database during error cleanup: {dispose_error}")
            except Exception as cleanup_error:
                logger.warning(f"Error during final cleanup: {cleanup_error}")
                # Continue with exit even if cleanup fails
            event.accept()
