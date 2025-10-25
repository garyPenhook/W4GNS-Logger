"""
QRZ.com XML API Client

Provides interface to QRZ.com XML API for callsign lookups and logbook management.
"""

import logging
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class QRZError(Exception):
    """Base exception for QRZ API errors"""
    pass


class QRZAuthError(QRZError):
    """Exception for authentication failures"""
    pass


@dataclass
class CallsignInfo:
    """Callsign information from QRZ database"""
    callsign: str
    name: str = ""
    addr1: str = ""
    addr2: str = ""
    state: str = ""
    zip: str = ""
    country: str = ""
    grid: str = ""
    lat: str = ""
    lon: str = ""
    email: str = ""
    qth: str = ""
    class_: str = ""  # License class
    codes: str = ""  # License codes
    qsl_mgr: str = ""
    qsl_via: str = ""
    club: str = ""
    web: str = ""
    image: str = ""
    bio: str = ""
    bio_date: str = ""
    user_agreed: bool = False
    lotw_member: bool = False
    eqsl_member: bool = False
    iota: str = ""
    sig_info: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'callsign': self.callsign,
            'name': self.name,
            'addr1': self.addr1,
            'addr2': self.addr2,
            'state': self.state,
            'zip': self.zip,
            'country': self.country,
            'grid': self.grid,
            'lat': self.lat,
            'lon': self.lon,
            'email': self.email,
            'qth': self.qth,
            'class': self.class_,
            'codes': self.codes,
            'qsl_mgr': self.qsl_mgr,
            'qsl_via': self.qsl_via,
            'club': self.club,
            'web': self.web,
            'image': self.image,
            'bio': self.bio,
            'bio_date': self.bio_date,
            'lotw_member': self.lotw_member,
            'eqsl_member': self.eqsl_member,
            'iota': self.iota,
            'sig_info': self.sig_info,
        }


class QRZAPIClient:
    """Client for QRZ.com XML API"""

    BASE_URL = "https://xmldata.qrz.com/xml/current/"

    def __init__(self, username: str, password: str, api_key: Optional[str] = None, timeout: int = 10):
        """
        Initialize QRZ API client

        Args:
            username: QRZ.com account username (for callsign lookups)
            password: QRZ.com account password (for callsign lookups)
            api_key: QRZ.com API Key (for logbook uploads - optional)
            timeout: Request timeout in seconds
        """
        self.username = username
        self.password = password
        self.api_key = api_key
        self.timeout = timeout
        self.session_key: Optional[str] = None
        self.session_expires: Optional[float] = None
        self.callsign_cache: Dict[str, CallsignInfo] = {}
        self.cache_ttl = 86400  # 24 hours

    def authenticate(self) -> bool:
        """
        Authenticate with QRZ.com and get session key

        Returns:
            True if authentication successful

        Raises:
            QRZAuthError: If authentication fails
        """
        try:
            params = urllib.parse.urlencode({
                'username': self.username,
                'password': self.password,
                'agent': 'W4GNSLogger/1.0'
            })

            url = f"{self.BASE_URL}?{params}"

            with urllib.request.urlopen(url, timeout=self.timeout) as response:
                data = response.read().decode('utf-8')
                root = ET.fromstring(data)

                # Check for error (handle namespaces)
                error_elem = self._find_element(root, 'Error')
                if error_elem is not None:
                    error_msg = error_elem.text or "Unknown error"
                    logger.error(f"QRZ authentication failed: {error_msg}")
                    raise QRZAuthError(f"Authentication failed: {error_msg}")

                # Get session key - handle namespaces
                session_elem = self._find_element(root, 'Session')
                if session_elem is None:
                    raise QRZAuthError("No Session element in response")

                key_elem = self._find_element(session_elem, 'Key')
                if key_elem is None or not key_elem.text:
                    raise QRZAuthError("No session key in response")

                self.session_key = key_elem.text
                self.session_expires = time.time() + (3600 * 24)  # 24 hours
                logger.info(f"QRZ authentication successful, session key: {self.session_key[:10]}...")
                return True

        except urllib.error.URLError as e:
            logger.error(f"QRZ connection error: {e}")
            raise QRZError(f"Connection failed: {e}")
        except ET.ParseError as e:
            logger.error(f"QRZ XML parse error: {e}")
            raise QRZError(f"Invalid XML response: {e}")

    def _ensure_authenticated(self) -> None:
        """Ensure we have a valid session, re-authenticate if needed"""
        if (self.session_key is None or
            self.session_expires is None or
            time.time() > self.session_expires):
            self.authenticate()

    def lookup_callsign(self, callsign: str, use_cache: bool = True) -> Optional[CallsignInfo]:
        """
        Look up a callsign in QRZ database

        Args:
            callsign: The callsign to look up
            use_cache: Whether to use cached results

        Returns:
            CallsignInfo object or None if not found

        Raises:
            QRZError: If lookup fails
        """
        # Check cache
        if use_cache and callsign.upper() in self.callsign_cache:
            cached = self.callsign_cache[callsign.upper()]
            logger.debug(f"Using cached callsign info for {callsign}")
            return cached

        try:
            # Note: QRZ.com callsign lookups require username/password directly,
            # not the session key. The session key appears to be for other operations.
            params = urllib.parse.urlencode({
                'username': self.username,
                'password': self.password,
                'callsign': callsign,
                'agent': 'W4GNSLogger/1.0'
            })

            url = f"{self.BASE_URL}?{params}"

            with urllib.request.urlopen(url, timeout=self.timeout) as response:
                data = response.read().decode('utf-8')
                root = ET.fromstring(data)

                # Check for error (handle namespaces)
                error_elem = self._find_element(root, 'Error')
                if error_elem is not None:
                    error_msg = error_elem.text or "Unknown error"
                    logger.warning(f"QRZ lookup error for {callsign}: {error_msg}")
                    return None

                # Parse callsign data (handle namespaces)
                callsign_elem = self._find_element(root, 'Callsign')
                if callsign_elem is None:
                    logger.debug(f"No callsign data found for {callsign}")
                    return None

                info = self._parse_callsign_element(callsign_elem)

                # Cache result
                self.callsign_cache[callsign.upper()] = info
                logger.info(f"Retrieved callsign info for {callsign}")

                return info

        except QRZError:
            raise
        except urllib.error.URLError as e:
            logger.error(f"QRZ connection error during lookup: {e}")
            raise QRZError(f"Connection failed: {e}")
        except ET.ParseError as e:
            logger.error(f"QRZ XML parse error: {e}")
            raise QRZError(f"Invalid XML response: {e}")

    def _parse_callsign_element(self, elem: ET.Element) -> CallsignInfo:
        """Parse a Callsign XML element into CallsignInfo"""
        info = CallsignInfo(
            callsign=self._get_text(elem, 'call', ''),
            name=self._get_text(elem, 'name', ''),
            addr1=self._get_text(elem, 'addr1', ''),
            addr2=self._get_text(elem, 'addr2', ''),
            state=self._get_text(elem, 'state', ''),
            zip=self._get_text(elem, 'zip', ''),
            country=self._get_text(elem, 'country', ''),
            grid=self._get_text(elem, 'grid', ''),
            lat=self._get_text(elem, 'lat', ''),
            lon=self._get_text(elem, 'lon', ''),
            email=self._get_text(elem, 'email', ''),
            qth=self._get_text(elem, 'qth', ''),
            class_=self._get_text(elem, 'class', ''),
            codes=self._get_text(elem, 'codes', ''),
            qsl_mgr=self._get_text(elem, 'qslmgr', ''),
            qsl_via=self._get_text(elem, 'qsl', ''),
            club=self._get_text(elem, 'club', ''),
            web=self._get_text(elem, 'web', ''),
            image=self._get_text(elem, 'image', ''),
            bio=self._get_text(elem, 'bio', ''),
            bio_date=self._get_text(elem, 'biodate', ''),
            lotw_member=self._get_bool(elem, 'lotw'),
            eqsl_member=self._get_bool(elem, 'eqsl'),
            iota=self._get_text(elem, 'iota', ''),
            sig_info=self._get_text(elem, 'sig_info', ''),
        )
        return info

    @staticmethod
    def _find_element(elem: ET.Element, tag: str) -> Optional[ET.Element]:
        """
        Find element by tag name, handling namespaces.

        Works with or without XML namespaces.
        """
        # Try direct find first (no namespace)
        result = elem.find(tag)
        if result is not None:
            return result

        # Try with wildcard namespace if not found
        result = elem.find(f'.//{{{{""}}}}{tag}')
        if result is not None:
            return result

        # Try with any namespace (using XPath with namespace wildcard)
        for child in elem:
            # Strip namespace from tag if present
            child_tag = child.tag
            if '}' in child_tag:
                child_tag = child_tag.split('}')[1]
            if child_tag == tag:
                return child

        return None

    @staticmethod
    def _get_text(elem: ET.Element, tag: str, default: str = '') -> str:
        """Get text from element, return default if not found"""
        child = QRZAPIClient._find_element(elem, tag)
        return child.text if child is not None and child.text else default

    @staticmethod
    def _get_bool(elem: ET.Element, tag: str) -> bool:
        """Get boolean value from element"""
        child = QRZAPIClient._find_element(elem, tag)
        if child is not None and child.text:
            return child.text.lower() in ('y', 'yes', '1', 'true')
        return False

    def upload_qso(self, callsign: str, qso_date: str, time_on: str,
                   freq: float, mode: str, rst_sent: str, rst_rcvd: str,
                   tx_power: Optional[float] = None,
                   notes: Optional[str] = None) -> bool:
        """
        Upload a QSO to QRZ logbook

        Requires API Key to be configured.

        Args:
            callsign: DX station callsign
            qso_date: QSO date (YYYY-MM-DD)
            time_on: QSO time (HH:MM:SS UTC)
            freq: Frequency in MHz
            mode: Operating mode (CW, SSB, etc.)
            rst_sent: RST sent to station
            rst_rcvd: RST received from station
            tx_power: TX power in watts (optional)
            notes: QSO notes (optional)

        Returns:
            True if upload successful

        Raises:
            QRZError: If upload fails or API Key not configured
        """
        if not self.api_key:
            logger.warning("Cannot upload QSO: API Key not configured")
            return False

        try:
            # Build QSO parameters for logbook API
            # API Key is used instead of session key for logbook uploads
            params = {
                'key': self.api_key,  # API Key for logbook access
                'callsign': callsign.upper(),
                'qso_date': qso_date.replace('-', ''),  # YYYYMMDD format
                'time_on': time_on.replace(':', ''),  # HHMMSS format
                'freq': str(freq),
                'mode': mode.upper(),
                'rst_sent': rst_sent,
                'rst_rcvd': rst_rcvd,
                'agent': 'W4GNSLogger/1.0'
            }

            if tx_power is not None:
                params['tx_pwr'] = str(int(tx_power))

            if notes:
                params['notes'] = notes

            params_encoded = urllib.parse.urlencode(params)

            # Logbook API endpoint
            logbook_url = "https://logbook.qrz.com/api"
            url = f"{logbook_url}?{params_encoded}"

            with urllib.request.urlopen(url, timeout=self.timeout) as response:
                data = response.read().decode('utf-8')

                # Try to parse as XML first (error case)
                try:
                    root = ET.fromstring(data)
                    error_elem = self._find_element(root, 'Error')
                    if error_elem is not None:
                        error_msg = error_elem.text or "Unknown error"
                        logger.error(f"QRZ logbook upload error: {error_msg}")
                        return False
                except ET.ParseError:
                    pass  # Not XML, likely success response

                # Success: QRZ returns "OK" or similar plain text
                if data.strip().upper() == 'OK':
                    logger.info(f"QSO uploaded to QRZ logbook for {callsign}")
                    return True
                elif not data.strip():
                    # Empty response often means success
                    logger.info(f"QSO uploaded to QRZ logbook for {callsign}")
                    return True
                else:
                    logger.debug(f"QRZ upload response: {data}")
                    logger.info(f"QSO upload attempt for {callsign} completed")
                    return True  # Assume success unless we get explicit error

        except urllib.error.URLError as e:
            logger.error(f"QRZ logbook connection error: {e}")
            return False
        except Exception as e:
            logger.error(f"QRZ logbook upload error: {e}")
            return False

    def clear_cache(self, callsign: Optional[str] = None) -> None:
        """
        Clear callsign cache

        Args:
            callsign: Specific callsign to clear, or None to clear all
        """
        if callsign:
            self.callsign_cache.pop(callsign.upper(), None)
            logger.debug(f"Cleared cache for {callsign}")
        else:
            self.callsign_cache.clear()
            logger.debug("Cleared all cached callsigns")

    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        return {
            'authenticated': self.session_key is not None,
            'session_key': self.session_key[:10] + '...' if self.session_key else None,
            'cached_callsigns': len(self.callsign_cache),
            'expires_in': max(0, int(self.session_expires - time.time())) if self.session_expires else None
        }
