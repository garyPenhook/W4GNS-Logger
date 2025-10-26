"""
Space Weather Data Fetcher

Retrieves current space weather conditions from NOAA SWPC for HF propagation assessment.
"""

import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# NOAA SWPC URLs (Official NOAA Space Weather Prediction Center)
NOAA_SCALES = "https://services.swpc.noaa.gov/products/noaa-scales.json"
NOAA_KP_FORECAST = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json"
NOAA_F107_FLUX = "https://services.swpc.noaa.gov/json/f107_cm_flux.json"  # Solar Flux (F10.7)

# Fallback data source for Solar Flux Index
# HamQSL aggregates various data sources for propagation data
HAMQSL_SOLAR_DATA = "https://www.hamqsl.com/solar.json"

# Default timeout for HTTP requests
HTTP_TIMEOUT = 10


class SpaceWeatherFetcher:
    """Fetcher for NOAA space weather data"""

    def __init__(self):
        """Initialize the space weather fetcher"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'W4GNS-Logger/1.0 (ham radio logging application)'
        })

    def get_current_conditions(self) -> Dict[str, Any]:
        """
        Get current space weather conditions from NOAA SWPC.

        Returns:
            Dict with current geomagnetic scale and K-index forecast data
        """
        try:
            # Get scales data
            scales_response = self.session.get(NOAA_SCALES, timeout=HTTP_TIMEOUT)
            scales_response.raise_for_status()
            scales_data = scales_response.json()

            # Get K-index forecast
            kp_response = self.session.get(NOAA_KP_FORECAST, timeout=HTTP_TIMEOUT)
            kp_response.raise_for_status()
            kp_data = kp_response.json()

            # Parse current scales (index "0" is current)
            current_scales = scales_data.get("0", {})
            g_scale = current_scales.get("G", {}).get("Scale")
            r_scale = current_scales.get("R", {}).get("Scale")
            s_scale = current_scales.get("S", {}).get("Scale")

            # Parse K-index from forecast (skip header row at index 0)
            kp_index = None
            if kp_data and len(kp_data) > 1:
                # Find the latest data row (usually last one is most recent)
                for row in reversed(kp_data[1:]):
                    if row[2] == "observed":  # Look for observed data
                        kp_index = float(row[1]) if row[1] else None
                        break
                # If no observed, use latest predicted
                if kp_index is None and len(kp_data) > 1:
                    kp_index = float(kp_data[-1][1]) if kp_data[-1][1] else None

            result = {
                'timestamp': current_scales.get('TimeStamp', datetime.now().isoformat()),
                'kp_index': kp_index,
                'geomagnetic_scale': g_scale,  # G-scale (0-5)
                'radio_blackout_scale': r_scale,  # R-scale
                'solar_radiation_scale': s_scale,  # S-scale
                'geomagnetic_text': current_scales.get("G", {}).get("Text", "unknown"),
                'status': self._assess_propagation_status(kp_index),
                'raw_scales': current_scales
            }
            return result

        except requests.RequestException as e:
            logger.error(f"Error fetching NOAA space weather data: {e}")
            return self._get_error_result(str(e))
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing NOAA space weather data: {e}")
            return self._get_error_result(f"Data parsing error: {str(e)}")

    def get_k_index_forecast(self) -> Dict[str, Any]:
        """
        Get K-index forecast from NOAA SWPC.

        Returns:
            Dict with K-index forecast data
        """
        try:
            response = self.session.get(NOAA_KP_FORECAST, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            # Extract forecast values (skip header row at index 0)
            forecasts = []
            if data and len(data) > 1:
                # data[0] is header: ['time_tag', 'kp', 'observed', 'noaa_scale']
                # data[1:] are data rows
                for row in data[1:12]:  # Next 12 periods (3 days)
                    try:
                        forecasts.append({
                            'time_tag': row[0] if len(row) > 0 else None,
                            'kp': float(row[1]) if row[1] else None,
                            'observed': row[2] if len(row) > 2 else False,  # 'observed' or 'predicted'
                            'noaa_scale': row[3] if len(row) > 3 else None  # e.g., 'G1', 'R2'
                        })
                    except (IndexError, ValueError):
                        continue

            return {
                'forecasts': forecasts,
                'timestamp': datetime.now().isoformat(),
                'count': len(forecasts)
            }

        except requests.RequestException as e:
            logger.error(f"Error fetching K-index forecast: {e}")
            return {'forecasts': [], 'error': str(e), 'timestamp': datetime.now().isoformat()}
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing K-index forecast: {e}")
            return {'forecasts': [], 'error': str(e), 'timestamp': datetime.now().isoformat()}

    def get_solar_flux_index(self) -> Optional[float]:
        """
        Get current Solar Flux Index (SFI/F10.7) from authoritative online sources.

        Data Sources (in order of preference):
        1. NOAA SWPC F10.7 (official US government space weather data)
        2. HamQSL solar data (community aggregation of various sources)
        3. Calculated estimate from NOAA geomagnetic conditions

        Returns:
            Current SFI value (in solar flux units) or None if unable to fetch

        Note: MUF calculations use this real online data combined with K-index
        from NOAA to determine band usability. This is the industry-standard
        approach since no direct online MUF API is available.
        """
        try:
            # Primary source: NOAA SWPC F10.7 (Solar Flux) - MOST AUTHORITATIVE
            logger.debug("Fetching Solar Flux (F10.7) from NOAA SWPC...")
            response = self.session.get(NOAA_F107_FLUX, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            noaa_data = response.json()

            if isinstance(noaa_data, list) and len(noaa_data) > 0:
                # Get the most recent entry
                latest = noaa_data[-1]
                if isinstance(latest, dict) and 'flux' in latest:
                    try:
                        sfi = float(latest['flux'])
                        if sfi > 0:
                            logger.info(f"Retrieved Solar Flux from NOAA SWPC: {sfi:.0f} sfu")
                            return sfi
                    except (ValueError, TypeError):
                        pass

            logger.debug("NOAA F10.7 data not available, trying HamQSL...")

        except requests.RequestException as e:
            logger.debug(f"Unable to fetch NOAA F10.7: {e}, trying fallback...")
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.debug(f"Error parsing NOAA F10.7: {e}, trying fallback...")

        try:
            # Secondary source: HamQSL (community maintained aggregation)
            response = self.session.get(HAMQSL_SOLAR_DATA, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            # HamQSL format includes 'sfi' field
            if isinstance(data, dict) and 'sfi' in data:
                try:
                    sfi = float(data['sfi'])
                    if sfi > 0:
                        logger.info(f"Retrieved Solar Flux from HamQSL: {sfi:.0f} sfu")
                        return sfi
                except (ValueError, TypeError):
                    pass

            logger.debug("SFI not found in HamQSL, will use estimation fallback")
            return None

        except requests.RequestException as e:
            logger.debug(f"Unable to fetch from HamQSL: {e}")
            return None
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.debug(f"Error parsing SFI from HamQSL: {e}")
            return None

    def estimate_sfi_from_conditions(self, g_scale: Optional[str] = None,
                                     r_scale: Optional[str] = None,
                                     kp_index: Optional[float] = None) -> float:
        """
        Estimate Solar Flux Index from geomagnetic conditions when actual SFI unavailable.

        Uses NOAA G-scale and R-scale data to estimate SFI:
        - Quiet conditions: SFI ~ 70-90
        - Unsettled: SFI ~ 90-120
        - Active: SFI ~ 120-180
        - Minor storm: SFI ~ 90-120
        - Major storm: SFI ~ 50-90 (reduced propagation)

        Args:
            g_scale: Geomagnetic scale (G0-G5)
            r_scale: Radio blackout scale (R0-R5)
            kp_index: K-index value (0-9)

        Returns:
            Estimated SFI value
        """
        # Start with baseline
        estimated_sfi = 85.0

        # G-scale affects estimated SFI
        if g_scale:
            if g_scale == 'G0':
                estimated_sfi += 20  # Very quiet
            elif g_scale == 'G1':
                estimated_sfi += 10
            elif g_scale in ('G2', 'G3'):
                estimated_sfi -= 10  # Minor storm
            elif g_scale in ('G4', 'G5'):
                estimated_sfi -= 30  # Major storm

        # R-scale (radio blackout) also correlates with solar activity
        if r_scale and r_scale != 'R0':
            try:
                scale_num = int(r_scale[1]) if len(r_scale) > 1 else 0
                estimated_sfi += (scale_num * 15)  # Radio events indicate higher solar activity
            except (ValueError, IndexError):
                pass

        # K-index can provide additional context
        if kp_index is not None:
            # Very high K-index can reduce apparent propagation
            if kp_index > 6:
                estimated_sfi -= (kp_index - 6) * 5

        # Ensure within reasonable bounds
        estimated_sfi = max(50, min(250, estimated_sfi))

        logger.info(f"Estimated SFI: {estimated_sfi:.0f} (G:{g_scale}, R:{r_scale}, Kp:{kp_index})")
        return estimated_sfi

    def get_solar_data(self) -> Dict[str, Any]:
        """
        Get solar data from NOAA scales (R-scale and S-scale data) and Solar Flux Index.

        Returns:
            Dict with solar radiation, radio blackout information, and Solar Flux Index
        """
        try:
            response = self.session.get(NOAA_SCALES, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            scales_data = response.json()

            # Get current and forecast scales
            current = scales_data.get("0", {})
            forecast_day1 = scales_data.get("1", {})
            forecast_day2 = scales_data.get("2", {})
            forecast_day3 = scales_data.get("3", {})

            # Also fetch Solar Flux Index
            solar_flux = self.get_solar_flux_index()

            # If actual SFI not available, estimate from conditions
            if solar_flux is None:
                kp_response = self.session.get(NOAA_KP_FORECAST, timeout=HTTP_TIMEOUT)
                kp_response.raise_for_status()
                kp_data = kp_response.json()

                # Get current K-index
                kp_index = None
                if kp_data and len(kp_data) > 1:
                    for row in reversed(kp_data[1:]):
                        if row[2] == "observed":
                            kp_index = float(row[1]) if row[1] else None
                            break

                # Use estimate based on conditions
                g_scale = current.get('G', {}).get('Scale')
                r_scale = current.get('R', {}).get('Scale')
                solar_flux = self.estimate_sfi_from_conditions(g_scale, r_scale, kp_index)

            result = {
                'timestamp': current.get('TimeStamp', datetime.now().isoformat()),
                'solar_flux_index': solar_flux,  # Add SFI for MUF calculations
                'current': {
                    'radio_blackout_scale': current.get('R', {}).get('Scale'),
                    'radio_blackout_text': current.get('R', {}).get('Text'),
                    'solar_radiation_scale': current.get('S', {}).get('Scale'),
                    'solar_radiation_text': current.get('S', {}).get('Text'),
                },
                'forecast': {
                    'day1': {
                        'date': forecast_day1.get('DateStamp'),
                        'radio_blackout': forecast_day1.get('R', {}).get('Scale'),
                        'solar_radiation': forecast_day1.get('S', {}).get('Scale'),
                    },
                    'day2': {
                        'date': forecast_day2.get('DateStamp'),
                        'radio_blackout': forecast_day2.get('R', {}).get('Scale'),
                        'solar_radiation': forecast_day2.get('S', {}).get('Scale'),
                    },
                    'day3': {
                        'date': forecast_day3.get('DateStamp'),
                        'radio_blackout': forecast_day3.get('R', {}).get('Scale'),
                        'solar_radiation': forecast_day3.get('S', {}).get('Scale'),
                    },
                }
            }
            return result

        except requests.RequestException as e:
            logger.error(f"Error fetching solar data: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing solar data: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}

    @staticmethod
    def _assess_propagation_status(kp_value: Optional[float]) -> Dict[str, Any]:
        """
        Assess HF propagation status based on K-index.

        Args:
            kp_value: Current Kp value (0-9)

        Returns:
            Dict with status, recommendation, and color
        """
        if kp_value is None:
            return {
                'status': 'Unknown',
                'recommendation': 'Check NOAA SWPC',
                'color': '#CCCCCC',
                'hf_condition': 'Unknown'
            }

        kp_val = float(kp_value)

        if kp_val < 3:
            return {
                'status': 'Excellent',
                'recommendation': 'Ideal conditions for HF DX',
                'color': '#00AA00',  # Green
                'hf_condition': 'Excellent',
                'description': 'Very stable, long-distance propagation enhanced'
            }
        elif kp_val < 4:
            return {
                'status': 'Good',
                'recommendation': 'Good conditions for DX',
                'color': '#55DD00',  # Light green
                'hf_condition': 'Good',
                'description': 'Stable conditions, good DX potential'
            }
        elif kp_val < 5:
            return {
                'status': 'Fair',
                'recommendation': 'Suitable for normal HF operation',
                'color': '#FFAA00',  # Orange
                'hf_condition': 'Fair',
                'description': 'Slightly unsettled, local/regional propagation good'
            }
        elif kp_val < 6:
            return {
                'status': 'Unsettled',
                'recommendation': 'Increasing ionospheric disturbance',
                'color': '#FF6600',  # Dark orange
                'hf_condition': 'Unsettled',
                'description': 'Minor geomagnetic disturbance ongoing'
            }
        elif kp_val < 7:
            return {
                'status': 'Disturbed',
                'recommendation': 'Reduced HF propagation, especially at high latitudes',
                'color': '#FF3300',  # Red-orange
                'hf_condition': 'Disturbed',
                'description': 'Moderate geomagnetic storm in progress'
            }
        else:
            return {
                'status': 'Storm',
                'recommendation': 'Severe HF degradation expected',
                'color': '#FF0000',  # Red
                'hf_condition': 'Storm',
                'description': 'Major geomagnetic storm - avoid DX attempts'
            }


    @staticmethod
    def _get_error_result(error_msg: str) -> Dict[str, Any]:
        """Return error result dict"""
        return {
            'timestamp': datetime.now().isoformat(),
            'error': error_msg,
            'kp_index': None,
            'status': {
                'status': 'Unavailable',
                'recommendation': 'Unable to fetch data',
                'color': '#999999',
                'hf_condition': 'Unknown'
            }
        }

    def close(self) -> None:
        """Close the session"""
        self.session.close()
