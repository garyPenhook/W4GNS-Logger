"""
Application-wide signals for event-driven UI updates.

This module provides a centralized signal system to replace polling timers,
allowing UI components to subscribe to data change events.
"""

from PyQt6.QtCore import QObject, pyqtSignal


class AppSignals(QObject):
    """Application-wide signals for data change events"""

    # Contact-related signals
    contact_added = pyqtSignal()  # New contact added to database
    contact_modified = pyqtSignal()  # Existing contact modified
    contact_deleted = pyqtSignal()  # Contact deleted from database
    contacts_changed = pyqtSignal()  # Generic contact data change signal

    # Award-related signals
    centurion_progress_updated = pyqtSignal()  # Centurion award progress changed
    tribune_progress_updated = pyqtSignal()  # Tribune award progress changed
    senator_progress_updated = pyqtSignal()  # Senator award progress changed
    award_progress_updated = pyqtSignal()  # Generic award progress change

    # QRP and power statistics signals
    qrp_progress_updated = pyqtSignal()  # QRP award progress changed
    power_statistics_updated = pyqtSignal()  # Power statistics changed

    # Cluster spot signals
    cluster_spots_updated = pyqtSignal()  # New cluster spots available
    cluster_spots_added = pyqtSignal(int)  # New spots added (count)

    def __init__(self):
        """Initialize signals"""
        super().__init__()


# Global signals instance
_app_signals = None


def get_app_signals() -> AppSignals:
    """
    Get the global app signals instance.

    Returns:
        AppSignals: The global signals instance
    """
    global _app_signals
    if _app_signals is None:
        _app_signals = AppSignals()
    return _app_signals
