"""
Application-wide signals for event-driven UI updates.

This module provides a centralized signal system to replace polling timers,
allowing UI components to subscribe to data change events.
"""

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from typing import Set


class AppSignals(QObject):
    """Application-wide signals for data change events"""

    # OPTIMIZED: Single batched contact signal with metadata
    # Reduces 28 refresh calls down to 14 per contact change
    contacts_batch_changed = pyqtSignal(str, dict)  # (change_type, metadata)

    # Legacy signals (kept for backward compatibility, but deprecated)
    contact_added = pyqtSignal()  # DEPRECATED: Use contacts_batch_changed instead
    contact_modified = pyqtSignal()  # DEPRECATED: Use contacts_batch_changed instead
    contact_deleted = pyqtSignal()  # DEPRECATED: Use contacts_batch_changed instead
    contacts_changed = pyqtSignal()  # DEPRECATED: Use contacts_batch_changed instead

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

        # Debouncing mechanism for bulk operations
        self._pending_changes: Set[str] = set()
        self._debounce_timer = QTimer()
        self._debounce_timer.timeout.connect(self._flush_pending_changes)
        self._debounce_timer.setSingleShot(True)
        self._debounce_delay_ms = 50  # 50ms debounce window

    def emit_contact_change(self, change_type: str, metadata: dict = None, debounce: bool = False):
        """
        Emit a batched contact change signal with optional debouncing.

        Args:
            change_type: Type of change ('added', 'modified', 'deleted', 'bulk_import')
            metadata: Optional metadata about the change (callsign, band, mode, etc.)
            debounce: If True, batch multiple rapid changes into one signal (for bulk operations)
        """
        if metadata is None:
            metadata = {}

        if debounce:
            # Queue the change for batched emission
            self._pending_changes.add(change_type)
            # Start/restart the debounce timer
            self._debounce_timer.start(self._debounce_delay_ms)
        else:
            # Emit immediately
            self.contacts_batch_changed.emit(change_type, metadata)

            # Also emit legacy signals for backward compatibility
            if change_type == 'added':
                self.contact_added.emit()
                self.contacts_changed.emit()
            elif change_type == 'modified':
                self.contact_modified.emit()
                self.contacts_changed.emit()
            elif change_type == 'deleted':
                self.contact_deleted.emit()
                self.contacts_changed.emit()

    def _flush_pending_changes(self):
        """Flush all pending debounced changes as a single batched signal"""
        if self._pending_changes:
            # Emit a single 'bulk' signal instead of individual ones
            change_types = ','.join(sorted(self._pending_changes))
            self.contacts_batch_changed.emit('bulk', {'types': change_types, 'count': len(self._pending_changes)})
            self.contacts_changed.emit()  # Legacy signal
            self._pending_changes.clear()


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
