"""
Settings Editor Widget

Provides a UI for editing application configuration with the ability to:
- View all settings organized by category
- Edit settings directly in the GUI
- Save changes to config.yaml
- Reset to defaults
- Export/Import settings
"""

import logging
from pathlib import Path
from typing import Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QGroupBox, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QCheckBox, QPushButton, QMessageBox,
    QFormLayout, QFileDialog, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.config.settings import get_config_manager
from src.ui.theme_manager import ThemeManager
from src.backup.backup_manager import BackupManager

logger = logging.getLogger(__name__)


class SettingsEditor(QWidget):
    """Settings editor widget for configuration management"""

    def __init__(self, parent=None):
        """
        Initialize settings editor

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.config_manager = get_config_manager()
        self.settings_widgets: Dict[str, Any] = {}
        self.raw_config_initial_text = ""  # Track initial raw config for comparison
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize UI components"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(5)  # Reduce spacing throughout

        # Create tabs for different setting categories
        self.tabs = QTabWidget()

        # General settings
        self.tabs.addTab(self._create_general_tab(), "General")

        # Database settings
        self.tabs.addTab(self._create_database_tab(), "Database")

        # ADIF settings
        self.tabs.addTab(self._create_adif_tab(), "ADIF")

        # UI settings
        self.tabs.addTab(self._create_ui_tab(), "User Interface")

        # Features settings
        self.tabs.addTab(self._create_features_tab(), "Features")

        # QRZ.com integration
        self.tabs.addTab(self._create_qrz_tab(), "QRZ.com")

        # Raw config editor
        self.tabs.addTab(self._create_raw_config_tab(), "Raw Config")

        main_layout.addWidget(self.tabs)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)  # Reduce spacing between buttons
        button_layout.addStretch()

        # Reset button
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        button_layout.addWidget(reset_btn)

        # Save button (primary)
        save_btn = QPushButton("Save Settings")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(save_btn)

        main_layout.addLayout(button_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

    def _create_general_tab(self) -> QWidget:
        """Create General settings tab"""
        widget = QWidget()
        form_layout = QFormLayout()
        form_layout.setSpacing(5)  # Reduce spacing between label and field

        # Operator callsign
        callsign_input = QLineEdit()
        callsign_input.setText(self.config_manager.get("general.operator_callsign", "MYCALL"))
        self.settings_widgets["general.operator_callsign"] = callsign_input
        form_layout.addRow("Operator Callsign:", callsign_input)

        # Home grid square
        grid_input = QLineEdit()
        grid_input.setText(self.config_manager.get("general.home_grid", "FN20qd"))
        grid_input.setPlaceholderText("e.g., FN20qd")
        self.settings_widgets["general.home_grid"] = grid_input
        form_layout.addRow("Home Grid Square:", grid_input)

        # Default mode
        mode_combo = QComboBox()
        modes = ["CW", "SSB", "FM", "AM", "RTTY", "PSK31", "PSK63", "JT65", "JT9", "WSPR"]
        mode_combo.addItems(modes)
        default_mode = self.config_manager.get("general.default_mode", "SSB")
        mode_combo.setCurrentText(default_mode)
        self.settings_widgets["general.default_mode"] = mode_combo
        form_layout.addRow("Default Mode:", mode_combo)

        # Default power
        power_spin = QSpinBox()
        power_spin.setRange(0, 10000)
        power_spin.setValue(self.config_manager.get("general.default_power", 100))
        power_spin.setSuffix(" W")
        self.settings_widgets["general.default_power"] = power_spin
        form_layout.addRow("Default TX Power:", power_spin)

        # Auto-save interval
        autosave_spin = QSpinBox()
        autosave_spin.setRange(10, 3600)
        autosave_spin.setValue(self.config_manager.get("general.auto_save_interval", 60))
        autosave_spin.setSuffix(" seconds")
        self.settings_widgets["general.auto_save_interval"] = autosave_spin
        form_layout.addRow("Auto-Save Interval:", autosave_spin)

        widget.setLayout(form_layout)
        return widget

    def _create_database_tab(self) -> QWidget:
        """Create Database settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        form_layout.setSpacing(5)  # Reduce spacing between label and field

        # Database location
        db_layout = QHBoxLayout()
        db_layout.setSpacing(5)  # Reduce spacing between input and button
        db_input = QLineEdit()
        db_input.setText(self.config_manager.get("database.location", ""))
        db_input.setReadOnly(True)
        self.settings_widgets["database.location"] = db_input
        db_button = QPushButton("Browse...")
        db_button.clicked.connect(self._browse_database)
        db_layout.addWidget(db_input)
        db_layout.addWidget(db_button)
        form_layout.addRow("Database Location:", db_layout)

        # Backup enabled
        backup_check = QCheckBox("Enable automatic backups")
        backup_check.setChecked(self.config_manager.get("database.backup_enabled", True))
        self.settings_widgets["database.backup_enabled"] = backup_check
        form_layout.addRow("", backup_check)

        # Backup interval
        backup_spin = QSpinBox()
        backup_spin.setRange(1, 168)  # 1 hour to 1 week
        backup_spin.setValue(self.config_manager.get("database.backup_interval", 24))
        backup_spin.setSuffix(" hours")
        self.settings_widgets["database.backup_interval"] = backup_spin
        form_layout.addRow("Backup Interval:", backup_spin)

        layout.addLayout(form_layout)
        layout.addSpacing(10)

        # Backup Destination section
        backup_dest_layout = QFormLayout()
        backup_dest_layout.setSpacing(5)

        # Backup destination display and button
        backup_dest_layout_h = QHBoxLayout()
        backup_dest_layout_h.setSpacing(5)
        backup_dest_input = QLineEdit()
        backup_dest = self.config_manager.get("database.backup_destination", "")
        backup_dest_input.setText(backup_dest if backup_dest else "(Not configured)")
        backup_dest_input.setReadOnly(True)
        self.settings_widgets["database.backup_destination"] = backup_dest_input
        backup_dest_button = QPushButton("Browse...")
        backup_dest_button.setToolTip("Select USB drive or external location for backups")
        backup_dest_button.clicked.connect(self._browse_backup_destination)
        backup_dest_layout_h.addWidget(backup_dest_input)
        backup_dest_layout_h.addWidget(backup_dest_button)
        backup_dest_layout.addRow("Backup Destination:", backup_dest_layout_h)

        # Auto-backup on shutdown
        auto_backup_check = QCheckBox("Automatically backup when closing application")
        auto_backup_check.setChecked(self.config_manager.get("database.auto_backup_on_shutdown", True))
        auto_backup_check.setToolTip("If enabled, database and ADIF files will be backed up to the destination when you close the program")
        self.settings_widgets["database.auto_backup_on_shutdown"] = auto_backup_check
        backup_dest_layout.addRow("", auto_backup_check)

        layout.addLayout(backup_dest_layout)
        layout.addSpacing(10)

        # Manual Backup button section
        backup_group = QGroupBox("Manual Backup")
        backup_group_layout = QVBoxLayout()
        backup_now_btn = QPushButton("Backup Now")
        backup_now_btn.setToolTip("Create a backup to the configured destination immediately")
        backup_now_btn.clicked.connect(self._backup_now)
        backup_group_layout.addWidget(backup_now_btn)
        backup_group.setLayout(backup_group_layout)
        layout.addWidget(backup_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_adif_tab(self) -> QWidget:
        """Create ADIF settings tab"""
        widget = QWidget()
        form_layout = QFormLayout()
        form_layout.setSpacing(5)  # Reduce spacing between label and field

        # Operator's SKCC number
        skcc_input = QLineEdit()
        skcc_input.setText(self.config_manager.get("adif.my_skcc_number", ""))
        skcc_input.setPlaceholderText("e.g., 14276T")
        skcc_input.setToolTip("Your SKCC member number (with suffix if applicable)")
        self.settings_widgets["adif.my_skcc_number"] = skcc_input
        form_layout.addRow("Your SKCC Number:", skcc_input)

        form_layout.addRow("", QLabel(""))  # Spacer

        # Default export format
        export_format_combo = QComboBox()
        export_format_combo.addItem("ADI (Text Format)", "adi")
        export_format_combo.addItem("ADX (XML Format)", "adx")
        current_format = self.config_manager.get("adif.export_default_format", "adi")
        if current_format == "adx":
            export_format_combo.setCurrentIndex(1)
        else:
            export_format_combo.setCurrentIndex(0)
        self.settings_widgets["adif.export_default_format"] = export_format_combo
        form_layout.addRow("Export Format:", export_format_combo)

        # Import conflict strategy
        conflict_combo = QComboBox()
        conflict_combo.addItem("Skip duplicates", "skip")
        conflict_combo.addItem("Update existing", "update")
        conflict_combo.addItem("Add all contacts", "append")
        current_strategy = self.config_manager.get("adif.import_conflict_strategy", "skip")
        if current_strategy == "update":
            conflict_combo.setCurrentIndex(1)
        elif current_strategy == "append":
            conflict_combo.setCurrentIndex(2)
        else:
            conflict_combo.setCurrentIndex(0)
        self.settings_widgets["adif.import_conflict_strategy"] = conflict_combo
        form_layout.addRow("When Importing Duplicates:", conflict_combo)

        # Include all fields checkbox
        include_all_check = QCheckBox("Include all fields when exporting")
        include_all_check.setChecked(self.config_manager.get("adif.include_all_fields", True))
        include_all_check.setToolTip("If unchecked, only export essential ADIF fields")
        self.settings_widgets["adif.include_all_fields"] = include_all_check
        form_layout.addRow("", include_all_check)

        widget.setLayout(form_layout)
        return widget

    def _create_ui_tab(self) -> QWidget:
        """Create UI settings tab"""
        widget = QWidget()
        form_layout = QFormLayout()
        form_layout.setSpacing(5)  # Reduce spacing between label and field

        # Theme
        theme_combo = QComboBox()
        theme_combo.addItems(["light", "dark"])
        theme_combo.setCurrentText(self.config_manager.get("ui.theme", "light"))
        self.settings_widgets["ui.theme"] = theme_combo
        form_layout.addRow("Theme:", theme_combo)

        # Font size
        font_spin = QSpinBox()
        font_spin.setRange(8, 20)
        font_spin.setValue(self.config_manager.get("ui.font_size", 10))
        font_spin.setSuffix(" pt")
        self.settings_widgets["ui.font_size"] = font_spin
        form_layout.addRow("Font Size:", font_spin)

        widget.setLayout(form_layout)
        return widget

    def _create_features_tab(self) -> QWidget:
        """Create Features settings tab"""
        widget = QWidget()
        form_layout = QFormLayout()
        form_layout.setSpacing(5)  # Reduce spacing between label and field

        # DX Cluster
        cluster_check = QCheckBox("Enable DX Cluster")
        cluster_check.setChecked(self.config_manager.get("dx_cluster.enabled", True))
        self.settings_widgets["dx_cluster.enabled"] = cluster_check
        form_layout.addRow("", cluster_check)

        cluster_auto_check = QCheckBox("Auto-connect to cluster")
        cluster_auto_check.setChecked(self.config_manager.get("dx_cluster.auto_connect", False))
        self.settings_widgets["dx_cluster.auto_connect"] = cluster_auto_check
        form_layout.addRow("", cluster_auto_check)

        cluster_heartbeat = QSpinBox()
        cluster_heartbeat.setRange(10, 300)
        cluster_heartbeat.setValue(self.config_manager.get("dx_cluster.heartbeat_interval", 60))
        cluster_heartbeat.setSuffix(" seconds")
        self.settings_widgets["dx_cluster.heartbeat_interval"] = cluster_heartbeat
        form_layout.addRow("Cluster Heartbeat:", cluster_heartbeat)

        form_layout.addRow("", QLabel(""))  # Spacer

        # Note: QRZ.com settings are in the dedicated QRZ.com tab
        form_layout.addRow("", QLabel("QRZ.com settings are in the QRZ.com tab"))

        form_layout.addRow("", QLabel(""))  # Spacer

        # Awards
        awards_check = QCheckBox("Enable award tracking")
        awards_check.setChecked(self.config_manager.get("awards.enabled", True))
        self.settings_widgets["awards.enabled"] = awards_check
        form_layout.addRow("", awards_check)

        awards_auto_check = QCheckBox("Auto-calculate award progress")
        awards_auto_check.setChecked(self.config_manager.get("awards.auto_calculate", True))
        self.settings_widgets["awards.auto_calculate"] = awards_auto_check
        form_layout.addRow("", awards_auto_check)

        form_layout.addRow("", QLabel(""))  # Spacer

        # SKCC Spots Monitoring
        skcc_spots_check = QCheckBox("Enable SKCC member spot monitoring")
        skcc_spots_check.setChecked(self.config_manager.get("skcc.spots_enabled", False))
        self.settings_widgets["skcc.spots_enabled"] = skcc_spots_check
        form_layout.addRow("", skcc_spots_check)

        skcc_auto_start_check = QCheckBox("Auto-start monitoring on launch")
        skcc_auto_start_check.setChecked(self.config_manager.get("skcc.auto_start_spots", False))
        self.settings_widgets["skcc.auto_start_spots"] = skcc_auto_start_check
        form_layout.addRow("", skcc_auto_start_check)

        skcc_unworked_check = QCheckBox("Show unworked stations only")
        skcc_unworked_check.setChecked(self.config_manager.get("skcc.unworked_only", False))
        self.settings_widgets["skcc.unworked_only"] = skcc_unworked_check
        form_layout.addRow("", skcc_unworked_check)

        skcc_min_strength = QSpinBox()
        skcc_min_strength.setRange(0, 50)
        skcc_min_strength.setValue(self.config_manager.get("skcc.min_signal_strength", 0))
        skcc_min_strength.setSuffix(" dB")
        self.settings_widgets["skcc.min_signal_strength"] = skcc_min_strength
        form_layout.addRow("Minimum Signal Strength:", skcc_min_strength)

        skcc_spot_age = QSpinBox()
        skcc_spot_age.setRange(60, 3600)
        skcc_spot_age.setValue(self.config_manager.get("skcc.max_spot_age_seconds", 300))
        skcc_spot_age.setSuffix(" seconds")
        self.settings_widgets["skcc.max_spot_age_seconds"] = skcc_spot_age
        form_layout.addRow("Max Spot Age:", skcc_spot_age)

        form_layout.addRow("", QLabel(""))  # Spacer

        # SKCC Goals (awards you're pursuing)
        form_layout.addRow(QLabel("<b>SKCC Goals (Awards You're Pursuing)</b>"), QLabel(""))

        # Create goal checkboxes
        goals_available = ["Centurion", "Tribune", "Senator", "WAS-C", "WAS-T", "WAS-S",
                          "QRP", "QRP-MPW", "K3Y", "Rag Chew", "DX", "TripleKey", "Canadian Maple"]
        current_goals = self.config_manager.get("skcc.goals", [])

        for goal in goals_available:
            goal_check = QCheckBox(goal)
            goal_check.setChecked(goal in current_goals)
            self.settings_widgets[f"skcc.goals.{goal}"] = goal_check
            form_layout.addRow("", goal_check)

        form_layout.addRow("", QLabel(""))  # Spacer

        # SKCC Targets (awards you want to help others earn)
        form_layout.addRow(QLabel("<b>SKCC Targets (Help Others Achieve)</b>"), QLabel(""))

        targets_available = ["Centurion", "Tribune", "Senator", "WAS-C", "WAS-T", "WAS-S",
                           "QRP", "QRP-MPW", "K3Y", "Rag Chew", "DX", "TripleKey", "Canadian Maple"]
        current_targets = self.config_manager.get("skcc.targets", [])

        for target in targets_available:
            target_check = QCheckBox(target)
            target_check.setChecked(target in current_targets)
            self.settings_widgets[f"skcc.targets.{target}"] = target_check
            form_layout.addRow("", target_check)

        widget.setLayout(form_layout)
        return widget

    def _create_qrz_tab(self) -> QWidget:
        """Create QRZ.com integration settings tab"""
        widget = QWidget()
        form_layout = QFormLayout()
        form_layout.setSpacing(5)  # Reduce spacing between label and field

        # Enable QRZ.com integration
        qrz_enable_check = QCheckBox("Enable QRZ.com integration")
        qrz_enable_check.setChecked(self.config_manager.get("qrz.enabled", False))
        qrz_enable_check.setToolTip("Enable callsign lookups and logbook management via QRZ.com")
        self.settings_widgets["qrz.enabled"] = qrz_enable_check
        form_layout.addRow("", qrz_enable_check)

        form_layout.addRow("", QLabel(""))  # Spacer

        # QRZ.com username
        username_input = QLineEdit()
        username_input.setText(self.config_manager.get("qrz.username", ""))
        username_input.setPlaceholderText("Your QRZ.com username")
        username_input.setToolTip("QRZ.com account username")
        self.settings_widgets["qrz.username"] = username_input
        form_layout.addRow("QRZ.com Username:", username_input)

        # QRZ.com password
        password_input = QLineEdit()
        password_input.setText(self.config_manager.get("qrz.password", ""))
        password_input.setPlaceholderText("Your QRZ.com password")
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_input.setToolTip("QRZ.com account password for callsign lookups")
        self.settings_widgets["qrz.password"] = password_input
        form_layout.addRow("QRZ.com Password:", password_input)

        # QRZ.com API Key
        api_key_input = QLineEdit()
        api_key_input.setText(self.config_manager.get("qrz.api_key", ""))
        api_key_input.setPlaceholderText("Your QRZ.com API Key")
        api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_key_input.setToolTip("QRZ.com API Key for logbook uploads (get from https://www.qrz.com)")
        self.settings_widgets["qrz.api_key"] = api_key_input
        form_layout.addRow("QRZ.com API Key:", api_key_input)

        form_layout.addRow("", QLabel(""))  # Spacer

        # Auto-fetch callsign info
        auto_fetch_check = QCheckBox("Auto-fetch callsign info from QRZ")
        auto_fetch_check.setChecked(self.config_manager.get("qrz.auto_fetch", False))
        auto_fetch_check.setToolTip("Automatically look up callsign info when entering a callsign in the logging form")
        self.settings_widgets["qrz.auto_fetch"] = auto_fetch_check
        form_layout.addRow("", auto_fetch_check)

        # Auto-upload contacts
        auto_upload_check = QCheckBox("Auto-upload contacts to QRZ logbook")
        auto_upload_check.setChecked(self.config_manager.get("qrz.auto_upload", False))
        auto_upload_check.setToolTip("Automatically upload logged contacts to your QRZ.com logbook")
        self.settings_widgets["qrz.auto_upload"] = auto_upload_check
        form_layout.addRow("", auto_upload_check)

        form_layout.addRow("", QLabel(""))  # Spacer

        # Test connection button
        test_btn = QPushButton("Test Callsign Lookup")
        test_btn.clicked.connect(self._test_qrz_connection)
        test_btn.setToolTip("Test QRZ.com callsign lookup credentials (username/password)")
        form_layout.addRow("", test_btn)

        form_layout.addRow("", QLabel(""))  # Spacer

        # Info label
        info_label = QLabel(
            "QRZ.com Integration:\n"
            "• Username/Password: Required for callsign lookups\n"
            "• API Key: Optional, required for logbook uploads\n"
            "• Get API Key from: Settings → Account → API → Logbook API Key\n"
            "• Click 'Test Callsign Lookup' to verify credentials\n"
            "• Visit https://www.qrz.com for account info"
        )
        info_label.setStyleSheet("color: #666; font-size: 9pt;")
        form_layout.addRow("", info_label)

        widget.setLayout(form_layout)
        return widget

    def _test_qrz_connection(self) -> None:
        """Test QRZ.com connection with provided credentials"""
        username = self.settings_widgets["qrz.username"].text()
        password = self.settings_widgets["qrz.password"].text()

        if not username or not password:
            QMessageBox.warning(
                self,
                "Missing Credentials",
                "Please enter your QRZ.com username and password."
            )
            return

        try:
            import urllib.request
            import urllib.parse
            import xml.etree.ElementTree as ET

            # QRZ.com XML API endpoint
            qrz_url = "https://xmldata.qrz.com/xml/current/"
            params = urllib.parse.urlencode({
                'username': username,
                'password': password,
                'agent': 'W4GNSLogger/1.0'
            })

            # Test authentication
            try:
                from src.utils.network import urlopen_with_retries
                opener = urlopen_with_retries(f"{qrz_url}?{params}", timeout=10, retries=3, backoff=0.5)
            except Exception:
                opener = urllib.request.urlopen(f"{qrz_url}?{params}", timeout=10)
            with opener as response:
                data = response.read()
                root = ET.fromstring(data)

                # Helper function to find elements (handles namespaces)
                def find_elem(parent, tag):
                    # Try direct find first
                    result = parent.find(tag)
                    if result is not None:
                        return result
                    # Try with any namespace
                    for child in parent:
                        child_tag = child.tag
                        if '}' in child_tag:
                            child_tag = child_tag.split('}')[1]
                        if child_tag == tag:
                            return child
                    return None

                # Check for error element
                error_elem = find_elem(root, 'Error')
                if error_elem is not None:
                    error_msg = error_elem.text or "Unknown error"
                    QMessageBox.critical(
                        self,
                        "Connection Failed",
                        f"QRZ.com authentication failed:\n{error_msg}"
                    )
                    logger.error(f"QRZ authentication error: {error_msg}")
                    return

                # Check for session element with key
                session_elem = find_elem(root, 'Session')
                if session_elem is not None:
                    key_elem = find_elem(session_elem, 'Key')
                    if key_elem is not None and key_elem.text:
                        QMessageBox.information(
                            self,
                            "Connection Successful",
                            "QRZ.com credentials are valid!\n"
                            "Session key obtained successfully."
                        )
                        logger.info("QRZ.com connection test successful")
                        return

                # If we get here, response was unexpected
                logger.warning("Unexpected QRZ response structure")
                QMessageBox.warning(
                    self,
                    "Unexpected Response",
                    "QRZ.com returned an unexpected response.\n"
                    "Please verify your username and password are correct.\n\n"
                    "If the issue persists, check:\n"
                    "• Your internet connection\n"
                    "• QRZ.com service status\n"
                    "• Your account status at qrz.com"
                )

        except urllib.error.HTTPError as e:
            if e.code == 401:
                QMessageBox.critical(
                    self,
                    "Authentication Failed",
                    "Invalid username or password.\n\n"
                    "Please check your QRZ.com credentials."
                )
            else:
                QMessageBox.critical(
                    self,
                    "Connection Error",
                    f"QRZ.com returned HTTP {e.code}:\n{str(e)}"
                )
            logger.error(f"QRZ.com HTTP error {e.code}: {e}")
        except urllib.error.URLError as e:
            QMessageBox.critical(
                self,
                "Connection Error",
                f"Failed to connect to QRZ.com:\n{str(e)}\n\n"
                "Please check your internet connection."
            )
            logger.error(f"QRZ.com connection error: {e}")
        except ET.ParseError as e:
            QMessageBox.critical(
                self,
                "Parse Error",
                f"Failed to parse QRZ.com response:\n{str(e)}"
            )
            logger.error(f"QRZ.com XML parse error: {e}")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error testing QRZ.com connection:\n{str(e)}"
            )
            logger.error(f"QRZ.com test error: {e}", exc_info=True)

    def _create_raw_config_tab(self) -> QWidget:
        """Create raw config editor tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Info label
        info_label = QLabel(
            "Advanced: Edit raw YAML configuration\n"
            "Warning: Incorrect syntax may cause errors"
        )
        info_label.setStyleSheet("color: #FF9800; font-weight: bold;")
        layout.addWidget(info_label)

        # Config display/editor
        from PyQt6.QtWidgets import QPlainTextEdit
        self.raw_config_editor = QPlainTextEdit()
        self.raw_config_editor.setFont(__import__("PyQt6.QtGui", fromlist=["QFont"]).QFont("Courier", 9))
        self._update_raw_config()
        layout.addWidget(self.raw_config_editor)

        widget.setLayout(layout)
        return widget

    def _update_raw_config(self) -> None:
        """Update raw config display"""
        import yaml
        config_yaml = yaml.dump(self.config_manager.settings, default_flow_style=False)
        self.raw_config_editor.setPlainText(config_yaml)
        # Remember initial text to detect if user modified the raw config
        self.raw_config_initial_text = config_yaml

    def _browse_database(self) -> None:
        """Browse for database file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Database Location",
            str(Path.home() / ".w4gns_logger" / "contacts.db"),
            "SQLite Database (*.db);;All Files (*)"
        )
        if file_path:
            self.settings_widgets["database.location"].setText(file_path)

    def _browse_backup_destination(self) -> None:
        """Browse for backup destination (USB drive, external drive, etc.)"""
        backup_dest = QFileDialog.getExistingDirectory(
            self,
            "Select Backup Destination (USB Drive or External Location)",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )

        if backup_dest:
            # Save to settings
            self.config_manager.set("database.backup_destination", backup_dest)
            # Update display
            self.settings_widgets["database.backup_destination"].setText(backup_dest)
            logger.info(f"Backup destination set to: {backup_dest}")
            QMessageBox.information(
                self,
                "Backup Destination Set",
                f"Backups will be created in:\n{backup_dest}\n\n"
                f"Auto-backup on shutdown is enabled by default."
            )

    def _backup_now(self) -> None:
        """Perform manual backup to configured or user-selected location"""
        try:
            # Check if backup destination is configured
            backup_dest = self.config_manager.get("database.backup_destination", "")

            if not backup_dest:
                # No destination configured, prompt user
                backup_dest = QFileDialog.getExistingDirectory(
                    self,
                    "Select Backup Destination",
                    str(Path.home()),
                    QFileDialog.Option.ShowDirsOnly
                )

                if not backup_dest:
                    # User cancelled
                    return

            # Validate backup destination exists
            if not Path(backup_dest).exists():
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Backup destination not found: {backup_dest}\n\n"
                    f"Please select a valid location (USB drive, external drive, etc.)"
                )
                return

            # Get database path
            db_path = Path(self.config_manager.get("database.location"))
            if not db_path.exists():
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Database file not found: {db_path}"
                )
                return

            # Perform backup
            backup_manager = BackupManager()
            result = backup_manager.backup_to_location(
                database_path=db_path,
                backup_destination=Path(backup_dest)
            )

            if result["success"]:
                QMessageBox.information(
                    self,
                    "Backup Successful",
                    result["message"]
                )
                logger.info(f"Backup completed: {result['backup_dir']}")
            else:
                QMessageBox.critical(
                    self,
                    "Backup Failed",
                    result["message"]
                )
                logger.error(f"Backup failed: {result['message']}")

        except Exception as e:
            logger.error(f"Error during backup: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Backup operation failed: {str(e)}"
            )

    def _save_settings(self) -> None:
        """Save all settings"""
        try:
            # Update settings from widgets
            # Collect goals and targets separately
            goals = []
            targets = []

            for key, widget in self.settings_widgets.items():
                # Handle goals and targets specially - collect checked items into lists
                if key.startswith("skcc.goals."):
                    if isinstance(widget, QCheckBox) and widget.isChecked():
                        goal_name = key.split(".")[-1]
                        goals.append(goal_name)
                    continue
                elif key.startswith("skcc.targets."):
                    if isinstance(widget, QCheckBox) and widget.isChecked():
                        target_name = key.split(".")[-1]
                        targets.append(target_name)
                    continue

                # Handle regular settings
                if isinstance(widget, QLineEdit):
                    value = widget.text()
                elif isinstance(widget, QSpinBox):
                    value = widget.value()
                elif isinstance(widget, QDoubleSpinBox):
                    value = widget.value()
                elif isinstance(widget, QComboBox):
                    # Use currentData() if data is set, otherwise use currentText()
                    value = widget.currentData()
                    if value is None:
                        value = widget.currentText()
                elif isinstance(widget, QCheckBox):
                    value = widget.isChecked()
                else:
                    continue

                self.config_manager.set(key, value)

            # Save collected goals and targets
            self.config_manager.set("skcc.goals", goals)
            self.config_manager.set("skcc.targets", targets)

            # Only try to save raw config if it was actually modified by user
            raw_text = self.raw_config_editor.toPlainText()
            if raw_text.strip() != self.raw_config_initial_text.strip():
                # Raw config was edited - use it if valid
                try:
                    import yaml
                    parsed = yaml.safe_load(raw_text)
                    if parsed and isinstance(parsed, dict):
                        logger.info("Applying changes from raw config editor")
                        self.config_manager.settings = parsed
                    else:
                        logger.warning("Raw config is empty or invalid YAML")
                except yaml.YAMLError as e:
                    logger.error(f"Raw config contains invalid YAML: {e}")
                    raise
                except Exception as e:
                    logger.error(f"Error parsing raw config: {e}")
                    raise
            else:
                # Raw config not modified, just save widget changes
                logger.debug("Raw config unchanged, saving widget changes")

            # Save all settings to disk
            self.config_manager.save()

            # Apply theme if it was changed
            try:
                theme = self.config_manager.get("ui.theme", "light")
                app = QApplication.instance()
                if app:
                    ThemeManager.apply_theme(app, theme)
                    logger.info(f"Applied {theme} theme from settings")
            except Exception as e:
                logger.warning(f"Could not apply theme: {e}")

            QMessageBox.information(
                self,
                "Success",
                "Settings saved successfully!"
            )

            logger.info("Settings saved")

        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save settings: {str(e)}"
            )

    def _reset_defaults(self) -> None:
        """Reset all settings to defaults"""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Reset all settings to defaults? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Reset to defaults
                self.config_manager.settings = self.config_manager.DEFAULT_CONFIG.copy()
                self.config_manager.save()

                # Update UI
                self._refresh_all_widgets()

                QMessageBox.information(
                    self,
                    "Success",
                    "Settings reset to defaults"
                )

                logger.info("Settings reset to defaults")

            except Exception as e:
                logger.error(f"Failed to reset settings: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to reset settings: {str(e)}"
                )

    def _refresh_all_widgets(self) -> None:
        """Refresh all settings widgets from config"""
        for key, widget in self.settings_widgets.items():
            value = self.config_manager.get(key)

            if isinstance(widget, QLineEdit):
                widget.setText(str(value) if value else "")
            elif isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
                widget.setValue(value if value else 0)
            elif isinstance(widget, QComboBox):
                if value and widget.findText(str(value)) >= 0:
                    widget.setCurrentText(str(value))
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))

        self._update_raw_config()
