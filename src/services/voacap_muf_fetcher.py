"""
VOACAP MUF (Maximum Usable Frequency) Prediction Service

Provides Maximum Usable Frequency predictions for HF propagation based on:
1. Empirical calculation from Solar Flux Index (SFI)
2. Optional VOACAP online predictions for path-specific accuracy
3. K-Index and geomagnetic conditions

The MUF is the highest frequency that will refract off the ionosphere for a given path.
"""

import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

# Standard HF bands used in amateur radio (frequency in MHz)
HF_BANDS = {
    "160m": (1.8, 2.0),
    "80m": (3.5, 4.0),
    "60m": (5.3, 5.4),
    "40m": (7.0, 7.3),
    "30m": (10.1, 10.15),
    "20m": (14.0, 14.35),
    "17m": (18.068, 18.168),
    "15m": (21.0, 21.45),
    "12m": (24.89, 24.99),
    "10m": (28.0, 29.7),
}

# VOACAP API endpoints and configuration
VOACAP_BASE_URL = "https://www.voacap.com"
VOACAP_QUERY_ENDPOINT = f"{VOACAP_BASE_URL}/query.html"


class MUFSource(Enum):
    """Source of MUF data"""
    EMPIRICAL = "empirical"  # SFI-based calculation
    VOACAP = "voacap"  # VOACAP online predictions
    HYBRID = "hybrid"  # Best of both


class MUFPrediction:
    """MUF prediction for a specific band"""

    def __init__(self, band_name: str, frequency_range: Tuple[float, float],
                 muf_value: float, confidence: float = 0.75, source: MUFSource = MUFSource.EMPIRICAL):
        """
        Initialize MUF prediction

        Args:
            band_name: Band name (e.g., "20m")
            frequency_range: Tuple of (min_freq, max_freq) in MHz
            muf_value: Maximum Usable Frequency in MHz
            confidence: Confidence level (0.0-1.0)
            source: Source of the prediction
        """
        self.band_name = band_name
        self.frequency_range = frequency_range
        self.muf_value = muf_value
        self.confidence = confidence
        self.source = source
        self.usable = muf_value >= frequency_range[1]  # Band is usable if MUF >= max band freq

    def __repr__(self) -> str:
        status = "✓" if self.usable else "✗"
        return f"{self.band_name}: {self.muf_value:.1f} MHz {status}"


class VOACAPMUFFetcher:
    """Fetch and calculate Maximum Usable Frequency predictions"""

    def __init__(self):
        """Initialize VOACAP MUF fetcher"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'W4GNS-Logger/1.0 (ham radio logging application)'
        })
        self.last_update = None
        self.cached_predictions: Dict[str, List[MUFPrediction]] = {}

    def calculate_empirical_muf(
        self,
        sfi: int,
        k_index: int,
        latitude: float = 38.0,
        frequency_mhz: float = 14.0
    ) -> float:
        """
        Calculate Maximum Usable Frequency using empirical model

        Based on standard ionospheric propagation models:
        - Solar Flux Index (SFI) is the primary driver
        - K-Index provides geomagnetic disturbance correction
        - Latitude affects ionospheric height
        - Time of day affects ionospheric absorption (simplified)

        Formula: MUF ≈ Base_MUF × (1 + Frequency_Factor) × (1 + K_Factor)

        Args:
            sfi: Solar Flux Index (70-300)
            k_index: Geomagnetic K-Index (0-9)
            latitude: Observer latitude in degrees (0-90)
            frequency_mhz: Operating frequency in MHz (for attenuation calc)

        Returns:
            Estimated MUF in MHz
        """
        try:
            # Base MUF calculation from Solar Flux Index
            # Empirical relationship: MUF increases with SFI
            # Nominal: SFI=70 -> MUF~9MHz at 14MHz reference
            #          SFI=200 -> MUF~25MHz at 14MHz reference
            base_muf = 9.0 + (sfi - 70) * 0.08  # Linear approximation

            # K-Index correction (negative effects from geomagnetic disturbance)
            # K=0-3: Normal conditions, slight boost
            # K=4-6: Degraded, slight reduction
            # K=7-9: Very poor, significant reduction
            if k_index <= 3:
                k_factor = 1.05  # Slight improvement
            elif k_index <= 6:
                k_factor = 1.0 - (k_index - 3) * 0.05  # 5% reduction per step
            else:
                k_factor = 0.80 - (k_index - 7) * 0.08  # More aggressive reduction

            # Latitude correction (equatorial regions have higher MUF)
            latitude_factor = 1.0 + (0.3 * (90.0 - abs(latitude)) / 90.0)

            # Frequency-dependent attenuation factor
            # Lower frequencies penetrate better
            freq_factor = max(0.85, 1.0 - (frequency_mhz - 3.5) / 100.0)

            # Calculate final MUF
            muf = base_muf * k_factor * latitude_factor * freq_factor

            # Ensure reasonable bounds
            muf = max(2.0, min(50.0, muf))

            return round(muf, 1)

        except Exception as e:
            logger.error(f"Error calculating empirical MUF: {e}")
            return 14.0  # Default fallback

    def get_band_muf_predictions(
        self,
        sfi: int,
        k_index: int,
        home_grid: str = "FN20qd",
        latitude: Optional[float] = None
    ) -> Dict[str, MUFPrediction]:
        """
        Get MUF predictions for all standard HF bands

        Args:
            sfi: Solar Flux Index (70-300)
            k_index: Geomagnetic K-Index (0-9)
            home_grid: Maidenhead grid square for location
            latitude: Override latitude (derived from grid if not provided)

        Returns:
            Dictionary of band name -> MUFPrediction
        """
        try:
            # Derive latitude from grid square if not provided
            if latitude is None:
                latitude = self._grid_to_latitude(home_grid)

            predictions = {}

            for band_name, (min_freq, max_freq) in HF_BANDS.items():
                # Use center frequency for calculation
                center_freq = (min_freq + max_freq) / 2.0

                # Calculate MUF for this band
                muf = self.calculate_empirical_muf(sfi, k_index, latitude, center_freq)

                # Create prediction
                prediction = MUFPrediction(
                    band_name=band_name,
                    frequency_range=(min_freq, max_freq),
                    muf_value=muf,
                    confidence=0.75,
                    source=MUFSource.EMPIRICAL
                )

                predictions[band_name] = prediction

            logger.info(f"Calculated MUF for {len(predictions)} bands (SFI={sfi}, K={k_index})")
            return predictions

        except Exception as e:
            logger.error(f"Error getting band MUF predictions: {e}", exc_info=True)
            return {}

    def query_voacap_muf(
        self,
        source_grid: str,
        dest_grid: str = "JO00AA",  # Default to central Europe for diversity
        frequency_mhz: float = 14.0,
        utc_hour: Optional[int] = None
    ) -> Optional[float]:
        """
        Query VOACAP online for path-specific MUF prediction

        Note: This requires web scraping or VOACAP API access.
        Currently implements a simplified approach based on grid distance.

        Args:
            source_grid: Source Maidenhead grid square
            dest_grid: Destination Maidenhead grid square
            frequency_mhz: Operating frequency in MHz
            utc_hour: UTC hour (0-23), defaults to current hour

        Returns:
            Estimated MUF for path in MHz, or None if query fails
        """
        try:
            if utc_hour is None:
                utc_hour = datetime.now(timezone.utc).hour

            # Calculate path distance and angle
            distance_km = self._grid_distance(source_grid, dest_grid)
            path_angle = self._grid_bearing(source_grid, dest_grid)

            logger.debug(f"VOACAP query: {source_grid} -> {dest_grid} "
                        f"({distance_km:.0f}km, bearing={path_angle:.0f}°)")

            # For now, use simplified MUF formula based on path distance
            # Longer paths generally require higher MUF
            # This is a simplified model; real VOACAP is more complex
            base_muf = 14.0  # 20m band baseline
            distance_factor = 1.0 + (distance_km / 10000.0) * 0.3  # Increase with distance

            muf = base_muf * distance_factor

            return round(max(3.5, min(50.0, muf)), 1)

        except Exception as e:
            logger.error(f"Error querying VOACAP MUF: {e}")
            return None

    def get_muf_status_string(self, predictions: Dict[str, MUFPrediction]) -> str:
        """
        Create a summary string of MUF status

        Args:
            predictions: Dictionary of MUF predictions

        Returns:
            Human-readable status string
        """
        if not predictions:
            return "No MUF data available"

        usable_bands = [band_name for band_name, pred in predictions.items() if pred.usable]
        total_bands = len(predictions)

        status = f"{len(usable_bands)}/{total_bands} bands usable\n"

        # Show top 3 usable bands
        top_bands = sorted(
            [(band_name, pred) for band_name, pred in predictions.items() if pred.usable],
            key=lambda x: x[1].muf_value,
            reverse=True
        )[:3]

        if top_bands:
            status += "Best: " + ", ".join([f"{band}({pred.muf_value:.0f}M)" for band, pred in top_bands])

        return status

    @staticmethod
    def _grid_to_latitude(grid: str) -> float:
        """
        Convert Maidenhead grid square to latitude

        Args:
            grid: Maidenhead grid square (e.g., "FN20qd")

        Returns:
            Latitude in degrees (-90 to 90)
        """
        try:
            if len(grid) < 2:
                return 38.0  # Default to mid-US

            # First two characters: field (degrees)
            lat_field = (ord(grid[1].upper()) - ord('A')) * 10
            lat_field = lat_field - 90  # Convert to ±90

            # Third and fourth characters: square (minutes)
            if len(grid) >= 4:
                lat_square = int(grid[3]) * 2
                lat_field += lat_square

            # Additional characters add seconds (ignored for simplicity)

            return float(lat_field)
        except Exception:
            return 38.0  # Default fallback

    @staticmethod
    def _grid_to_longitude(grid: str) -> float:
        """
        Convert Maidenhead grid square to longitude

        Args:
            grid: Maidenhead grid square (e.g., "FN20qd")

        Returns:
            Longitude in degrees (-180 to 180)
        """
        try:
            if len(grid) < 1:
                return -75.0  # Default to US East Coast

            # First character: field (degrees)
            lon_field = (ord(grid[0].upper()) - ord('A')) * 20
            lon_field = lon_field - 180  # Convert to ±180

            # Second character: square (minutes)
            if len(grid) >= 2:
                lon_square = int(grid[2]) * 5
                lon_field += lon_square

            # Additional characters add seconds (ignored for simplicity)

            return float(lon_field)
        except Exception:
            return -75.0  # Default fallback

    @classmethod
    def _grid_distance(cls, grid1: str, grid2: str) -> float:
        """
        Calculate approximate distance between two grid squares

        Uses simplified great-circle distance formula

        Args:
            grid1: Source Maidenhead grid square
            grid2: Destination Maidenhead grid square

        Returns:
            Distance in kilometers
        """
        import math

        lat1 = math.radians(cls._grid_to_latitude(grid1))
        lon1 = math.radians(cls._grid_to_longitude(grid1))
        lat2 = math.radians(cls._grid_to_latitude(grid2))
        lon2 = math.radians(cls._grid_to_longitude(grid2))

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Earth radius in km

        return c * r

    @classmethod
    def _grid_bearing(cls, grid1: str, grid2: str) -> float:
        """
        Calculate bearing from grid1 to grid2

        Args:
            grid1: Source Maidenhead grid square
            grid2: Destination Maidenhead grid square

        Returns:
            Bearing in degrees (0-360)
        """
        import math

        lat1 = math.radians(cls._grid_to_latitude(grid1))
        lon1 = math.radians(cls._grid_to_longitude(grid1))
        lat2 = math.radians(cls._grid_to_latitude(grid2))
        lon2 = math.radians(cls._grid_to_longitude(grid2))

        dlon = lon2 - lon1

        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)

        bearing = math.atan2(x, y)
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360

        return bearing

    def get_color_for_muf(self, prediction: MUFPrediction) -> str:
        """
        Get color code for MUF bar display

        Args:
            prediction: MUF prediction

        Returns:
            Color in hex format
        """
        if prediction.usable:
            # Band is usable - use gradient from yellow to green based on margin
            margin = (prediction.muf_value - prediction.frequency_range[1]) / 5.0
            if margin < 0:
                return "#FFFF00"  # Yellow - marginal
            elif margin < 3:
                return "#90EE90"  # Light green - good
            else:
                return "#00AA00"  # Dark green - excellent
        else:
            # Band not usable
            if prediction.muf_value >= prediction.frequency_range[0] * 0.8:
                return "#FF6600"  # Orange - barely not usable
            else:
                return "#FF0000"  # Red - not usable

    def close(self) -> None:
        """Close HTTP session"""
        try:
            self.session.close()
        except Exception as e:
            logger.warning(f"Error closing VOACAP session: {e}")
