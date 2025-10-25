"""
Backup manager for database and ADIF file backups

Handles backing up the W4GNS Logger database and ADIF exports to a user-selected
location (e.g., USB drive, external hard drive, cloud storage).
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages backups of database and ADIF files"""

    def __init__(self):
        """Initialize backup manager"""
        self.backup_timestamp = None

    def backup_to_location(
        self,
        database_path: Path,
        backup_destination: Path,
        adif_directory: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Backup database and most recent ADIF file to specified location

        Args:
            database_path: Path to the contacts.db file
            backup_destination: Path to backup destination directory
            adif_directory: Optional directory to search for ADIF files (default: project_root/logs)

        Returns:
            Dictionary with:
            - success: True if backup completed successfully
            - backup_dir: Path to created backup directory
            - database_backed_up: Path to backed up database file
            - adif_backed_up: Path to backed up ADIF file (or None)
            - timestamp: Backup timestamp
            - message: Human-readable status message

        Raises:
            ValueError: If database_path doesn't exist or is invalid
            OSError: If file operations fail
        """
        try:
            # Validate inputs
            database_path = Path(database_path)
            backup_destination = Path(backup_destination)

            if not database_path.exists():
                raise ValueError(f"Database file not found: {database_path}")

            if not backup_destination.exists():
                raise ValueError(f"Backup destination directory not found: {backup_destination}")

            if not backup_destination.is_dir():
                raise ValueError(f"Backup destination must be a directory: {backup_destination}")

            # Create timestamped backup directory
            self.backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = backup_destination / f"w4gns_logger_backup_{self.backup_timestamp}"
            backup_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Creating backup in: {backup_dir}")

            # Backup database
            db_backup_path = backup_dir / database_path.name
            shutil.copy2(database_path, db_backup_path)
            logger.info(f"Database backed up to: {db_backup_path}")

            # Find and backup most recent ADIF file
            adif_backup_path = None
            most_recent_adif = self._find_most_recent_adif(adif_directory)

            if most_recent_adif:
                adif_backup_path = backup_dir / most_recent_adif.name
                shutil.copy2(most_recent_adif, adif_backup_path)
                logger.info(f"ADIF file backed up to: {adif_backup_path}")
            else:
                logger.warning("No ADIF file found for backup")

            # Build result message
            files_backed_up = ["Database"]
            if adif_backup_path:
                files_backed_up.append("ADIF export")

            message = (
                f"Backup completed successfully!\n\n"
                f"Location: {backup_dir}\n"
                f"Files backed up: {', '.join(files_backed_up)}"
            )

            return {
                "success": True,
                "backup_dir": backup_dir,
                "database_backed_up": db_backup_path,
                "adif_backed_up": adif_backup_path,
                "timestamp": self.backup_timestamp,
                "message": message
            }

        except Exception as e:
            logger.error(f"Backup failed: {e}", exc_info=True)
            return {
                "success": False,
                "backup_dir": None,
                "database_backed_up": None,
                "adif_backed_up": None,
                "timestamp": self.backup_timestamp,
                "message": f"Backup failed: {str(e)}"
            }

    def _find_most_recent_adif(self, adif_directory: Optional[Path] = None) -> Optional[Path]:
        """
        Find the most recently modified ADIF file in the specified directory

        Args:
            adif_directory: Directory to search (default: project_root/logs or ~/.w4gns_logger)

        Returns:
            Path to most recent ADIF file, or None if not found
        """
        if adif_directory is None:
            # Try project logs directory first
            project_root = Path(__file__).parent.parent.parent
            logs_dir = project_root / "logs"

            if not logs_dir.exists():
                # Try home directory
                home_logs = Path.home() / ".w4gns_logger" / "logs"
                if home_logs.exists():
                    adif_directory = home_logs
                else:
                    return None
            else:
                adif_directory = logs_dir

        try:
            # Find all ADIF files
            adif_files = list(adif_directory.glob("*.adif")) + list(
                adif_directory.glob("*.adi")
            )

            if not adif_files:
                logger.warning(f"No ADIF files found in {adif_directory}")
                return None

            # Return most recently modified
            most_recent = max(adif_files, key=lambda p: p.stat().st_mtime)
            logger.debug(f"Found most recent ADIF file: {most_recent}")
            return most_recent

        except Exception as e:
            logger.warning(f"Error finding ADIF file: {e}")
            return None
