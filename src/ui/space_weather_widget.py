"""
Space Weather Widget

Displays current space weather conditions and HF propagation forecasts.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QProgressBar,
    QPushButton, QGridLayout
)
from PyQt6.QtCore import QTimer, Qt, QMetaObject, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QFont
import threading

from src.services.space_weather_fetcher import SpaceWeatherFetcher
from src.services.voacap_muf_fetcher import VOACAPMUFFetcher, MUFPrediction
from src.utils.cache import TTLCache
from src.config.settings import ConfigManager

logger = logging.getLogger(__name__)


class SpaceWeatherWidget(QWidget):
    """Displays current space weather conditions and HF propagation status"""

    # Signal emitted when data is fetched and ready to display (thread-safe)
    data_fetched = pyqtSignal(dict)

    # Default font size multipliers for consistent scaling
    FONT_SMALL = 0.95  # 9-10pt equivalent
    FONT_NORMAL = 1.15  # 11-12pt equivalent
    FONT_LARGE = 1.5  # 15pt equivalent
    FONT_XLARGE = 1.8  # 18pt equivalent
    FONT_HUGE = 2.3    # 23pt+ equivalent

    def _get_font(self, size_multiplier: float = FONT_NORMAL, bold: bool = False) -> QFont:
        """Get a properly scaled font based on application default font and multiplier"""
        font = QFont()  # Get application default font
        # Scale the point size
        base_size = font.pointSize()
        if base_size <= 0:
            base_size = 10  # Fallback if point size isn't set
        font.setPointSize(int(base_size * size_multiplier))
        if bold:
            font.setBold(True)
        return font

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize space weather widget

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.fetcher = SpaceWeatherFetcher()
        self.muf_fetcher = VOACAPMUFFetcher()
        self.config = ConfigManager()

        # Cache space weather data with 1-hour TTL (NOAA updates every 3 hours)
        self.cache = TTLCache(ttl_seconds=3600)
        # Cache MUF predictions with 1-hour TTL (synced with space weather refresh)
        self.muf_cache = TTLCache(ttl_seconds=3600)

        # Store MUF predictions for display
        self.current_muf_predictions: Dict[str, MUFPrediction] = {}

        # For passing data from background thread to main thread
        self._pending_data: Optional[Dict[str, Any]] = None

        self._init_ui()

        # Connect data_fetched signal to slot (thread-safe way to update UI from background thread)
        self.data_fetched.connect(self._on_data_fetched_signal)

        # Defer initial refresh to avoid blocking GUI initialization
        # Uses QTimer.singleShot to defer until event loop is running
        # This allows the window to render immediately while network data loads in background
        # Use 500ms delay to ensure event loop is fully active during startup
        QTimer.singleShot(500, self._refresh_in_background)

        # Auto-refresh every 15 minutes (MUF changes frequently with solar conditions)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_in_background)
        self.refresh_timer.start(900000)  # 15 minutes

    def _init_ui(self) -> None:
        """Initialize UI components"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(30)  # Maximum spacing for readability
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Current Conditions Section
        conditions_group = self._create_current_conditions_section()
        main_layout.addWidget(conditions_group)

        # K-Index and Solar Activity side by side (save vertical space)
        kindex_solar_layout = QHBoxLayout()
        kindex_solar_layout.setSpacing(15)

        # K-Index Status Section
        kindex_group = self._create_kindex_section()
        kindex_solar_layout.addWidget(kindex_group)

        # Solar Activity Section
        solar_group = self._create_solar_section()
        kindex_solar_layout.addWidget(solar_group)

        main_layout.addLayout(kindex_solar_layout)

        # Maximum Usable Frequency (MUF) Section
        muf_group = self._create_muf_section()
        main_layout.addWidget(muf_group)

        # HF Propagation Recommendation Section removed to save space for MUF sections

        # Refresh button and status
        controls_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh Now")
        refresh_btn.clicked.connect(self.refresh)
        controls_layout.addWidget(refresh_btn)

        self.update_status_label = QLabel("Loading...")
        self.update_status_label.setFont(self._get_font(self.FONT_SMALL))
        controls_layout.addWidget(self.update_status_label)

        # Data source indicator
        self.data_source_label = QLabel("Data: NOAA SWPC")
        self.data_source_label.setFont(self._get_font(self.FONT_SMALL))
        self.data_source_label.setStyleSheet("color: #666666;")
        controls_layout.addWidget(self.data_source_label)

        controls_layout.addStretch()
        main_layout.addLayout(controls_layout)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _create_current_conditions_section(self) -> QGroupBox:
        """Create current conditions display"""
        group = QGroupBox("Current Space Weather Conditions")
        layout = QVBoxLayout()

        # Status indicator with color
        status_layout = QHBoxLayout()
        self.status_label_main = QLabel("Status: ")
        self.status_label_main.setFont(self._get_font(self.FONT_LARGE, bold=True))
        status_layout.addWidget(self.status_label_main)

        self.status_indicator = QLabel("●")
        self.status_indicator.setFont(self._get_font(self.FONT_HUGE))
        status_layout.addWidget(self.status_indicator)

        self.hf_condition_label = QLabel("HF Condition: ")
        self.hf_condition_label.setFont(self._get_font(self.FONT_LARGE))
        status_layout.addWidget(self.hf_condition_label)

        status_layout.addStretch()
        layout.addLayout(status_layout)

        # Description
        self.description_label = QLabel("")
        self.description_label.setFont(self._get_font(self.FONT_NORMAL))
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label)

        # Recommendation
        self.recommendation_label = QLabel("")
        self.recommendation_label.setFont(self._get_font(self.FONT_NORMAL, bold=True))
        self.recommendation_label.setWordWrap(True)
        layout.addWidget(self.recommendation_label)

        group.setLayout(layout)
        return group

    def _create_kindex_section(self) -> QGroupBox:
        """Create K-index display"""
        group = QGroupBox("Geomagnetic K-Index")
        layout = QVBoxLayout()

        # K-Index value and scale
        kindex_layout = QHBoxLayout()

        kindex_label = QLabel("Kp: ")
        kindex_label.setFont(self._get_font(self.FONT_LARGE, bold=True))
        kindex_layout.addWidget(kindex_label)

        self.kp_value_label = QLabel("--")
        self.kp_value_label.setFont(self._get_font(self.FONT_HUGE, bold=True))
        self.kp_value_label.setMinimumWidth(50)
        kindex_layout.addWidget(self.kp_value_label)

        kindex_layout.addWidget(QLabel("(0=Excellent, 9=Storm)"))
        kindex_layout.addStretch()
        layout.addLayout(kindex_layout)

        # K-Index progress bar (0-9 scale)
        self.kindex_progress = QProgressBar()
        self.kindex_progress.setMaximum(9)
        self.kindex_progress.setValue(0)
        self.kindex_progress.setTextVisible(True)
        layout.addWidget(self.kindex_progress)

        # A-Index
        aindex_layout = QHBoxLayout()
        aindex_layout.addWidget(QLabel("Planetary A-Index:"))
        self.aindex_label = QLabel("--")
        self.aindex_label.setFont(self._get_font(self.FONT_LARGE, bold=True))
        aindex_layout.addWidget(self.aindex_label)
        aindex_layout.addWidget(QLabel("(Lower is better for DX)"))
        aindex_layout.addStretch()
        layout.addLayout(aindex_layout)

        group.setLayout(layout)
        return group

    def _create_muf_section(self) -> QGroupBox:
        """Create Maximum Usable Frequency (MUF) bar display"""
        group = QGroupBox("Maximum Usable Frequency (MUF) - Updated every 15 minutes")
        layout = QVBoxLayout()
        layout.setSpacing(25)
        layout.setContentsMargins(20, 20, 20, 20)

        # MUF value display (large and prominent)
        muf_header_layout = QHBoxLayout()
        muf_label = QLabel("Current MUF:")
        muf_label.setFont(self._get_font(self.FONT_NORMAL, bold=True))
        muf_header_layout.addWidget(muf_label)

        self.muf_value_label = QLabel("-- MHz")
        self.muf_value_label.setFont(self._get_font(self.FONT_XLARGE, bold=True))
        self.muf_value_label.setStyleSheet("color: #1E7D5E;")  # Green
        muf_header_layout.addWidget(self.muf_value_label)
        muf_header_layout.addStretch()
        layout.addLayout(muf_header_layout)

        # MUF bar representation
        bar_layout = QHBoxLayout()
        bar_layout.setSpacing(10)

        self.muf_bar_display = QLabel("█░░░░░░░░░░░░░░░░░░ Loading...")
        self.muf_bar_display.setFont(self._get_font(self.FONT_LARGE))
        bar_layout.addWidget(self.muf_bar_display)

        self.muf_status_label = QLabel("Calculating...")
        self.muf_status_label.setFont(self._get_font(self.FONT_NORMAL))
        bar_layout.addWidget(self.muf_status_label)

        layout.addLayout(bar_layout)

        # MUF explanation
        info_label = QLabel(
            "MUF (Maximum Usable Frequency) is the highest frequency that reliably supports skywave propagation.\n"
            "Higher MUF = More bands available for long-distance communication."
        )
        info_label.setFont(self._get_font(self.FONT_NORMAL))
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)

        # Location info
        self.muf_location_label = QLabel("Location: -- (grid square from settings)")
        self.muf_location_label.setFont(self._get_font(self.FONT_NORMAL))
        self.muf_location_label.setStyleSheet("color: gray;")
        layout.addWidget(self.muf_location_label)

        group.setLayout(layout)
        return group

    def _create_solar_section(self) -> QGroupBox:
        """Create solar activity display"""
        group = QGroupBox("Solar Activity")
        layout = QVBoxLayout()

        # Solar Flux Index
        sfi_layout = QHBoxLayout()
        sfi_layout.addWidget(QLabel("Solar Flux Index (SFI):"))
        self.sfi_label = QLabel("-- sfu")
        self.sfi_label.setFont(self._get_font(self.FONT_LARGE, bold=True))
        sfi_layout.addWidget(self.sfi_label)
        sfi_layout.addWidget(QLabel("(Higher = Better for 10-15-20m)"))
        sfi_layout.addStretch()
        layout.addLayout(sfi_layout)

        # SFI condition indicator
        self.sfi_condition_label = QLabel("")
        self.sfi_condition_label.setFont(self._get_font(self.FONT_NORMAL))
        layout.addWidget(self.sfi_condition_label)

        # Sunspot Count
        sunspot_layout = QHBoxLayout()
        sunspot_layout.addWidget(QLabel("Sunspot Count:"))
        self.sunspot_count_label = QLabel("--")
        self.sunspot_count_label.setFont(self._get_font(self.FONT_LARGE, bold=True))
        sunspot_layout.addWidget(self.sunspot_count_label)
        sunspot_layout.addWidget(QLabel("(Current observed count)"))
        sunspot_layout.addStretch()
        layout.addLayout(sunspot_layout)

        # Smoothed Sunspot Number (SSN)
        ssn_layout = QHBoxLayout()
        ssn_layout.addWidget(QLabel("Smoothed Sunspot # (SSN):"))
        self.ssn_label = QLabel("--")
        self.ssn_label.setFont(self._get_font(self.FONT_LARGE, bold=True))
        ssn_layout.addWidget(self.ssn_label)
        ssn_layout.addWidget(QLabel("(12-month average)"))
        ssn_layout.addStretch()
        layout.addLayout(ssn_layout)

        # X-ray Class
        xray_layout = QHBoxLayout()
        xray_layout.addWidget(QLabel("X-Ray Class:"))
        self.xray_class_label = QLabel("--")
        self.xray_class_label.setFont(self._get_font(self.FONT_LARGE, bold=True))
        xray_layout.addWidget(self.xray_class_label)
        xray_layout.addWidget(QLabel("(A=Quiet, X=Major flare)"))
        xray_layout.addStretch()
        layout.addLayout(xray_layout)

        group.setLayout(layout)
        return group

    def _refresh_in_background(self) -> None:
        """Start refresh operation in background thread to avoid blocking UI"""
        def background_refresh():
            """Background thread function to fetch data (non-blocking)"""
            try:
                # Try cache first
                cached = self.cache.get("current_conditions")
                if cached is not None:
                    logger.debug("Using cached space weather data")
                    # Emit signal to update UI on main thread (thread-safe)
                    self.data_fetched.emit(cached)
                    return

                # Fetch new data (blocking network calls - but in background thread!)
                logger.debug("Fetching current space weather data from NOAA (background thread)")
                conditions = self.fetcher.get_current_conditions()
                logger.debug(f"Fetched conditions: {conditions}")
                solar = self.fetcher.get_solar_data()
                logger.debug(f"Fetched solar data: {solar}")

                if conditions is None or solar is None:
                    logger.warning(f"Incomplete data fetch - conditions={conditions is not None}, solar={solar is not None}")

                # Combine data
                data = {**(conditions or {}), **(solar or {})}
                logger.debug(f"Combined data: {data}")

                # Cache the results
                self.cache.set("current_conditions", data)

                # Emit signal to update UI on main thread (thread-safe)
                logger.info("✓ Emitting data_fetched signal to main thread")
                self.data_fetched.emit(data)

            except Exception as e:
                logger.error(f"Error refreshing space weather: {e}", exc_info=True)
                # Update status label with error on main thread
                error_msg = f"Error: {str(e)[:100]}"  # Increased from 50 to 100 chars for better error visibility
                QMetaObject.invokeMethod(self.update_status_label, "setText", Qt.ConnectionType.QueuedConnection, error_msg)

        # Start the background thread to fetch data
        thread = threading.Thread(target=background_refresh, daemon=True)
        thread.start()

    @pyqtSlot(dict)
    def _on_data_fetched_signal(self, data: dict) -> None:
        """Slot called when data_fetched signal is emitted (runs on main thread, thread-safe)"""
        logger.info("✓ _on_data_fetched_signal received data - signal/slot working!")
        try:
            # Update UI with fetched data
            self._update_ui(data)
            self._update_muf_display(data)

            # Update timestamp
            self.update_status_label.setText(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

            # Show data source information
            sources = []
            if data.get('kp_index') is not None:
                sources.append("K-index: NOAA SWPC")
            if data.get('solar_flux_index') is not None:
                sources.append("Solar Flux: NOAA/HamQSL")
            if data.get('sunspot_count') is not None or data.get('sunspot_ssn') is not None:
                sunspot_source = data.get('sunspot_source', 'NOAA/HamQSL')
                sources.append(f"Sunspots: {sunspot_source}")
            if sources:
                self.data_source_label.setText(f"Data: {' | '.join(sources)}")
            else:
                self.data_source_label.setText("Data: Calculated estimate")

        except Exception as e:
            logger.error(f"Error updating space weather display: {e}", exc_info=True)
            self.update_status_label.setText(f"Error: {str(e)[:50]}")

    def refresh(self) -> None:
        """Refresh space weather data (synchronous - for manual refresh button)"""
        try:
            # Try cache first
            cached = self.cache.get("current_conditions")
            if cached is not None:
                logger.debug("Using cached space weather data")
                self._update_ui(cached)
                self._update_muf_display(cached)
                return

            # Fetch new data
            logger.debug("Fetching current space weather data from NOAA")
            conditions = self.fetcher.get_current_conditions()
            solar = self.fetcher.get_solar_data()

            # Combine data
            data = {**conditions, **solar}

            # Cache the results
            self.cache.set("current_conditions", data)

            # Update UI
            self._update_ui(data)
            self._update_muf_display(data)

            # Update timestamp and data sources
            self.update_status_label.setText(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

            # Show data source information
            sources = []
            if data.get('kp_index') is not None:
                sources.append("K-index: NOAA SWPC")
            if data.get('solar_flux_index') is not None:
                sources.append("Solar Flux: NOAA/HamQSL")
            if data.get('sunspot_count') is not None or data.get('sunspot_ssn') is not None:
                sunspot_source = data.get('sunspot_source', 'NOAA/HamQSL')
                sources.append(f"Sunspots: {sunspot_source}")
            if sources:
                self.data_source_label.setText(f"Data: {' | '.join(sources)}")
            else:
                self.data_source_label.setText("Data: Calculated estimate")

        except Exception as e:
            logger.error(f"Error refreshing space weather: {e}")
            self.update_status_label.setText(f"Error: {str(e)[:50]}")

    def _update_ui(self, data: dict) -> None:
        """Update UI with space weather data"""
        # Current conditions
        status_info = data.get('status', {})
        if status_info:
            status = status_info.get('status', 'Unknown')
            hf_condition = status_info.get('hf_condition', 'Unknown')
            description = status_info.get('description', '')
            recommendation = status_info.get('recommendation', '')
            color = status_info.get('color', '#999999')

            self.status_label_main.setText(f"Status: {status}")
            self.hf_condition_label.setText(f"HF Condition: {hf_condition}")
            self.description_label.setText(description)
            self.recommendation_label.setText(f"📡 {recommendation}")

            # Set indicator color
            self.status_indicator.setStyleSheet(f"color: {color};")

        # K-Index
        kp = data.get('kp_index')
        if kp is not None:
            try:
                kp_val = float(kp)
                self.kp_value_label.setText(f"{kp_val:.1f}")
                self.kindex_progress.setValue(int(min(kp_val, 9)))  # Cap at 9

                # Color code the progress bar
                if kp_val < 3:
                    style = "background-color: #00AA00;"  # Green
                elif kp_val < 5:
                    style = "background-color: #FFAA00;"  # Orange
                elif kp_val < 7:
                    style = "background-color: #FF6600;"  # Dark orange
                else:
                    style = "background-color: #FF0000;"  # Red

                self.kindex_progress.setStyleSheet(f"QProgressBar::chunk {{{style}}}")
            except (ValueError, TypeError):
                self.kp_value_label.setText("--")

        # Geomagnetic Scale
        g_scale = data.get('geomagnetic_scale')
        g_text = data.get('geomagnetic_text', '')
        if g_scale is not None:
            self.aindex_label.setText(f"G-Scale: {g_scale} ({g_text})")

        # Radio Blackout Scale
        r_scale = data.get('radio_blackout_scale')
        if r_scale is not None:
            # R-scale affects HF, add this info
            if r_scale == '0':
                self.sfi_condition_label.setText("Radio: None")
            elif r_scale in ('1', '2'):
                self.sfi_condition_label.setText("Radio: Minor disturbance")
            else:
                self.sfi_condition_label.setText("Radio: Major event - HF impact!")

        # Solar Flux Index (actual value)
        sfi = data.get('solar_flux_index')
        if sfi is not None:
            try:
                sfi_val = float(sfi)
                self.sfi_label.setText(f"{sfi_val:.0f} sfu")
            except (ValueError, TypeError):
                self.sfi_label.setText("-- sfu")

        # Sunspot Count
        sunspot_count = data.get('sunspot_count')
        if sunspot_count is not None:
            try:
                count_val = int(sunspot_count)
                self.sunspot_count_label.setText(str(count_val))
            except (ValueError, TypeError):
                self.sunspot_count_label.setText("--")
        else:
            self.sunspot_count_label.setText("--")

        # Smoothed Sunspot Number (SSN)
        ssn = data.get('sunspot_ssn')
        if ssn is not None:
            try:
                ssn_val = float(ssn)
                self.ssn_label.setText(f"{ssn_val:.0f}")
            except (ValueError, TypeError):
                self.ssn_label.setText("--")
        else:
            self.ssn_label.setText("--")

        # Solar Radiation Scale
        s_scale = data.get('solar_radiation_scale')
        if s_scale is not None:
            if s_scale == '0':
                self.xray_class_label.setText("Solar: Quiet")
            else:
                self.xray_class_label.setText(f"Solar: Event Level {s_scale}")

        # Band recommendations removed - no longer displayed

    def _update_muf_display(self, data: dict) -> None:
        """Update single MUF bar display with current maximum MUF value"""
        try:
            # Get user's grid square from settings
            home_grid = self.config.get("general.home_grid", "FN20qd")
            self.muf_location_label.setText(f"Location: {home_grid} (your home grid)")

            # Get solar flux and K-index for MUF calculation
            sfi = data.get('solar_flux_index')
            kp = data.get('kp_index')

            if sfi is None or kp is None:
                logger.warning("Missing SFI or K-index data for MUF calculation")
                self.muf_value_label.setText("-- MHz")
                self.muf_bar_display.setText("█░░░░░░░░░░░░░░░░░░ Data unavailable")
                self.muf_status_label.setText("Cannot calculate - missing data")
                return

            try:
                sfi_val = int(float(sfi))
                kp_val = int(float(kp))
            except (ValueError, TypeError):
                logger.warning(f"Invalid SFI or K-index values: SFI={sfi}, K={kp}")
                self.muf_value_label.setText("-- MHz")
                self.muf_bar_display.setText("█░░░░░░░░░░░░░░░░░░ Invalid data")
                return

            # Calculate MUF predictions
            logger.debug(f"Calculating MUF for location {home_grid} (SFI={sfi_val}, K={kp_val})")
            predictions = self.muf_fetcher.get_band_muf_predictions(
                sfi=sfi_val,
                k_index=kp_val,
                home_grid=home_grid
            )

            # Store predictions for reference
            self.current_muf_predictions = predictions

            # Find the maximum MUF value from all predictions
            max_muf = 0
            best_band = None
            if predictions:
                for band_name, prediction in predictions.items():
                    if prediction.muf_value > max_muf:
                        max_muf = prediction.muf_value
                        best_band = band_name

            # Display the maximum MUF value
            self.muf_value_label.setText(f"{max_muf:.0f} MHz")
            self.muf_value_label.setStyleSheet("color: #1E7D5E;")  # Green

            # Create visual bar representation (0-60 MHz scale)
            filled_blocks = int((max_muf / 60.0) * 20)
            filled_blocks = min(filled_blocks, 20)
            bar = "█" * filled_blocks + "░" * (20 - filled_blocks)

            self.muf_bar_display.setText(bar)
            self.muf_status_label.setText(f"Maximum MUF: {max_muf:.0f} MHz (from {best_band})")

            logger.info(f"Updated MUF display: Max MUF = {max_muf:.1f} MHz from {best_band}")

        except Exception as e:
            logger.error(f"Error updating MUF display: {e}", exc_info=True)
            self.muf_value_label.setText("-- MHz")
            self.muf_bar_display.setText(f"█░░░░░░░░░░░░░░░░░░ Error: {str(e)[:30]}")

    def closeEvent(self, event) -> None:
        """Clean up on close"""
        self.refresh_timer.stop()
        self.fetcher.close()
        self.muf_fetcher.close()
        super().closeEvent(event)
