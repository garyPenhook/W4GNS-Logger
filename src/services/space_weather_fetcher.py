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
NOAA_SUNSPOTS = "https://services.swpc.noaa.gov/json/sunspots.json"  # Sunspot counts
NOAA_SUNSPOT_AREA = "https://services.swpc.noaa.gov/json/solar_sunspot_areas.json"  # Sunspot areas

# Fallback data source for Solar Flux Index and Sunspots
# HamQSL aggregates various data sources for propagation data
HAMQSL_SOLAR_DATA = "https://www.hamqsl.com/solar.json"
HAMQSL_SOLAR_XML = "https://www.hamqsl.com/solarxml.php"  # XML version with more detailed data

# GIRO (Global Ionosphere Radio Observatory) Real-time Ionospheric Data
# Data from worldwide ionosondes, updated every ~15 minutes
# This provides real measured MUF (MUFD) and other ionospheric parameters
GIRO_STATIONS_API = "https://prop.kc2g.com/api/stations.json"

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

    def get_sunspot_data(self) -> Dict[str, Any]:
        """
        Get sunspot count and Smoothed Sunspot Number (SSN) from NOAA SWPC.

        Returns:
            Dict with:
            - sunspot_count: Current daily sunspot count
            - ssn: Smoothed Sunspot Number (12-month average)
            - timestamp: Data timestamp
            - source: Data source (NOAA SWPC or HamQSL)
        """
        try:
            # Try NOAA sunspot data (current daily count)
            logger.debug("Fetching sunspot data from NOAA SWPC...")
            response = self.session.get(NOAA_SUNSPOTS, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            sunspot_data = {}

            if isinstance(data, list) and len(data) > 0:
                # Get most recent entry
                latest = data[-1]
                if isinstance(latest, dict):
                    sunspot_count = latest.get('sunspot_count')
                    if sunspot_count is not None:
                        try:
                            sunspot_data['sunspot_count'] = int(sunspot_count)
                            sunspot_data['timestamp'] = latest.get('time_tag', datetime.now().isoformat())
                            sunspot_data['source'] = 'NOAA SWPC'
                            logger.info(f"Retrieved sunspot count from NOAA: {sunspot_data['sunspot_count']}")
                        except (ValueError, TypeError):
                            logger.debug(f"Invalid sunspot count value: {sunspot_count}")

            # Now try to get SSN from HamQSL (contains 12-month smoothed average)
            ssn = self._get_smoothed_sunspot_number()
            if ssn is not None:
                sunspot_data['ssn'] = ssn

            return sunspot_data

        except requests.RequestException as e:
            logger.debug(f"Unable to fetch NOAA sunspot data: {e}")
            return {}
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.debug(f"Error parsing NOAA sunspot data: {e}")
            return {}

    def _get_smoothed_sunspot_number(self) -> Optional[float]:
        """
        Get Smoothed Sunspot Number (SSN) - 12-month running average.

        Data Sources (in order of preference):
        1. HamQSL solar data (includes 'ssn' field)
        2. NOAA/other sources as fallback

        Returns:
            SSN value or None if unable to fetch
        """
        try:
            logger.debug("Fetching Smoothed Sunspot Number (SSN) from HamQSL...")
            response = self.session.get(HAMQSL_SOLAR_DATA, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            # HamQSL format includes 'ssn' field (Smoothed Sunspot Number)
            if isinstance(data, dict) and 'ssn' in data:
                try:
                    ssn = float(data['ssn'])
                    if ssn >= 0:  # SSN should be non-negative
                        logger.info(f"Retrieved Smoothed Sunspot Number from HamQSL: {ssn:.0f}")
                        return ssn
                except (ValueError, TypeError):
                    logger.debug(f"Invalid SSN value from HamQSL: {data.get('ssn')}")

            logger.debug("SSN not found in HamQSL response")
            return None

        except requests.RequestException as e:
            logger.debug(f"Unable to fetch SSN from HamQSL: {e}")
            return None
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.debug(f"Error parsing SSN from HamQSL: {e}")
            return None

    def get_solar_data(self) -> Dict[str, Any]:
        """
        Get solar data from NOAA scales (R-scale and S-scale data), Solar Flux Index, and sunspot data.

        Returns:
            Dict with solar radiation, radio blackout information, Solar Flux Index, and sunspot data
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

            # Fetch sunspot data (includes both sunspot count and SSN)
            sunspot_data = self.get_sunspot_data()

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
                'sunspot_count': sunspot_data.get('sunspot_count'),  # Current daily sunspot count
                'sunspot_ssn': sunspot_data.get('ssn'),  # Smoothed Sunspot Number (12-month average)
                'sunspot_source': sunspot_data.get('source', 'NOAA SWPC'),  # Data source
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

    def get_giro_nearest_station_mufd(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """
        Get real-time MUF measurement from nearest GIRO ionosonde station.

        GIRO provides ACTUAL MEASURED ionospheric data from worldwide ionosondes,
        updated every ~15 minutes. This is far more accurate than empirical formulas.

        Args:
            latitude: User latitude in degrees
            longitude: User longitude in degrees

        Returns:
            Dict with:
            - 'mufd': Measured MUFD (MUF for daytime) in MHz
            - 'fof2': Critical frequency (foF2) in MHz
            - 'hmf2': Peak height (hmF2) in km
            - 'station_code': Ionosonde station code
            - 'station_name': Ionosonde station name
            - 'distance_km': Distance from user location to station in km
            - 'time': Measurement time
            Or None if unable to fetch
        """
        try:
            logger.debug("Fetching real-time GIRO ionospheric data from prop.kc2g.com...")
            response = self.session.get(GIRO_STATIONS_API, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            stations = response.json()

            if not isinstance(stations, list) or len(stations) == 0:
                logger.warning("No GIRO station data available")
                return None

            # Calculate distance to each station using simple Haversine approximation
            # For small distances, Euclidean distance in degrees works adequately
            min_distance = float('inf')
            nearest_station = None

            for station_data in stations:
                try:
                    station_info = station_data.get('station', {})
                    station_lat = float(station_info.get('latitude', 0))
                    station_lon = float(station_info.get('longitude', 0))

                    # Simple distance calculation (Euclidean in degrees)
                    # Good enough for finding nearest station
                    lat_diff = latitude - station_lat
                    lon_diff = longitude - station_lon
                    distance_deg = (lat_diff**2 + lon_diff**2)**0.5

                    if distance_deg < min_distance:
                        min_distance = distance_deg
                        nearest_station = station_data

                except (ValueError, TypeError):
                    continue

            if nearest_station is None:
                logger.warning("Unable to process GIRO station data")
                return None

            # Extract relevant data from nearest station
            station_info = nearest_station.get('station', {})
            mufd = nearest_station.get('mufd')
            fof2 = nearest_station.get('fof2')
            hmf2 = nearest_station.get('hmf2')
            time_str = nearest_station.get('time', 'Unknown')

            # Convert distance back to km (rough approximation: 1 degree ≈ 111 km)
            distance_km = min_distance * 111.0

            logger.info(
                f"Got GIRO data from nearest station: {station_info.get('code', 'Unknown')} "
                f"({station_info.get('name', 'Unknown')}), {distance_km:.0f}km away. "
                f"MUFD={mufd:.1f}MHz, foF2={fof2:.1f}MHz at {time_str}"
            )

            return {
                'mufd': mufd,
                'fof2': fof2,
                'hmf2': hmf2,
                'station_code': station_info.get('code', 'Unknown'),
                'station_name': station_info.get('name', 'Unknown'),
                'distance_km': round(distance_km, 1),
                'time': time_str,
                'source': 'GIRO'
            }

        except requests.RequestException as e:
            logger.debug(f"Unable to fetch GIRO data: {e}")
            return None
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.debug(f"Error parsing GIRO data: {e}")
            return None

    def close(self) -> None:
        """Close the session"""
        self.session.close()
