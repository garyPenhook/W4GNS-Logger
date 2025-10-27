"""
Contact Logging Form

PyQt6 form for logging new QSO (contact) entries with dropdown support for
band, mode, frequency, country, and state selection.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QPushButton, QMessageBox, QDateTimeEdit, QGroupBox, QCheckBox
)
from PyQt6.QtCore import Qt, QDateTime, QTimer, pyqtSignal

from src.database.models import Contact
from src.database.repository import DatabaseRepository
from src.database.skcc_membership import SKCCMembershipManager
from src.ui.dropdown_data import DropdownData
from src.ui.field_manager import FieldManager
from src.ui.resizable_field import ResizableFieldRow
from src.qrz import get_qrz_service
from src.config.settings import get_config_manager
from src.utils.timezone_utils import (
    get_utc_now, datetime_to_adif_date, datetime_to_adif_time,
    format_utc_time_for_display
)

logger = logging.getLogger(__name__)


class CallsignLineEdit(QLineEdit):
    """Custom QLineEdit for callsign input that detects when user tabs away"""

    # Signal emitted when focus is lost
    focus_lost = pyqtSignal()

    def focusOutEvent(self, event):
        """Called when focus is lost from this field"""
        self.focus_lost.emit()
        super().focusOutEvent(event)


class LoggingForm(QWidget):
    """Contact logging form with dropdown menus"""

    # Signal for thread-safe QRZ data updates
    qrz_data_ready = pyqtSignal(object)  # Emits CallsignInfo object

    def __init__(self, db: DatabaseRepository, parent: Optional[QWidget] = None):
        """
        Initialize logging form

        Args:
            db: Database repository instance
            parent: Parent widget

        Raises:
            TypeError: If db is not a DatabaseRepository instance
        """
        try:
            super().__init__(parent)

            # Validate database
            if db is None:
                raise TypeError("db cannot be None")
            if not isinstance(db, DatabaseRepository):
                raise TypeError(f"db must be DatabaseRepository, got {type(db).__name__}")

            self.db = db
            self.dropdown_data = DropdownData()
            self.config_manager = get_config_manager()
            self.qrz_service = get_qrz_service()
            self.skcc_membership = SKCCMembershipManager(self.config_manager.get('database.location'))

            # QSO timing tracking
            self.qso_start_time: Optional[datetime] = None
            self.qso_end_time: Optional[datetime] = None
            self.last_callsign = ""  # Track last callsign for 5-second stable detection

            # Always-running clock timer (updates every 500ms)
            self.clock_timer = QTimer()
            self.clock_timer.timeout.connect(self._update_clock)
            self.clock_timer.start(500)  # Update 2x per second for smooth display
            logger.debug("Always-running clock timer started")

            # Track if user is editing datetime to avoid overwriting their input
            self.datetime_input_focus = False

            # Callsign stability timer (detects when callsign stable for 5 seconds)
            self.callsign_stable_timer = QTimer()  # Timer for detecting stable callsign
            self.callsign_stable_timer.timeout.connect(self._on_callsign_stable)
            self.callsign_stable_timer.setSingleShot(True)

            # Connect QRZ data signal to populate method for thread-safe UI updates
            self.qrz_data_ready.connect(self._populate_from_qrz_info)

            # Store minimum widths for resizing
            self.min_widths = {
                'callsign': 80,
                'datetime': 69,  # 15% wider for better time field visibility
                'band': 56,  # 30% narrower (was 80, now 56)
                'mode': 70,  # 30% narrower (was 100, now 70)
                'frequency': 77,  # 10% wider (was 70, now 77)
                'country': 84,  # 30% narrower (was 120, now 84)
                'state': 56,  # 30% narrower (was 80, now 56)
                'grid': 73,  # Grid square field width
                'qth': 96,  # QTH field width
                'rst_sent': 50,
                'rst_rcvd': 50,
                'operator': 100,
                'skcc_number': 60  # SKCC number field
            }

            self._init_ui()
            logger.info("LoggingForm initialized successfully")

        except (TypeError, Exception) as e:
            logger.error(f"Error initializing LoggingForm: {e}", exc_info=True)
            raise

    def _init_ui(self) -> None:
        """Initialize UI components with compact grid layout"""
        try:
            main_layout = QVBoxLayout()
            main_layout.setContentsMargins(5, 5, 5, 5)
            main_layout.setSpacing(2)

            # Create compact grid form
            try:
                compact_section = self._create_compact_grid_section()
                logger.debug("Compact grid section created")
            except Exception as e:
                logger.error(f"Error creating compact grid section: {e}", exc_info=True)
                raise

            try:
                buttons_section = self._create_buttons_section()
                logger.debug("Buttons section created")
            except Exception as e:
                logger.error(f"Error creating buttons section: {e}", exc_info=True)
                raise

            # Add sections to main layout
            main_layout.addWidget(compact_section)
            main_layout.addLayout(buttons_section)
            main_layout.addStretch()

            self.setLayout(main_layout)
            logger.debug("UI initialization complete")

        except Exception as e:
            logger.error(f"Error initializing UI: {e}", exc_info=True)
            raise

    def _create_compact_grid_section(self) -> QGroupBox:
        """Create compact grid layout with larger labels and fields spread horizontally"""
        group = QGroupBox("")
        group.setStyleSheet("QGroupBox { border: none; padding: 0px; }")
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(12)

        # Helper to create larger labels (15% larger)
        def create_label(text: str) -> QLabel:
            label = QLabel(text)
            font = label.font()
            font.setPointSize(int(font.pointSize() * 1.15))
            font.setBold(True)
            label.setFont(font)
            return label

        # ROW 1: Callsign, RST Sent, RST Received, Date/Time
        row1 = QHBoxLayout()
        row1.setSpacing(15)

        # Callsign with QRZ lookup button
        callsign_row = QHBoxLayout()
        callsign_row.setSpacing(5)

        self.callsign_input = CallsignLineEdit()
        self.callsign_input.setPlaceholderText("Callsign")
        self.callsign_input.textChanged.connect(self._on_callsign_changed)
        # Trigger QRZ lookup when user tabs away from callsign field
        self.callsign_input.focus_lost.connect(self._on_callsign_focus_lost)
        font = self.callsign_input.font()
        font.setPointSize(int(font.pointSize() * 1.15))
        self.callsign_input.setFont(font)
        self.callsign_input.setMinimumHeight(35)
        self.callsign_input.setMaximumWidth(70)  # Reduced by 80%
        callsign_row.addWidget(self.callsign_input, 0)

        # QRZ Lookup button (only show if QRZ is enabled)
        if self.config_manager.get("qrz.enabled", False):
            self.qrz_lookup_btn = QPushButton("QRZ↻")
            self.qrz_lookup_btn.setMaximumWidth(60)  # Increased by 20%
            self.qrz_lookup_btn.setMinimumHeight(35)
            self.qrz_lookup_btn.clicked.connect(self._fetch_qrz_callsign)
            self.qrz_lookup_btn.setToolTip("Fetch callsign info from QRZ.com")
            callsign_row.addWidget(self.qrz_lookup_btn)

        row1.addWidget(create_label("Call:"))
        row1.addLayout(callsign_row, 0)

        # RST Sent (3-digit RST code: 111-599)
        self.rst_sent_input = QSpinBox()
        self.rst_sent_input.setRange(111, 599)
        self.rst_sent_input.setValue(599)  # Default: 5=readability, 9=strength, 9=tone
        font = self.rst_sent_input.font()
        font.setPointSize(int(font.pointSize() * 1.15))
        self.rst_sent_input.setFont(font)
        self.rst_sent_input.setMinimumHeight(35)
        self.rst_sent_input.setMaximumWidth(60)
        self.rst_sent_input.setToolTip("RST Sent: 3-digit code (e.g., 599 = 5,9,9)")
        row1.addWidget(create_label("Sent:"))
        row1.addWidget(self.rst_sent_input, 0)

        # RST Received (3-digit RST code: 111-599)
        self.rst_rcvd_input = QSpinBox()
        self.rst_rcvd_input.setRange(111, 599)
        self.rst_rcvd_input.setValue(599)  # Default: 5=readability, 9=strength, 9=tone
        font = self.rst_rcvd_input.font()
        font.setPointSize(int(font.pointSize() * 1.15))
        self.rst_rcvd_input.setFont(font)
        self.rst_rcvd_input.setMinimumHeight(35)
        self.rst_rcvd_input.setMaximumWidth(60)
        self.rst_rcvd_input.setToolTip("RST Received: 3-digit code (e.g., 599 = 5,9,9)")
        row1.addWidget(create_label("Rcvd:"))
        row1.addWidget(self.rst_rcvd_input, 0)

        # Date/Time (UTC - ALL LOGGING IS IN UTC)
        self.datetime_input = QDateTimeEdit()
        # Convert UTC to QDateTime
        utc_now = get_utc_now()
        q_datetime = QDateTime.fromSecsSinceEpoch(int(utc_now.timestamp()))
        self.datetime_input.setDateTime(q_datetime)
        self.datetime_input.setDisplayFormat("MM-dd hh:mm (UTC)")  # Show UTC indicator
        self.datetime_input.focusInEvent = lambda event: self._on_datetime_focus_in()
        self.datetime_input.focusOutEvent = lambda event: self._on_datetime_focus_out()
        font = self.datetime_input.font()
        font.setPointSize(int(font.pointSize() * 1.15))
        self.datetime_input.setFont(font)
        self.datetime_input.setMinimumHeight(35)
        self.datetime_input.setMaximumWidth(60)  # 50% narrower, visible
        row1.addWidget(create_label("Time:"))
        row1.addWidget(self.datetime_input, 0)

        row1.addStretch()  # Absorb extra space, prevents other fields from expanding

        main_layout.addLayout(row1)

        # ROW 2: Band, Mode, Frequency, Country, State
        row2 = QHBoxLayout()
        row2.setSpacing(15)

        # Band
        self.band_combo = QComboBox()
        self.band_combo.addItems(self.dropdown_data.get_bands())
        self.band_combo.currentTextChanged.connect(self._on_band_changed)
        font = self.band_combo.font()
        font.setPointSize(int(font.pointSize() * 1.15))
        self.band_combo.setFont(font)
        self.band_combo.setMinimumHeight(35)
        self.band_combo.setMaximumWidth(56)  # 30% narrower
        row2.addWidget(create_label("Band:"))
        row2.addWidget(self.band_combo, 0)

        # Mode
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(self.dropdown_data.get_modes())
        # Set default mode to CW
        cw_index = self.mode_combo.findText("CW")
        if cw_index >= 0:
            self.mode_combo.setCurrentIndex(cw_index)
        font = self.mode_combo.font()
        font.setPointSize(int(font.pointSize() * 1.15))
        self.mode_combo.setFont(font)
        self.mode_combo.setMinimumHeight(35)
        self.mode_combo.setMaximumWidth(70)  # 30% narrower
        row2.addWidget(create_label("Mode:"))
        row2.addWidget(self.mode_combo, 0)

        # Frequency
        self.frequency_input = QDoubleSpinBox()
        self.frequency_input.setRange(0.1, 10000.0)
        self.frequency_input.setDecimals(5)  # 5 decimal places for accurate frequency (e.g., 14.05500 MHz)
        self.frequency_input.setSingleStep(0.001)  # Step by 1 kHz increments
        font = self.frequency_input.font()
        font.setPointSize(int(font.pointSize() * 1.15))
        self.frequency_input.setFont(font)
        self.frequency_input.setMinimumHeight(35)
        self.frequency_input.setMaximumWidth(77)  # 10% wider
        row2.addWidget(create_label("Freq:"))
        row2.addWidget(self.frequency_input, 0)

        # Country
        self.country_combo = QComboBox()
        self.country_combo.addItems([""] + self.dropdown_data.get_countries())
        self.country_combo.currentTextChanged.connect(self._on_country_changed)
        font = self.country_combo.font()
        font.setPointSize(int(font.pointSize() * 1.15))
        self.country_combo.setFont(font)
        self.country_combo.setMinimumHeight(35)
        self.country_combo.setMaximumWidth(84)  # 30% narrower
        row2.addWidget(create_label("Country:"))
        row2.addWidget(self.country_combo, 0)

        # State
        self.state_combo = QComboBox()
        self.state_combo.addItems([""] + self.dropdown_data.get_us_states())
        self.state_combo.setEnabled(False)
        font = self.state_combo.font()
        font.setPointSize(int(font.pointSize() * 1.15))
        self.state_combo.setFont(font)
        self.state_combo.setMinimumHeight(35)
        self.state_combo.setMaximumWidth(56)  # 30% narrower
        row2.addWidget(create_label("State:"))
        row2.addWidget(self.state_combo, 0)

        row2.addStretch()

        main_layout.addLayout(row2)

        # ROW 3: Grid, QTH, TX Power, RX Power, SKCC
        row3 = QHBoxLayout()
        row3.setSpacing(15)

        # Grid Square
        self.grid_input = QLineEdit()
        self.grid_input.setPlaceholderText("Grid")
        font = self.grid_input.font()
        font.setPointSize(int(font.pointSize() * 1.15))
        self.grid_input.setFont(font)
        self.grid_input.setMinimumHeight(35)
        self.grid_input.setMaximumWidth(73)  # Grid square field width (increased by 10%)
        row3.addWidget(create_label("Grid:"))
        row3.addWidget(self.grid_input, 0)

        # QTH
        self.qth_input = QLineEdit()
        self.qth_input.setPlaceholderText("City")
        font = self.qth_input.font()
        font.setPointSize(int(font.pointSize() * 1.15))
        self.qth_input.setFont(font)
        self.qth_input.setMinimumHeight(35)
        self.qth_input.setMaximumWidth(96)  # QTH field width
        row3.addWidget(create_label("QTH:"))
        row3.addWidget(self.qth_input, 0)

        # SKCC Number
        self.skcc_number_input = QLineEdit()
        self.skcc_number_input.setPlaceholderText("SKCC#")
        self.skcc_number_input.setMaxLength(20)
        font = self.skcc_number_input.font()
        font.setPointSize(int(font.pointSize() * 1.15))
        self.skcc_number_input.setFont(font)
        self.skcc_number_input.setMinimumHeight(35)
        self.skcc_number_input.setMaximumWidth(60)  # SKCC number field (prevent over-expansion)
        row3.addWidget(create_label("SKCC:"))
        row3.addWidget(self.skcc_number_input, 0)

        # Add stretch to prevent Grid/QTH width changes from affecting other fields
        row3.addStretch()

        main_layout.addLayout(row3)

        # ROW 4: Key Type, Operator Name
        row4 = QHBoxLayout()
        row4.setSpacing(15)

        # Key Type
        self.key_type_combo = QComboBox()
        self.key_type_combo.addItems(["STRAIGHT", "BUG", "SIDESWIPER", "NONE"])
        self.key_type_combo.setMaximumWidth(49)
        font = self.key_type_combo.font()
        font.setPointSize(int(font.pointSize() * 1.15))
        self.key_type_combo.setFont(font)
        self.key_type_combo.setMinimumHeight(35)
        row4.addWidget(create_label("Key Type:"))
        row4.addWidget(self.key_type_combo, 0)
        row4.addSpacing(10)

        # Paddle
        self.paddle_combo = QComboBox()
        self.paddle_combo.addItems(["", "ELECTRONIC", "SEMI-AUTO", "IAMBIC", "MECHANICAL"])
        self.paddle_combo.setMaximumWidth(90)
        font = self.paddle_combo.font()
        font.setPointSize(int(font.pointSize() * 1.15))
        self.paddle_combo.setFont(font)
        self.paddle_combo.setMinimumHeight(35)
        row4.addWidget(create_label("Paddle:"))
        row4.addWidget(self.paddle_combo, 0)
        row4.addSpacing(10)

        # Operator Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Operator name")
        self.name_input.setMaximumWidth(130)
        self.name_input.setMinimumHeight(35)
        # Keep normal font size (not enlarged)
        row4.addWidget(create_label("Name:"))
        row4.addWidget(self.name_input, 0)
        row4.addSpacing(10)

        # County
        self.county_input = QLineEdit()
        self.county_input.setPlaceholderText("County")
        self.county_input.setMaximumWidth(80)
        font = self.county_input.font()
        font.setPointSize(int(font.pointSize() * 1.15))
        self.county_input.setFont(font)
        self.county_input.setMinimumHeight(35)
        row4.addWidget(create_label("County:"))
        row4.addWidget(self.county_input, 0)
        row4.addSpacing(10)

        # QRP Checkbox
        self.qrp_checkbox = QCheckBox("QRP")
        self.qrp_checkbox.setMinimumHeight(35)
        self.qrp_checkbox.setToolTip("Check if this is a QRP contact (≤5 watts)")
        font = self.qrp_checkbox.font()
        font.setPointSize(int(font.pointSize() * 1.15))
        self.qrp_checkbox.setFont(font)
        row4.addWidget(self.qrp_checkbox, 0)
        row4.addSpacing(10)

        # Power (Watts)
        self.power_input = QSpinBox()
        self.power_input.setRange(0, 1000)
        self.power_input.setValue(0)
        self.power_input.setSuffix(" W")
        self.power_input.setMaximumWidth(90)
        self.power_input.setMinimumHeight(35)
        self.power_input.setToolTip("Transmit power in watts")
        font = self.power_input.font()
        font.setPointSize(int(font.pointSize() * 1.15))
        self.power_input.setFont(font)
        row4.addWidget(create_label("Power:"))
        row4.addWidget(self.power_input, 0)

        row4.addStretch()

        main_layout.addLayout(row4)

        group.setLayout(main_layout)
        return group

    def _create_basic_section(self) -> QGroupBox:
        """Create basic QSO information section"""
        group = QGroupBox("Basic QSO Information")
        layout = QVBoxLayout()
        layout.setSpacing(3)

        # Callsign
        self.callsign_input = QLineEdit()
        self.callsign_input.setPlaceholderText("Enter remote station callsign")
        self.callsign_input.setMaximumWidth(150)
        self.callsign_input.textChanged.connect(self._on_callsign_changed)
        callsign_row = ResizableFieldRow("Callsign:", self.callsign_input)
        layout.addWidget(callsign_row)

        # Date/Time (with always-running clock)
        self.datetime_input = QDateTimeEdit()
        self.datetime_input.setDateTime(QDateTime.currentDateTime())
        self.datetime_input.setDisplayFormat("yyyy-MM-dd hh:mm")
        self.datetime_input.setMaximumWidth(180)
        # Track focus to avoid overwriting user input
        self.datetime_input.focusInEvent = lambda event: self._on_datetime_focus_in()
        self.datetime_input.focusOutEvent = lambda event: self._on_datetime_focus_out()
        datetime_row = ResizableFieldRow("Date & Time:", self.datetime_input)
        layout.addWidget(datetime_row)

        # Band dropdown
        self.band_combo = QComboBox()
        self.band_combo.addItems(self.dropdown_data.get_bands())
        self.band_combo.currentTextChanged.connect(self._on_band_changed)
        self.band_combo.setMaximumWidth(80)
        band_row = ResizableFieldRow("Band:", self.band_combo)
        layout.addWidget(band_row)

        # Mode dropdown
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(self.dropdown_data.get_modes())
        self.mode_combo.setMaximumWidth(100)
        mode_row = ResizableFieldRow("Mode:", self.mode_combo)
        layout.addWidget(mode_row)

        group.setLayout(layout)
        return group

    def _create_frequency_section(self) -> QGroupBox:
        """Create frequency information section"""
        group = QGroupBox("Frequency")
        layout = QVBoxLayout()
        layout.setSpacing(3)

        # Frequency input with button
        freq_container = QWidget()
        freq_layout = QHBoxLayout()
        freq_layout.setContentsMargins(0, 0, 0, 0)
        freq_layout.setSpacing(2)

        self.frequency_input = QDoubleSpinBox()
        self.frequency_input.setRange(0.1, 10000.0)
        self.frequency_input.setDecimals(5)  # 5 decimal places for accurate frequency (e.g., 14.05500 MHz)
        self.frequency_input.setSingleStep(0.001)  # Step by 1 kHz increments
        self.frequency_input.setMaximumWidth(140)  # Increased for 5 decimal display
        freq_layout.addWidget(self.frequency_input)

        # Auto-frequency button
        auto_freq_btn = QPushButton("Auto Fill")
        auto_freq_btn.clicked.connect(self._auto_fill_frequency)
        freq_layout.addWidget(auto_freq_btn)
        freq_layout.addStretch()
        freq_container.setLayout(freq_layout)

        freq_row = ResizableFieldRow("Frequency (MHz):", freq_container)
        layout.addWidget(freq_row)
        group.setLayout(layout)
        return group

    def _create_location_section(self) -> QGroupBox:
        """Create location information section"""
        group = QGroupBox("Location")
        layout = QVBoxLayout()
        layout.setSpacing(3)

        # Country dropdown
        self.country_combo = QComboBox()
        self.country_combo.addItems([""] + self.dropdown_data.get_countries())
        self.country_combo.currentTextChanged.connect(self._on_country_changed)
        self.country_combo.setMaximumWidth(120)
        self.country_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        country_row = ResizableFieldRow("Country:", self.country_combo)
        layout.addWidget(country_row)

        # State dropdown (initially disabled)
        self.state_combo = QComboBox()
        self.state_combo.addItems([""] + self.dropdown_data.get_us_states())
        self.state_combo.setEnabled(False)
        self.state_combo.setMaximumWidth(80)
        state_row = ResizableFieldRow("State:", self.state_combo)
        layout.addWidget(state_row)

        # Grid square
        self.grid_input = QLineEdit()
        self.grid_input.setPlaceholderText("e.g., EM87ui")
        self.grid_input.setMaximumWidth(73)  # Grid square field width (increased by 10%)
        grid_row = ResizableFieldRow("Grid Square:", self.grid_input)
        layout.addWidget(grid_row)

        # QTH
        self.qth_input = QLineEdit()
        self.qth_input.setPlaceholderText("City/Location")
        self.qth_input.setMaximumWidth(96)  # QTH field width (increased by 20%)
        qth_row = ResizableFieldRow("QTH:", self.qth_input)
        layout.addWidget(qth_row)

        group.setLayout(layout)
        return group

    def _create_signal_section(self) -> QGroupBox:
        """Create signal report section"""
        group = QGroupBox("Signal Reports & Power")
        layout = QVBoxLayout()
        layout.setSpacing(3)

        # RST Sent
        self.rst_sent_input = QLineEdit()
        self.rst_sent_input.setPlaceholderText("e.g., 59")
        self.rst_sent_input.setMaxLength(3)
        self.rst_sent_input.setMaximumWidth(60)
        rst_sent_row = ResizableFieldRow("RST Sent:", self.rst_sent_input)
        layout.addWidget(rst_sent_row)

        # RST Received
        self.rst_rcvd_input = QLineEdit()
        self.rst_rcvd_input.setPlaceholderText("e.g., 59")
        self.rst_rcvd_input.setMaxLength(3)
        self.rst_rcvd_input.setMaximumWidth(60)
        rst_rcvd_row = ResizableFieldRow("RST Received:", self.rst_rcvd_input)
        layout.addWidget(rst_rcvd_row)

        # SKCC Number
        self.skcc_number_input = QLineEdit()
        self.skcc_number_input.setPlaceholderText("e.g., 12345")
        self.skcc_number_input.setMaxLength(20)
        self.skcc_number_input.setMaximumWidth(60)  # SKCC number field (prevent over-expansion)
        self.skcc_number_input.setToolTip("Straight Key Century Club member number")
        skcc_row = ResizableFieldRow("SKCC Number:", self.skcc_number_input)
        layout.addWidget(skcc_row)

        # Key Type
        self.key_type_combo = QComboBox()
        self.key_type_combo.addItems(["STRAIGHT", "BUG", "SIDESWIPER", "NONE"])
        self.key_type_combo.setMaximumWidth(30)
        self.key_type_combo.setToolTip("Type of mechanical key used (for Triple Key Award, or NONE if paddle used)")
        key_type_row = ResizableFieldRow("Key Type:", self.key_type_combo)
        layout.addWidget(key_type_row)

        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Remote operator name")
        self.name_input.setMaximumWidth(35)
        name_row = ResizableFieldRow("Operator Name:", self.name_input)
        layout.addWidget(name_row)

        # County
        self.county_input = QLineEdit()
        self.county_input.setPlaceholderText("County")
        self.county_input.setMaximumWidth(150)
        county_row = ResizableFieldRow("County:", self.county_input)
        layout.addWidget(county_row)

        group.setLayout(layout)
        return group

    def _create_buttons_section(self) -> QHBoxLayout:
        """Create action buttons section"""
        layout = QHBoxLayout()
        layout.addStretch()

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_form)
        layout.addWidget(clear_btn)

        # Save button
        save_btn = QPushButton("Save Contact")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        save_btn.clicked.connect(self.save_contact)
        layout.addWidget(save_btn)

        return layout

    def _on_band_changed(self, band: str) -> None:
        """Handle band selection change"""
        if band:
            center_freq = self.dropdown_data.get_band_center_frequency(band)
            self.frequency_input.setValue(center_freq)
            logger.debug(f"Band changed to {band}, frequency set to {center_freq} MHz")

    def _on_country_changed(self, country: str) -> None:
        """Handle country selection change"""
        # Enable state dropdown only for United States
        is_us = country == "United States"
        self.state_combo.setEnabled(is_us)
        if not is_us:
            self.state_combo.setCurrentIndex(0)

    def _auto_fill_frequency(self) -> None:
        """Auto-fill frequency from band selection"""
        band = self.band_combo.currentText()
        if band:
            center_freq = self.dropdown_data.get_band_center_frequency(band)
            self.frequency_input.setValue(center_freq)
            logger.debug(f"Auto-filled frequency: {center_freq} MHz for band {band}")

    def _validate_form(self) -> bool:
        """Validate form inputs"""
        errors = []

        # Required fields
        if not self.callsign_input.text().strip():
            errors.append("Callsign is required")

        if not self.band_combo.currentText():
            errors.append("Band is required")

        if not self.mode_combo.currentText():
            errors.append("Mode is required")

        if self.frequency_input.value() <= 0:
            errors.append("Frequency must be greater than 0")

        # RST Sent/Received are validated by spinbox range (111-599), no manual validation needed

        if errors:
            QMessageBox.warning(self, "Validation Error", "\n".join(errors))
            return False

        return True

    @staticmethod
    def _is_valid_rst(rst: str) -> bool:
        """Check if RST string is valid"""
        return rst.isdigit() and 1 <= len(rst) <= 3

    def save_contact(self) -> None:
        """
        Save contact to database

        Handles all validation, parsing, and database operations with comprehensive
        error handling and user feedback.
        """
        try:
            # Validate form first
            if not self._validate_form():
                logger.debug("Form validation failed, save cancelled")
                return

            logger.debug("Form validation passed, proceeding with save")

            try:
                # Parse datetime (MUST BE IN UTC)
                datetime_edit = self.datetime_input.dateTime()
                if datetime_edit is None:
                    raise ValueError("Invalid datetime value")

                # QDateTime.toPython() returns naive datetime
                # QDateTime stores as local system time, so we need to interpret it as UTC
                qso_datetime = datetime_edit.toPython()
                if qso_datetime is None:
                    raise ValueError("Failed to convert QDateTime to Python datetime")

                # Make datetime UTC-aware
                # Since we're using QDateTime.fromSecsSinceEpoch (which is UTC),
                # the toPython() result should be treated as UTC
                if qso_datetime.tzinfo is None:
                    qso_datetime = qso_datetime.replace(tzinfo=timezone.utc)

                # Convert to ADIF format (YYYYMMDD and HHMM)
                qso_date = datetime_to_adif_date(qso_datetime)

                # Get QSO start time (time_on) and end time (time_off)
                time_on, time_off = self._get_qso_times()
                logger.debug(f"Parsed UTC datetime: {qso_date} {time_on} UTC | QSO: {time_on}-{time_off}")

            except Exception as e:
                logger.error(f"Error parsing datetime: {e}", exc_info=True)
                raise ValueError(f"Failed to parse date/time: {str(e)}")

            try:
                # Create contact object
                callsign = self.callsign_input.text().strip().upper()
                if not callsign:
                    raise ValueError("Callsign is empty after stripping")

                contact = Contact(
                    callsign=callsign,
                    qso_date=qso_date,
                    time_on=time_on,
                    time_off=time_off,
                    band=self.band_combo.currentText(),
                    mode=self.mode_combo.currentText(),
                    frequency=self.frequency_input.value(),
                    country=self.country_combo.currentText() if self.country_combo.currentText() else None,
                    state=self.state_combo.currentText() if self.state_combo.currentText() else None,
                    county=self.county_input.text().strip() if self.county_input.text().strip() else None,
                    gridsquare=self.grid_input.text().strip() if self.grid_input.text().strip() else None,
                    qth=self.qth_input.text().strip() if self.qth_input.text().strip() else None,
                    rst_sent=str(self.rst_sent_input.value()),
                    rst_rcvd=str(self.rst_rcvd_input.value()),
                    skcc_number=self.skcc_number_input.text().strip() if self.skcc_number_input.text().strip() else None,
                    key_type=self.key_type_combo.currentText(),
                    paddle=self.paddle_combo.currentText() if self.paddle_combo.currentText().strip() else None,
                    name=self.name_input.text().strip() if self.name_input.text().strip() else None,
                    tx_power=self.power_input.value() if self.power_input.value() > 0 else None,
                )
                logger.debug(f"Contact object created: {callsign}")

            except Exception as e:
                logger.error(f"Error creating contact object: {e}", exc_info=True)
                raise ValueError(f"Failed to create contact: {str(e)}")

            try:
                # Save to database
                if self.db is None:
                    raise RuntimeError("Database connection is None")

                self.db.add_contact(contact)
                logger.info(f"Contact saved successfully: {contact.callsign} on {contact.band} {contact.mode}")

            except Exception as e:
                logger.error(f"Error saving to database: {e}", exc_info=True)
                raise RuntimeError(f"Database error: {str(e)}")

            # Auto-upload to QRZ if enabled
            if self.config_manager.get("qrz.auto_upload", False):
                try:
                    # Convert frequency to MHz if needed
                    freq_mhz = contact.frequency
                    if freq_mhz and freq_mhz > 0:
                        # Ensure frequency is in MHz
                        if freq_mhz > 30000:  # If in Hz
                            freq_mhz = freq_mhz / 1_000_000
                        elif freq_mhz > 300:  # If in kHz
                            freq_mhz = freq_mhz / 1000

                        # Upload asynchronously
                        self.qrz_service.upload_qso_async(
                            callsign=contact.callsign,
                            qso_date=contact.qso_date,
                            time_on=contact.time_on,
                            freq=freq_mhz,
                            mode=contact.mode,
                            rst_sent=contact.rst_sent or "59",
                            rst_rcvd=contact.rst_rcvd or "59",
                            tx_power=contact.tx_power,
                            notes=f"Key Type: {contact.key_type}" if contact.key_type else None
                        )
                        logger.debug(f"Queued QSO for upload to QRZ: {contact.callsign}")
                except Exception as e:
                    logger.warning(f"Failed to queue QRZ upload: {e}")
                    # Don't fail contact save if QRZ upload fails

            # Show success message
            QMessageBox.information(
                self,
                "Success",
                f"Contact with {contact.callsign} saved successfully!"
            )

            # Clear form
            self.clear_form()

        except Exception as e:
            logger.error(f"Error in save_contact: {str(e)}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save contact: {str(e)}"
            )

    def clear_form(self) -> None:
        """
        Clear all form fields

        Resets all inputs to default/empty state and sets focus to callsign field.
        ALL TIMES ARE IN UTC.
        """
        try:
            self.callsign_input.clear()
            # Set datetime to current UTC time
            utc_now = get_utc_now()
            q_datetime = QDateTime.fromSecsSinceEpoch(int(utc_now.timestamp()))
            self.datetime_input.setDateTime(q_datetime)
            self.band_combo.setCurrentIndex(0)
            self.mode_combo.setCurrentIndex(0)
            self.frequency_input.setValue(0.0)
            self.country_combo.setCurrentIndex(0)
            self.state_combo.setCurrentIndex(0)
            self.grid_input.clear()
            self.qth_input.clear()
            self.rst_sent_input.setValue(599)  # Reset to 599 (5,9,9)
            self.rst_rcvd_input.setValue(599)  # Reset to 599 (5,9,9)
            self.skcc_number_input.clear()
            self.key_type_combo.setCurrentIndex(0)  # Reset to STRAIGHT
            self.paddle_combo.setCurrentIndex(0)  # Reset to empty
            self.name_input.clear()
            self.county_input.clear()
            self.qrp_checkbox.setChecked(False)
            self.power_input.setValue(0)

            # Reset QSO timing
            self.qso_start_time = None
            self.qso_end_time = None
            self.last_callsign = ""
            self.callsign_stable_timer.stop()

            self.callsign_input.setFocus()
            logger.debug("Form cleared successfully - QSO timing reset, UTC time restored")
        except Exception as e:
            logger.error(f"Error clearing form: {e}", exc_info=True)
            raise

    def set_field_width(self, field_name: str, width: int) -> None:
        """
        Set width of a form field by name

        Args:
            field_name: 'callsign', 'datetime', 'band', 'mode', 'frequency',
                       'country', 'state', 'grid', 'qth', 'rst_sent',
                       'rst_rcvd', or 'operator'
            width: Width in pixels (minimum enforced)

        Raises:
            TypeError: If field_name is not a string or width is not an integer
            ValueError: If field_name is not recognized
        """
        try:
            # Validate inputs
            if not isinstance(field_name, str):
                raise TypeError(f"field_name must be str, got {type(field_name).__name__}")
            if not isinstance(width, int):
                raise TypeError(f"width must be int, got {type(width).__name__}")
            if not field_name.strip():
                raise ValueError("field_name cannot be empty")

            # Enforce minimum width
            min_width = self.min_widths.get(field_name, 50)
            if min_width is None:
                raise ValueError(f"Unknown field_name: {field_name}")
            width = max(width, min_width)

            try:
                if field_name == 'callsign':
                    self.callsign_input.setMaximumWidth(width)
                elif field_name == 'datetime':
                    self.datetime_input.setMaximumWidth(width)
                elif field_name == 'band':
                    self.band_combo.setMaximumWidth(width)
                elif field_name == 'mode':
                    self.mode_combo.setMaximumWidth(width)
                elif field_name == 'frequency':
                    self.frequency_input.setMaximumWidth(width)
                elif field_name == 'country':
                    self.country_combo.setMaximumWidth(width)
                elif field_name == 'state':
                    self.state_combo.setMaximumWidth(width)
                elif field_name == 'grid':
                    self.grid_input.setMaximumWidth(width)
                elif field_name == 'qth':
                    self.qth_input.setMaximumWidth(width)
                elif field_name == 'rst_sent':
                    self.rst_sent_input.setMaximumWidth(width)
                elif field_name == 'rst_rcvd':
                    self.rst_rcvd_input.setMaximumWidth(width)
                elif field_name == 'operator':
                    self.name_input.setMaximumWidth(width)
                else:
                    raise ValueError(f"Unknown field_name: {field_name}")

                logger.debug(f"Set {field_name} field width to {width}px")

            except Exception as e:
                logger.error(f"Error setting field width for {field_name}: {e}", exc_info=True)
                raise

        except (TypeError, ValueError) as e:
            logger.error(f"Error in set_field_width: {e}", exc_info=True)
            raise

    def set_dropdown_width(self, dropdown_name: str, width: int) -> None:
        """
        DEPRECATED: Use set_field_width() instead
        Set width of a dropdown by name

        Args:
            dropdown_name: 'band', 'mode', 'country', or 'state'
            width: Width in pixels (minimum enforced)
        """
        self.set_field_width(dropdown_name, width)

    def get_field_width(self, field_name: str) -> int:
        """
        Get current width of a form field

        Args:
            field_name: 'callsign', 'datetime', 'band', 'mode', 'frequency',
                       'country', 'state', 'grid', 'qth', 'rst_sent',
                       'rst_rcvd', or 'operator'

        Returns:
            Width in pixels
        """
        if field_name == 'callsign':
            return self.callsign_input.width()
        elif field_name == 'datetime':
            return self.datetime_input.width()
        elif field_name == 'band':
            return self.band_combo.width()
        elif field_name == 'mode':
            return self.mode_combo.width()
        elif field_name == 'frequency':
            return self.frequency_input.width()
        elif field_name == 'country':
            return self.country_combo.width()
        elif field_name == 'state':
            return self.state_combo.width()
        elif field_name == 'grid':
            return self.grid_input.width()
        elif field_name == 'qth':
            return self.qth_input.width()
        elif field_name == 'rst_sent':
            return self.rst_sent_input.width()
        elif field_name == 'rst_rcvd':
            return self.rst_rcvd_input.width()
        elif field_name == 'operator':
            return self.name_input.width()
        return 0

    def get_dropdown_width(self, dropdown_name: str) -> int:
        """
        DEPRECATED: Use get_field_width() instead
        Get current width of a dropdown

        Args:
            dropdown_name: 'band', 'mode', 'country', or 'state'

        Returns:
            Width in pixels
        """
        return self.get_field_width(dropdown_name)

    def reset_field_widths(self) -> None:
        """Reset all form field widths to defaults"""
        for field_name in self.min_widths.keys():
            self.set_field_width(field_name, self.min_widths[field_name])
        logger.debug("Reset all form field widths to defaults")

    def reset_dropdown_widths(self) -> None:
        """DEPRECATED: Use reset_field_widths() instead"""
        self.reset_field_widths()

    # ==================== Clock Display Methods ====================

    def _on_datetime_focus_in(self) -> None:
        """Called when user clicks on datetime field to edit it"""
        self.datetime_input_focus = True
        logger.debug("DateTime field focus in - stopping clock updates")

    def _on_datetime_focus_out(self) -> None:
        """Called when user leaves datetime field"""
        self.datetime_input_focus = False
        logger.debug("DateTime field focus out - resuming clock updates")

    def _update_clock(self) -> None:
        """
        Update datetime display to show current UTC time (always-running clock)

        Called by clock_timer every 500ms to keep datetime display current.
        Respects user focus - stops updating when user is actively editing the time.
        ALL TIMES ARE IN UTC.
        """
        try:
            # Only update if user is not actively editing the datetime field
            if not self.datetime_input_focus:
                # Use UTC time, not local time
                utc_now = get_utc_now()
                q_datetime = QDateTime.fromSecsSinceEpoch(int(utc_now.timestamp()))
                self.datetime_input.setDateTime(q_datetime)
        except Exception as e:
            logger.error(f"Error updating clock: {e}", exc_info=True)

    # ==================== QSO Timing Methods ====================

    def _on_callsign_changed(self, text: str) -> None:
        """
        Handle callsign input changes

        When callsign is entered and remains stable for 5 seconds,
        record the QSO start time.

        Args:
            text: Current callsign input text
        """
        # Stop existing timer
        self.callsign_stable_timer.stop()

        # If callsign changed, restart the 5-second timer
        if text != self.last_callsign:
            self.last_callsign = text
            if text.strip():  # Only start timer if not empty
                self.callsign_stable_timer.start(5000)  # 5 seconds
                logger.debug(f"Callsign changed to '{text}', waiting 5 seconds...")
            else:
                # Callsign cleared
                logger.debug("Callsign cleared, QSO start time reset")

    def _on_callsign_focus_lost(self) -> None:
        """
        Called when user tabs away from callsign field

        Immediately fetches QRZ callsign info if configured.
        """
        current_callsign = self.callsign_input.text().strip()

        if current_callsign and self.config_manager.get("qrz.auto_fetch", False):
            logger.debug(f"Callsign field lost focus, fetching QRZ info for: {current_callsign}")
            self._fetch_qrz_callsign_async(current_callsign)

    def _on_callsign_stable(self) -> None:
        """
        Called when callsign has been stable for 5 seconds

        Records the QSO start time and optionally fetches QRZ callsign info.
        ALL TIMES ARE IN UTC.
        """
        current_callsign = self.callsign_input.text().strip()

        if current_callsign:
            self.qso_start_time = get_utc_now()
            logger.info(f"QSO start time recorded (UTC): {self.qso_start_time.strftime('%H:%M:%S')} for {current_callsign}")

            # Auto-fetch QRZ info if enabled
            if self.config_manager.get("qrz.auto_fetch", False):
                self._fetch_qrz_callsign_async(current_callsign)
        else:
            self.qso_start_time = None
            logger.debug("QSO start time cleared (callsign empty)")

    def _get_qso_times(self) -> tuple[Optional[str], Optional[str]]:
        """
        Get QSO start and end times in ADIF format (HHMM)

        ALL TIMES ARE IN UTC.

        Returns:
            Tuple of (time_on, time_off) in HHMM format or None if not available
        """
        # time_on: Use qso_start_time if available (recorded when callsign was stable)
        # qso_start_time is already in UTC
        if self.qso_start_time:
            time_on = datetime_to_adif_time(self.qso_start_time)
        else:
            # Fallback to current UTC time from clock display
            utc_now = get_utc_now()
            time_on = datetime_to_adif_time(utc_now)

        # time_off: Record when Save is clicked (now in UTC)
        utc_now = get_utc_now()
        time_off = datetime_to_adif_time(utc_now)

        logger.debug(f"QSO times (UTC): time_on={time_on}, time_off={time_off}")
        return time_on, time_off

    def closeEvent(self, event) -> None:
        """
        Clean up resources when form is closed

        Ensures all timers are stopped and all signals are disconnected.
        """
        try:
            # Stop clock timer if active
            if self.clock_timer.isActive():
                self.clock_timer.stop()
                logger.debug("Always-running clock timer stopped on form close")

            # Stop callsign stability timer if active
            if self.callsign_stable_timer.isActive():
                self.callsign_stable_timer.stop()
                logger.debug("QSO timing timer stopped on form close")

            # Disconnect all signals to prevent orphaned connections
            try:
                self.clock_timer.timeout.disconnect()
            except RuntimeError:
                # Signal already disconnected, this is expected
                pass
            try:
                self.callsign_stable_timer.timeout.disconnect()
            except RuntimeError:
                # Signal already disconnected, this is expected
                pass
            try:
                self.callsign_input.textChanged.disconnect()
            except RuntimeError:
                # Signal already disconnected, this is expected
                pass
            try:
                self.callsign_input.focus_lost.disconnect()
            except RuntimeError:
                # Signal already disconnected, this is expected
                pass

            logger.info("LoggingForm closed and resources cleaned up")
            event.accept()

        except Exception as e:
            logger.error(f"Error cleaning up LoggingForm: {e}", exc_info=True)
            # Accept event anyway to allow exit
            event.accept()

    def _fetch_qrz_callsign(self) -> None:
        """
        Manually fetch QRZ callsign info for current callsign
        """
        callsign = self.callsign_input.text().strip()
        if not callsign:
            QMessageBox.warning(self, "No Callsign", "Please enter a callsign first")
            return

        # Disable button during fetch
        if hasattr(self, 'qrz_lookup_btn'):
            self.qrz_lookup_btn.setEnabled(False)
            self.qrz_lookup_btn.setText("Loading...")

        self._fetch_qrz_callsign_async(callsign)

    def _fetch_qrz_callsign_async(self, callsign: str) -> None:
        """
        Fetch QRZ callsign info asynchronously

        Args:
            callsign: The callsign to look up
        """
        def _callback(info):
            """Callback when lookup completes"""
            # Re-enable button if it exists
            if hasattr(self, 'qrz_lookup_btn') and self.qrz_lookup_btn:
                self.qrz_lookup_btn.setEnabled(True)
                self.qrz_lookup_btn.setText("QRZ↻")

            if info is None:
                logger.debug(f"No QRZ info found for {callsign}")
                return

            # Emit signal to update form fields on main thread (thread-safe)
            self.qrz_data_ready.emit(info)
            logger.info(f"Emitted QRZ data ready signal for {callsign}")

        # Make async request
        self.qrz_service.lookup_callsign_async(callsign, _callback)

    def _populate_from_qrz_info(self, info) -> None:
        """
        Populate form fields with QRZ callsign information

        Args:
            info: CallsignInfo object from QRZ
        """
        try:
            # Fill in name if available and not already filled
            # QRZ returns fname (first name) and name (last name) separately
            # Combine them: "First Last" or just the one that's available
            if (info.fname or info.name) and not self.name_input.text().strip():
                full_name = ""
                if info.fname and info.name:
                    full_name = f"{info.fname} {info.name}"
                elif info.fname:
                    full_name = info.fname
                else:
                    full_name = info.name

                if full_name:
                    self.name_input.setText(full_name)
                    logger.debug(f"Filled operator name from QRZ: {full_name}")

            # Fill in state if available
            if info.state:
                # Try to set state combo if it exists
                if hasattr(self, 'state_combo'):
                    index = self.state_combo.findText(info.state.upper())
                    if index >= 0:
                        self.state_combo.setCurrentIndex(index)
                        logger.debug(f"Set state to {info.state}")

            # Fill in grid if available
            if info.grid and not self.grid_input.text().strip():
                self.grid_input.setText(info.grid.upper())
                logger.debug(f"Filled grid from QRZ: {info.grid}")

            # Fill in QTH if available
            if info.qth and not self.qth_input.text().strip():
                self.qth_input.setText(info.qth)
                logger.debug(f"Filled QTH from QRZ: {info.qth}")

            # Fill in county if available
            if info.county and not self.county_input.text().strip():
                self.county_input.setText(info.county)
                logger.debug(f"Filled county from QRZ: {info.county}")

            # Fill in country if available
            if info.country:
                # Try to set country combo if it exists
                if hasattr(self, 'country_combo'):
                    index = self.country_combo.findText(info.country)
                    if index >= 0:
                        self.country_combo.setCurrentIndex(index)
                        logger.debug(f"Set country to {info.country}")

            # Look up SKCC number from membership database if not already filled
            if not self.skcc_number_input.text().strip():
                try:
                    # Get the callsign being logged
                    callsign = self.callsign_input.text().strip().upper()
                    if callsign:
                        # Query SKCC membership database
                        member = self.skcc_membership.get_member_by_callsign(callsign)
                        if member and member.get('skcc_number'):
                            self.skcc_number_input.setText(member['skcc_number'])
                            logger.info(f"Filled SKCC number from membership database: {member['skcc_number']} for {callsign}")
                        else:
                            logger.debug(f"No SKCC membership found for {callsign}")
                except Exception as e:
                    logger.debug(f"Error looking up SKCC membership for {callsign}: {e}")

        except Exception as e:
            logger.error(f"Error populating form from QRZ info: {e}", exc_info=True)
