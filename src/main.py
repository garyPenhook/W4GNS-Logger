#!/usr/bin/env python3
"""
W4GNS SKCC Logger - Main Application Entry Point

A comprehensive SKCC-focused ham radio contact logging application with support for:
- ADIF import/export
- Award tracking (SKCC, DXCC, WAS, etc.)
- DX Cluster integration
- QRZ.com synchronization
- Cross-platform GUI (PyQt6)
"""

# pyright: disable=reportUnknownParameterType, reportUnknownArgumentType

import sys
import logging
import os
import signal
import types
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src directory to path
src_path = Path(__file__).parent.absolute()
sys.path.insert(0, str(src_path.parent))

# Set Qt platform plugin if not already set
# Default to xcb, but allow override via environment variable
if not os.environ.get('QT_QPA_PLATFORM'):
    os.environ['QT_QPA_PLATFORM'] = 'xcb'

from src.ui.main_window import MainWindow
from src.ui.theme_manager import ThemeManager
from src.config.settings import load_config
from PyQt6.QtWidgets import QApplication


# Global reference to app for signal handler
_app = None


def signal_handler(signum: int, frame: Optional[types.FrameType]) -> None:  # type: ignore[no-untyped-def]
    """
    Handle system signals for graceful shutdown

    Handles:
    - SIGINT (Ctrl+C)
    - SIGTERM (kill signal)

    Args:
        signum: Signal number received
        frame: Current stack frame (unused but required by signal handler signature)
    """
    global _app
    try:
        sig_name = signal.Signals(signum).name
    except ValueError:
        sig_name = f"UNKNOWN({signum})"
    logger.info(f"Received signal {sig_name} ({signum}), shutting down gracefully...")

    if _app:
        _app.quit()
    else:
        sys.exit(0)


def main():
    """Main application entry point with signal handling for graceful shutdown"""
    global _app

    try:
        # Load configuration
        config = load_config()
        logger.info(f"Configuration loaded: {config}")

        # Create Qt application
        app = QApplication(sys.argv)
        _app = app  # Store for signal handler access
        app.setApplicationName("W4GNS SKCC Logger")
        app.setApplicationVersion("1.0.0")

        # Apply stored theme
        theme = config.get("ui", {}).get("theme", "light")
        ThemeManager.apply_theme(app, theme)
        logger.info(f"Applied {theme} theme on startup")

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)   # type: ignore # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # type: ignore # Kill signal
        logger.debug("Signal handlers registered for graceful shutdown (SIGINT, SIGTERM)")

        # Create and show main window
        main_window = MainWindow(config)
        main_window.show()

        logger.info("Application started successfully")
        # Run application
        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

