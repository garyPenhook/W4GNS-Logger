"""
Configuration Management Module

Handles loading, saving, and managing application settings.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages application configuration"""

    DEFAULT_CONFIG = {
        "general": {
            "operator_callsign": "MYCALL",
            "home_grid": "FN20qd",
            "default_mode": "SSB",
            "default_power": 100,
            "auto_save_interval": 60,
        },
        "database": {
            "location": str(Path.home() / ".w4gns_logger" / "contacts.db"),
            "backup_enabled": True,
            "backup_interval": 24,  # hours
            "backup_destination": "",  # Path to backup destination (USB drive, external drive, etc.)
            "auto_backup_on_shutdown": True,  # Automatically backup when application closes
        },
        "adif": {
            "my_skcc_number": "",  # Operator's SKCC number (e.g., "14276T")
            "export_default_format": "adi",  # "adi" or "adx"
            "import_conflict_strategy": "skip",  # "skip", "update", or "append"
            "include_all_fields": True,  # Export all fields or minimal set
        },
        "dx_cluster": {
            "enabled": True,
            "auto_connect": False,
            "heartbeat_interval": 60,  # seconds
        },
        "qrz": {
            "enabled": False,
            "username": "",  # QRZ.com username (for callsign lookups)
            "password": "",  # QRZ.com password (for callsign lookups)
            "api_key": "",  # QRZ.com API Key (for logbook uploads)
            "auto_upload": False,  # Auto-upload contacts to QRZ logbook
            "auto_fetch": False,  # Auto-fetch callsign info from QRZ
        },
        "awards": {
            "enabled": True,
            "auto_calculate": True,
        },
        "skcc": {
            "spots_enabled": False,  # Enable SKCC member spot monitoring
            "auto_start_spots": False,  # Auto-start monitoring on launch
            "unworked_only": False,  # Show unworked stations only
            "min_signal_strength": 0,  # dB
            "max_spot_age_seconds": 300,  # seconds
        },
        "ui": {
            "theme": "light",
            "font_size": 10,
            "window_geometry": None,
        },
    }

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize ConfigManager

        Args:
            config_dir: Directory for configuration files. Defaults to ~/.w4gns_logger
        """
        if config_dir is None:
            config_dir = Path.home() / ".w4gns_logger"

        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "config.yaml"
        self.settings: Dict[str, Any] = {}

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load configuration
        self.load()

    def load(self) -> None:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    self.settings = yaml.safe_load(f) or {}
                logger.info(f"Loaded configuration from {self.config_file}")
            except FileNotFoundError as e:
                logger.error(f"Config file not found: {e}. Using defaults.")
                self.settings = self.DEFAULT_CONFIG.copy()
            except PermissionError as e:
                logger.error(f"Permission denied reading config: {e}. Using defaults.")
                self.settings = self.DEFAULT_CONFIG.copy()
            except yaml.YAMLError as e:
                logger.error(f"Invalid YAML in config file: {e}. Using defaults.")
                self.settings = self.DEFAULT_CONFIG.copy()
            except IOError as e:
                logger.error(f"IO error reading config: {e}. Using defaults.")
                self.settings = self.DEFAULT_CONFIG.copy()
            except Exception as e:
                logger.error(f"Unexpected error loading config: {e}. Using defaults.", exc_info=True)
                self.settings = self.DEFAULT_CONFIG.copy()
        else:
            logger.info("No config file found. Using defaults.")
            self.settings = self.DEFAULT_CONFIG.copy()
            try:
                self.save()
            except Exception as save_error:
                logger.warning(f"Could not save default config: {save_error}")

    def save(self) -> None:
        """Save current configuration to file"""
        try:
            with open(self.config_file, "w") as f:
                yaml.dump(self.settings, f, default_flow_style=False)
            logger.info(f"Configuration saved to {self.config_file}")
        except PermissionError as e:
            logger.error(f"Permission denied writing config: {e}")
            raise
        except IOError as e:
            logger.error(f"IO error saving config: {e}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"YAML error writing config: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving config: {e}", exc_info=True)
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key

        Args:
            key: Dot-notation key (e.g., "database.location")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self.settings
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value by dot-notation key

        Args:
            key: Dot-notation key (e.g., "database.location")
            value: Value to set
        """
        keys = key.split(".")
        current = self.settings

        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value
        self.save()

    def to_dict(self) -> Dict[str, Any]:
        """Return settings as dictionary"""
        return self.settings.copy()


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get or create global config manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def load_config() -> Dict[str, Any]:
    """Load configuration and return as dictionary"""
    return get_config_manager().to_dict()
