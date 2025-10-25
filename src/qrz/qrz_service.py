"""
QRZ Service Manager

High-level interface for QRZ.com operations integrated with application settings.
"""

import logging
import threading
from typing import Optional, Callable, Any
from src.config.settings import get_config_manager
from src.qrz.qrz_api import QRZAPIClient, QRZError, CallsignInfo

logger = logging.getLogger(__name__)


class QRZService:
    """Service for managing QRZ.com operations"""

    def __init__(self):
        """Initialize QRZ service"""
        self.config_manager = get_config_manager()
        self.api_client: Optional[QRZAPIClient] = None
        self.authenticated = False
        self._lock = threading.Lock()

    def is_enabled(self) -> bool:
        """Check if QRZ integration is enabled"""
        return self.config_manager.get("qrz.enabled", False)

    def initialize(self) -> bool:
        """
        Initialize QRZ API client with credentials from config

        Returns:
            True if initialization successful
        """
        if not self.is_enabled():
            logger.debug("QRZ integration is disabled")
            return False

        username = self.config_manager.get("qrz.username", "")
        password = self.config_manager.get("qrz.password", "")
        api_key = self.config_manager.get("qrz.api_key", "")

        if not username or not password:
            logger.warning("QRZ callsign lookup credentials not configured")
            return False

        try:
            # API key is optional - only needed for logbook uploads
            self.api_client = QRZAPIClient(username, password, api_key)
            logger.debug(f"QRZ client initialized with callsign lookup credentials{' and logbook API key' if api_key else ''}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize QRZ client: {e}")
            return False

    def authenticate(self) -> bool:
        """
        Authenticate with QRZ.com

        Returns:
            True if authentication successful
        """
        if self.api_client is None:
            if not self.initialize():
                return False

        try:
            with self._lock:
                self.api_client.authenticate()
                self.authenticated = True
                logger.info("QRZ authentication successful")
                return True
        except QRZError as e:
            logger.error(f"QRZ authentication failed: {e}")
            self.authenticated = False
            return False

    def lookup_callsign(self, callsign: str) -> Optional[CallsignInfo]:
        """
        Look up a callsign

        Args:
            callsign: The callsign to look up

        Returns:
            CallsignInfo or None if not found
        """
        if not self.authenticated:
            if not self.authenticate():
                return None

        try:
            with self._lock:
                return self.api_client.lookup_callsign(callsign)
        except QRZError as e:
            logger.error(f"Callsign lookup failed: {e}")
            return None

    def lookup_callsign_async(self, callsign: str, callback: Callable[[Optional[CallsignInfo]], None]) -> None:
        """
        Look up a callsign asynchronously

        Args:
            callsign: The callsign to look up
            callback: Function to call with result (runs in separate thread)
        """
        def _lookup():
            result = self.lookup_callsign(callsign)
            callback(result)

        thread = threading.Thread(target=_lookup, daemon=True)
        thread.start()

    def upload_qso(self, callsign: str, qso_date: str, time_on: str,
                   freq: float, mode: str, rst_sent: str, rst_rcvd: str,
                   tx_power: Optional[float] = None,
                   notes: Optional[str] = None) -> bool:
        """
        Upload a QSO to QRZ logbook

        Args:
            callsign: DX station callsign
            qso_date: QSO date (YYYY-MM-DD)
            time_on: QSO time (HH:MM:SS UTC)
            freq: Frequency in MHz
            mode: Operating mode
            rst_sent: RST sent
            rst_rcvd: RST received
            tx_power: TX power in watts
            notes: QSO notes

        Returns:
            True if upload successful
        """
        if not self.is_enabled() or not self.config_manager.get("qrz.auto_upload", False):
            return False

        if not self.authenticated:
            if not self.authenticate():
                return False

        try:
            with self._lock:
                return self.api_client.upload_qso(
                    callsign, qso_date, time_on, freq, mode,
                    rst_sent, rst_rcvd, tx_power, notes
                )
        except QRZError as e:
            logger.error(f"QSO upload failed: {e}")
            return False

    def upload_qso_async(self, callsign: str, qso_date: str, time_on: str,
                        freq: float, mode: str, rst_sent: str, rst_rcvd: str,
                        tx_power: Optional[float] = None,
                        notes: Optional[str] = None,
                        callback: Optional[Callable[[bool], None]] = None) -> None:
        """
        Upload a QSO asynchronously

        Args:
            callsign: DX station callsign
            qso_date: QSO date (YYYY-MM-DD)
            time_on: QSO time (HH:MM:SS UTC)
            freq: Frequency in MHz
            mode: Operating mode
            rst_sent: RST sent
            rst_rcvd: RST received
            tx_power: TX power in watts
            notes: QSO notes
            callback: Function to call with result (bool)
        """
        def _upload():
            result = self.upload_qso(
                callsign, qso_date, time_on, freq, mode,
                rst_sent, rst_rcvd, tx_power, notes
            )
            if callback:
                callback(result)

        thread = threading.Thread(target=_upload, daemon=True)
        thread.start()

    def get_status(self) -> dict:
        """Get QRZ service status"""
        if self.api_client is None:
            return {
                'enabled': self.is_enabled(),
                'authenticated': False,
                'status': 'Not initialized'
            }

        return {
            'enabled': self.is_enabled(),
            'authenticated': self.authenticated,
            'status': 'Ready' if self.authenticated else 'Not authenticated',
            'session_info': self.api_client.get_session_info() if self.authenticated else None
        }

    def clear_cache(self, callsign: Optional[str] = None) -> None:
        """Clear callsign cache"""
        if self.api_client:
            self.api_client.clear_cache(callsign)


# Global service instance
_qrz_service: Optional[QRZService] = None


def get_qrz_service() -> QRZService:
    """Get or create global QRZ service instance"""
    global _qrz_service
    if _qrz_service is None:
        _qrz_service = QRZService()
    return _qrz_service
