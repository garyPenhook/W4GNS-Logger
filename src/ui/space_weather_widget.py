"""
Space Weather Widget

Displays current space weather conditions and HF propagation forecasts.
"""

import logging
from typing import Optional, Dict
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QProgressBar,
    QPushButton, QGridLayout
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
import threading

from src.services.space_weather_fetcher import SpaceWeatherFetcher
from src.services.voacap_muf_fetcher import VOACAPMUFFetcher, MUFPrediction
from src.utils.cache import TTLCache
from src.config.settings import ConfigManager

logger = logging.getLogger(__name__)


class SpaceWeatherWidget(QWidget):
    """Displays current space weather conditions and HF propagation status"""

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

        self._init_ui()

        # Defer initial refresh to avoid blocking GUI initialization
        # Uses QTimer.singleShot to defer until event loop is running
        # This allows the window to render immediately while network data loads in background
        QTimer.singleShot(100, self._refresh_in_background)

        # Auto-refresh every hour (space weather updates every 3 hours, hourly refresh ensures timely updates)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_in_background)
        self.refresh_timer.start(3600000)  # 1 hour

    def _init_ui(self) -> None:
        """Initialize UI components"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Current Conditions Section
        conditions_group = self._create_current_conditions_section()
        main_layout.addWidget(conditions_group)

        # K-Index Status Section
        kindex_group = self._create_kindex_section()
        main_layout.addWidget(kindex_group)

        # Best Band NOW Section (NEW!)
        best_band_group = self._create_best_band_now_section()
        main_layout.addWidget(best_band_group)

        # Maximum Usable Frequency (MUF) Section
        muf_group = self._create_muf_section()
        main_layout.addWidget(muf_group)

        # Solar Activity Section
        solar_group = self._create_solar_section()
        main_layout.addWidget(solar_group)

        # HF Propagation Recommendation Section
        propagation_group = self._create_propagation_section()
        main_layout.addWidget(propagation_group)

        # Refresh button and status
        controls_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh Now")
        refresh_btn.clicked.connect(self.refresh)
        controls_layout.addWidget(refresh_btn)

        self.update_status_label = QLabel("Loading...")
        self.update_status_label.setFont(QFont("Arial", 8))
        controls_layout.addWidget(self.update_status_label)

        # Data source indicator
        self.data_source_label = QLabel("Data: NOAA SWPC")
        self.data_source_label.setFont(QFont("Arial", 7))
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
        self.status_label_main.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        status_layout.addWidget(self.status_label_main)

        self.status_indicator = QLabel("●")
        self.status_indicator.setFont(QFont("Arial", 24))
        status_layout.addWidget(self.status_indicator)

        self.hf_condition_label = QLabel("HF Condition: ")
        self.hf_condition_label.setFont(QFont("Arial", 11))
        status_layout.addWidget(self.hf_condition_label)

        status_layout.addStretch()
        layout.addLayout(status_layout)

        # Description
        self.description_label = QLabel("")
        self.description_label.setFont(QFont("Arial", 9))
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label)

        # Recommendation
        self.recommendation_label = QLabel("")
        self.recommendation_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
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
        kindex_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        kindex_layout.addWidget(kindex_label)

        self.kp_value_label = QLabel("--")
        self.kp_value_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
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
        self.aindex_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        aindex_layout.addWidget(self.aindex_label)
        aindex_layout.addWidget(QLabel("(Lower is better for DX)"))
        aindex_layout.addStretch()
        layout.addLayout(aindex_layout)

        group.setLayout(layout)
        return group

    def _create_best_band_now_section(self) -> QGroupBox:
        """Create 'Best Band NOW' recommendation section with time-aware analysis"""
        group = QGroupBox("🎯 BEST BAND FOR WORLDWIDE COMMUNICATION NOW")
        group.setStyleSheet("QGroupBox { font-weight: bold; }")
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Time and location info
        time_info_layout = QHBoxLayout()
        self.best_band_time_label = QLabel("Time: -- UTC | Location: --")
        self.best_band_time_label.setFont(QFont("Arial", 9))
        time_info_layout.addWidget(self.best_band_time_label)
        time_info_layout.addStretch()
        layout.addLayout(time_info_layout)

        # Best band recommendation (LARGE)
        best_band_layout = QHBoxLayout()

        # Time period emoji
        self.best_band_emoji = QLabel("❓")
        self.best_band_emoji.setFont(QFont("Arial", 24))
        self.best_band_emoji.setMinimumWidth(50)
        best_band_layout.addWidget(self.best_band_emoji)

        # Band name and reason
        recommendation_vbox = QVBoxLayout()

        # Best band name (LARGE) - uses system palette, works in light and dark mode
        self.best_band_name = QLabel("--")
        self.best_band_name.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        self.best_band_name.setStyleSheet("color: #1E7D5E;")  # Medium green, readable in both modes
        recommendation_vbox.addWidget(self.best_band_name)

        # Reason text - uses system palette
        self.best_band_reason = QLabel("Loading propagation data...")
        self.best_band_reason.setFont(QFont("Arial", 9))
        self.best_band_reason.setWordWrap(True)
        # No color style - uses system palette text color
        recommendation_vbox.addWidget(self.best_band_reason)

        # MUF and margin info - uses system palette
        self.best_band_muf_info = QLabel("MUF: -- MHz | Margin: -- MHz")
        self.best_band_muf_info.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        # No color style - uses system palette text color
        recommendation_vbox.addWidget(self.best_band_muf_info)

        best_band_layout.addLayout(recommendation_vbox)
        best_band_layout.addStretch()
        layout.addLayout(best_band_layout)

        # Top 3 bands section
        layout.addWidget(QLabel("Next best options:"))
        self.best_band_top3_label = QLabel("Loading...")
        self.best_band_top3_label.setFont(QFont("Arial", 8))
        # Use palette-aware styling with padding only, no explicit colors
        self.best_band_top3_label.setStyleSheet("padding: 5px;")
        self.best_band_top3_label.setWordWrap(True)
        layout.addWidget(self.best_band_top3_label)

        group.setLayout(layout)
        return group

    def _create_muf_section(self) -> QGroupBox:
        """Create Maximum Usable Frequency (MUF) bar chart display"""
        group = QGroupBox("Maximum Usable Frequency (MUF) - HF Band Predictions")
        layout = QVBoxLayout()

        # MUF explanation
        info_label = QLabel(
            "MUF = Maximum Usable Frequency. The bar shows the highest frequency available now.\n"
            "If band frequency is BELOW MUF: works for any distance.\n"
            "If band frequency is ABOVE MUF: only works for distant contacts."
        )
        info_label.setFont(QFont("Arial", 8))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Status legend
        legend_label = QLabel(
            "🟢 Green (Reliable): Band works for local, regional, AND distant stations\n"
            "🔴 Red (Long-distance): Band only works with distant stations via skip"
        )
        legend_label.setFont(QFont("Arial", 8))
        legend_label.setWordWrap(True)
        legend_label.setStyleSheet("color: gray;")
        layout.addWidget(legend_label)

        # Create grid for MUF bars (2 columns)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(8)

        self.muf_band_labels: Dict[str, QLabel] = {}  # Band name -> label with bar
        self.muf_value_labels: Dict[str, QLabel] = {}  # Band name -> value label

        # Practical amateur HF bands to display (most hams can't accommodate 160m antenna)
        bands_to_show = ["80m", "60m", "40m", "30m", "20m", "17m", "15m", "12m", "10m", "6m"]

        for i, band in enumerate(bands_to_show):
            row = i % 3
            col = (i // 3) * 2

            # Band label
            band_label = QLabel(f"{band}:")
            band_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            grid_layout.addWidget(band_label, row, col)

            # MUF value and bar container
            value_bar_layout = QHBoxLayout()

            # MUF value label
            muf_value_label = QLabel("--")
            muf_value_label.setFont(QFont("Courier", 10, QFont.Weight.Bold))
            muf_value_label.setMinimumWidth(50)
            self.muf_value_labels[band] = muf_value_label
            value_bar_layout.addWidget(muf_value_label)

            # Simplified bar representation using label with styled background
            # We'll show this as text with indicator (using text color coding)
            muf_bar_label = QLabel("█░░░░░░░░░░ Calculating...")
            muf_bar_label.setFont(QFont("Courier", 8))
            muf_bar_label.setMinimumWidth(120)
            self.muf_band_labels[band] = muf_bar_label
            value_bar_layout.addWidget(muf_bar_label)

            value_bar_layout.addStretch()

            grid_layout.addLayout(value_bar_layout, row, col + 1)

        layout.addLayout(grid_layout)

        # Add note about location
        location_label = QLabel("Location: Getting grid square from settings...")
        location_label.setFont(QFont("Arial", 8))
        location_label.setStyleSheet("color: gray;")
        self.muf_location_label = location_label
        layout.addWidget(location_label)

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
        self.sfi_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        sfi_layout.addWidget(self.sfi_label)
        sfi_layout.addWidget(QLabel("(Higher = Better for 10-15-20m)"))
        sfi_layout.addStretch()
        layout.addLayout(sfi_layout)

        # SFI condition indicator
        self.sfi_condition_label = QLabel("")
        self.sfi_condition_label.setFont(QFont("Arial", 9))
        layout.addWidget(self.sfi_condition_label)

        # Sunspot Count
        sunspot_layout = QHBoxLayout()
        sunspot_layout.addWidget(QLabel("Sunspot Count:"))
        self.sunspot_count_label = QLabel("--")
        self.sunspot_count_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        sunspot_layout.addWidget(self.sunspot_count_label)
        sunspot_layout.addWidget(QLabel("(Current observed count)"))
        sunspot_layout.addStretch()
        layout.addLayout(sunspot_layout)

        # Smoothed Sunspot Number (SSN)
        ssn_layout = QHBoxLayout()
        ssn_layout.addWidget(QLabel("Smoothed Sunspot # (SSN):"))
        self.ssn_label = QLabel("--")
        self.ssn_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        ssn_layout.addWidget(self.ssn_label)
        ssn_layout.addWidget(QLabel("(12-month average)"))
        ssn_layout.addStretch()
        layout.addLayout(ssn_layout)

        # X-ray Class
        xray_layout = QHBoxLayout()
        xray_layout.addWidget(QLabel("X-Ray Class:"))
        self.xray_class_label = QLabel("--")
        self.xray_class_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        xray_layout.addWidget(self.xray_class_label)
        xray_layout.addWidget(QLabel("(A=Quiet, X=Major flare)"))
        xray_layout.addStretch()
        layout.addLayout(xray_layout)

        group.setLayout(layout)
        return group

    def _create_propagation_section(self) -> QGroupBox:
        """Create HF propagation recommendation"""
        group = QGroupBox("HF Band Recommendations")
        layout = QVBoxLayout()

        self.band_recommendations = QLabel("")
        self.band_recommendations.setFont(QFont("Arial", 9))
        self.band_recommendations.setWordWrap(True)
        layout.addWidget(self.band_recommendations)

        group.setLayout(layout)
        return group

    def _refresh_in_background(self) -> None:
        """Start refresh operation in background thread to avoid blocking UI"""
        def background_refresh():
            """Background thread function to fetch data"""
            try:
                # Try cache first
                cached = self.cache.get("current_conditions")
                if cached is not None:
                    logger.debug("Using cached space weather data")
                    # Update UI on main thread
                    self._update_ui(cached)
                    self._update_muf_display(cached)
                    return

                # Fetch new data (blocking network calls)
                logger.debug("Fetching current space weather data from NOAA (background thread)")
                conditions = self.fetcher.get_current_conditions()
                solar = self.fetcher.get_solar_data()

                # Combine data
                data = {**conditions, **solar}

                # Cache the results
                self.cache.set("current_conditions", data)

                # Update UI on main thread
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

        # Start background thread (daemon thread exits with main app)
        thread = threading.Thread(target=background_refresh, daemon=True)
        thread.start()

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

        # Band recommendations
        self._update_band_recommendations(data)

    def _update_band_recommendations(self, data: dict) -> None:
        """Update HF band recommendations based on actual time-of-day propagation"""
        try:
            kp = data.get('kp_index')
            sfi = data.get('solar_flux_index')

            if kp is None or sfi is None:
                self.band_recommendations.setText("Unable to assess conditions")
                return

            kp_val = int(float(kp))
            sfi_val = int(float(sfi))

            # Get user's home grid and calculate best bands NOW
            home_grid = self.config.get("general.home_grid", "FN20qd")

            # Calculate MUF predictions
            predictions = self.muf_fetcher.get_band_muf_predictions(
                sfi=sfi_val,
                k_index=kp_val,
                home_grid=home_grid
            )

            # Get best band ranking based on time of day
            best_band_info = self.muf_fetcher.get_best_band_now(
                predictions=predictions,
                home_grid=home_grid,
                sfi=sfi_val,
                k_index=kp_val
            )

            # Get time period and top 3 bands
            time_period = best_band_info.get('time_period', 'Unknown')
            top_3 = best_band_info.get('top_3_bands', [])

            recommendations = []

            # Add time period indicator
            if time_period == "Daytime":
                recommendations.append(f"☀️ {time_period}: High frequencies best for worldwide")
            elif time_period == "Terminator (Best!)":
                recommendations.append(f"🌅 {time_period}: All bands excellent!")
            else:  # Nighttime
                recommendations.append(f"🌙 {time_period}: Low frequencies best for worldwide")

            # Add top 3 recommended bands with usability info
            if top_3:
                recommendations.append("\nBest bands to use RIGHT NOW:")
                for i, band_info in enumerate(top_3, 1):
                    band = band_info['band']
                    muf = band_info['muf']
                    margin = band_info['margin']
                    is_marginal = band_info.get('marginal', False)

                    # Determine quality indicator based on margin
                    if margin > 5:
                        quality = "✓ Excellent"
                    elif margin > 2:
                        quality = "✓ Good"
                    elif margin >= 0:
                        quality = "⚠ Marginal"
                    else:
                        quality = "⚠⚠ VERY Marginal" if margin < -2 else "⚠ Marginal"

                    # Add warning indicator if marginal high-frequency band
                    margin_note = " ← TRY THIS FIRST (right frequency for daytime!)" if is_marginal and margin < 0 else ""

                    recommendations.append(f"{i}. {band}: {quality} (MUF margin: {margin:+.1f} MHz){margin_note}")
            else:
                recommendations.append("\nNo bands currently usable. Wait for conditions to improve.")

            self.band_recommendations.setText("\n".join(recommendations))

        except Exception as e:
            logger.error(f"Error updating band recommendations: {e}")
            self.band_recommendations.setText(f"Error calculating recommendations: {str(e)[:50]}")

    def _update_muf_display(self, data: dict) -> None:
        """Update MUF bar chart with current predictions"""
        try:
            # Get user's grid square from settings
            home_grid = self.config.get("general.home_grid", "FN20qd")

            # Update location label
            self.muf_location_label.setText(f"Location: {home_grid} (your home grid)")

            # Get solar flux and K-index for MUF calculation
            sfi = data.get('solar_flux_index')
            kp = data.get('kp_index')

            if sfi is None or kp is None:
                logger.warning("Missing SFI or K-index data for MUF calculation")
                for band in self.muf_band_labels.keys():
                    self.muf_value_labels[band].setText("--")
                    self.muf_band_labels[band].setText("Data unavailable")
                return

            try:
                sfi_val = int(float(sfi))
                kp_val = int(float(kp))
            except (ValueError, TypeError):
                logger.warning(f"Invalid SFI or K-index values: SFI={sfi}, K={kp}")
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

            # Update "Best Band Now" section (NEW!)
            self._update_best_band_now(predictions, home_grid, sfi_val, kp_val)

            # Update display for each band
            for band_name, label in self.muf_band_labels.items():
                if band_name in predictions:
                    prediction = predictions[band_name]

                    # Update MUF value label
                    value_label = self.muf_value_labels[band_name]
                    value_label.setText(f"{prediction.muf_value:.1f}M")

                    # Create visual bar representation
                    # Bar fills from 0 to 50 MHz
                    filled_blocks = int((prediction.muf_value / 50.0) * 10)
                    filled_blocks = min(filled_blocks, 10)

                    bar = "█" * filled_blocks + "░" * (10 - filled_blocks)

                    # Add status indicator with user-friendly explanations
                    if prediction.usable:
                        status = "✓ Reliable"
                        color = "#00AA00"  # Green
                    else:
                        # Red = band is below MUF, only works for long distance (skip)
                        status = "⚠ Long-distance"
                        color = "#FF0000"  # Red

                    # Set color for value label
                    value_label.setStyleSheet(f"color: {color};")

                    # Update bar label
                    band_min, band_max = prediction.frequency_range
                    label.setText(f"{bar} {status}")
                    label.setStyleSheet(f"color: {color};")

                    logger.debug(f"{band_name}: MUF={prediction.muf_value:.1f}MHz "
                               f"({band_min}-{band_max}MHz), Usable={prediction.usable}")
                else:
                    # Band not in predictions
                    self.muf_value_labels[band_name].setText("N/A")
                    self.muf_band_labels[band_name].setText("Not calculated")

            logger.info(f"Updated MUF display with {len(predictions)} band predictions")

        except Exception as e:
            logger.error(f"Error updating MUF display: {e}", exc_info=True)
            # Show error in first band label
            if self.muf_band_labels:
                first_band = next(iter(self.muf_band_labels.values()))
                first_band.setText(f"Error: {str(e)[:40]}")

    def _update_best_band_now(self, predictions: Dict[str, 'MUFPrediction'],
                              home_grid: str, sfi: int, k_index: int) -> None:
        """Update 'Best Band NOW' section with time-aware recommendation"""
        try:
            # Get best band recommendation
            best_band_data = self.muf_fetcher.get_best_band_now(
                predictions=predictions,
                home_grid=home_grid,
                sfi=sfi,
                k_index=k_index
            )

            # Update time and location
            self.best_band_time_label.setText(
                f"Time: {best_band_data['utc_time']} | Location: {home_grid} | "
                f"Time Period: {best_band_data['time_period']}"
            )

            # Update emoji based on time period
            self.best_band_emoji.setText(best_band_data['time_emoji'])

            # Update best band name
            if best_band_data['band']:
                self.best_band_name.setText(best_band_data['band'])
                self.best_band_name.setStyleSheet("color: #006400; font-weight: bold;")  # Dark green
            else:
                self.best_band_name.setText("No data")
                self.best_band_name.setStyleSheet("color: #ff0000; font-weight: bold;")  # Red

            # Update reason
            self.best_band_reason.setText(best_band_data['reason'])

            # Update MUF and margin info
            if best_band_data['band'] and best_band_data['muf'] is not None:
                margin_str = f"{best_band_data['margin']:.1f}" if best_band_data['margin'] else "--"
                muf_str = f"{best_band_data['muf']:.1f}"
                self.best_band_muf_info.setText(
                    f"MUF: {muf_str} MHz | Margin: {margin_str} MHz above band edge"
                )
            else:
                self.best_band_muf_info.setText("MUF: -- MHz | Margin: -- MHz")

            # Update top 3 bands
            if best_band_data['top_3_bands']:
                top_3_items = []
                for b in best_band_data['top_3_bands']:
                    marginal_indicator = " ⚠" if b.get('marginal', False) else ""
                    top_3_items.append(f"{b['band']} ({b['muf']:.1f}M, {b['margin']:+.1f}){marginal_indicator}")
                top_3_text = "  " + " | ".join(top_3_items)
                self.best_band_top3_label.setText(top_3_text)
            else:
                self.best_band_top3_label.setText("(No usable bands at this time)")

            logger.info(f"Best band now: {best_band_data['band']} ({best_band_data['time_period']})")

        except Exception as e:
            logger.error(f"Error updating best band now: {e}", exc_info=True)
            self.best_band_name.setText("Error")
            self.best_band_reason.setText(f"Failed to calculate: {str(e)[:50]}")

    def closeEvent(self, event) -> None:
        """Clean up on close"""
        self.refresh_timer.stop()
        self.fetcher.close()
        self.muf_fetcher.close()
        super().closeEvent(event)
