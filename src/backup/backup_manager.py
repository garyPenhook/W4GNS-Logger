"""
Backup manager for database and ADIF file backups

Handles backing up the W4GNS SKCC Logger database and ADIF exports to a user-selected
location (e.g., USB drive, external hard drive, cloud storage).
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, List

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
            try:
                shutil.copy2(database_path, db_backup_path)
                logger.info(f"Database backed up to: {db_backup_path}")
            except FileNotFoundError as e:
                logger.error(f"Database file not found during backup: {e}")
                raise
            except PermissionError as e:
                logger.error(f"Permission denied reading database: {e}")
                raise
            except IOError as e:
                logger.error(f"IO error during database backup: {e}")
                raise

            # Find and backup most recent ADIF file
            adif_backup_path = None
            most_recent_adif = self._find_most_recent_adif(adif_directory)

            if most_recent_adif:
                adif_backup_path = backup_dir / most_recent_adif.name
                try:
                    shutil.copy2(most_recent_adif, adif_backup_path)
                    logger.info(f"ADIF file backed up to: {adif_backup_path}")
                except FileNotFoundError as e:
                    logger.error(f"ADIF file not found during backup: {e}")
                    # Continue - ADIF backup is optional
                except PermissionError as e:
                    logger.error(f"Permission denied reading ADIF file: {e}")
                    # Continue - ADIF backup is optional
                except IOError as e:
                    logger.error(f"IO error during ADIF backup: {e}")
                    # Continue - ADIF backup is optional
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
            try:
                adif_files = list(adif_directory.glob("*.adif")) + list(
                    adif_directory.glob("*.adi")
                )
            except (OSError, PermissionError) as e:
                logger.warning(f"Cannot access ADIF directory {adif_directory}: {e}")
                return None

            if not adif_files:
                logger.warning(f"No ADIF files found in {adif_directory}")
                return None

            # Return most recently modified
            try:
                most_recent = max(adif_files, key=lambda p: p.stat().st_mtime)
                logger.debug(f"Found most recent ADIF file: {most_recent}")
                return most_recent
            except (OSError, ValueError) as e:
                logger.warning(f"Error determining most recent ADIF file: {e}")
                return None

        except Exception as e:
            logger.warning(f"Unexpected error finding ADIF file: {e}", exc_info=True)
            return None

    def create_adif_backup(
        self,
        contacts: List[Any],
        my_skcc: Optional[str] = None,
        backup_location: Optional[Path] = None,
        max_backups: int = 5
    ) -> Dict[str, Any]:
        """
        Create timestamped ADIF backup and rotate old backups

        Args:
            contacts: List of Contact objects to export
            my_skcc: Operator's SKCC number (optional)
            backup_location: Directory to store backups (default: ~/.w4gns_logger/Logs)
            max_backups: Maximum number of backup files to keep (default: 5)

        Returns:
            Dictionary with:
            - success: True if backup created successfully
            - backup_file: Path to created backup file
            - total_backups: Number of backup files after cleanup
            - message: Human-readable status message

        Raises:
            ValueError: If contacts list is empty
            OSError: If file operations fail
        """
        try:
            if not contacts:
                raise ValueError("No contacts to export")

            # Use default location if not specified
            if backup_location is None:
                # Default to project root logs directory
                project_root = Path(__file__).parent.parent.parent
                backup_location = project_root / "logs"

            # Ensure directory exists
            backup_location.mkdir(parents=True, exist_ok=True)
            logger.info(f"Using backup location: {backup_location}")

            # Create timestamped filename
            # Add counter suffix if file already exists (in case of rapid backups in same second)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_location / f"{timestamp}.adi"

            # Handle filename collision by adding counter
            counter = 1
            base_name = timestamp
            while backup_file.exists():
                backup_file = backup_location / f"{base_name}_{counter}.adi"
                counter += 1

            # Import ADIF exporter
            try:
                from src.adif.exporter import ADIFExporter
            except ImportError:
                logger.error("Failed to import ADIFExporter")
                raise

            # Export contacts to ADIF
            try:
                exporter = ADIFExporter()
                exporter.export_to_file(
                    filename=str(backup_file),
                    contacts=contacts,
                    my_skcc=my_skcc,
                    include_fields=None  # Export all non-empty fields
                )
                logger.info(f"Created ADIF backup: {backup_file}")
            except Exception as e:
                logger.error(f"Failed to export ADIF file: {e}", exc_info=True)
                raise

            # Rotate old backups - keep only the most recent N files
            try:
                self._rotate_backups(backup_location, max_backups)
            except Exception as e:
                logger.warning(f"Error rotating old backups: {e}", exc_info=True)
                # Don't fail the entire backup if rotation fails

            # Count remaining backups
            remaining_backups = len(list(backup_location.glob("*.adi")))

            message = f"ADIF backup created: {backup_file.name} ({remaining_backups} total backups)"

            return {
                "success": True,
                "backup_file": backup_file,
                "total_backups": remaining_backups,
                "message": message
            }

        except Exception as e:
            logger.error(f"ADIF backup failed: {e}", exc_info=True)
            return {
                "success": False,
                "backup_file": None,
                "total_backups": 0,
                "message": f"ADIF backup failed: {str(e)}"
            }

    def create_database_backup(
        self,
        database_path: Path,
        backup_location: Optional[Path] = None,
        max_backups: int = 5
    ) -> Dict[str, Any]:
        """
        Create timestamped database backup and rotate old backups

        Args:
            database_path: Path to the contacts.db file
            backup_location: Directory to store backups (default: ~/.w4gns_logger/Logs)
            max_backups: Maximum number of backup files to keep (default: 5)

        Returns:
            Dictionary with:
            - success: True if backup created successfully
            - backup_file: Path to created backup file
            - total_backups: Number of backup files after cleanup
            - message: Human-readable status message

        Raises:
            ValueError: If database_path doesn't exist
            OSError: If file operations fail
        """
        try:
            database_path = Path(database_path)

            if not database_path.exists():
                raise ValueError(f"Database file not found: {database_path}")

            # Use default location if not specified
            if backup_location is None:
                # Default to project root logs directory
                project_root = Path(__file__).parent.parent.parent
                backup_location = project_root / "logs"

            # Ensure directory exists
            backup_location.mkdir(parents=True, exist_ok=True)
            logger.info(f"Creating database backup in: {backup_location}")

            # Create timestamped filename (contacts_YYYYMMDD_HHMMSS.db)
            # Add counter suffix if file already exists (in case of rapid backups in same second)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_location / f"contacts_{timestamp}.db"

            # Handle filename collision by adding counter
            counter = 1
            base_name = f"contacts_{timestamp}"
            while backup_file.exists():
                backup_file = backup_location / f"{base_name}_{counter}.db"
                counter += 1

            # Copy database file
            try:
                shutil.copy2(database_path, backup_file)
                logger.info(f"Created database backup: {backup_file}")
            except FileNotFoundError as e:
                logger.error(f"Database file not found during backup: {e}")
                raise
            except PermissionError as e:
                logger.error(f"Permission denied reading database: {e}")
                raise
            except IOError as e:
                logger.error(f"IO error during database backup: {e}")
                raise

            # Rotate old backups - keep only the most recent N files
            try:
                self._rotate_db_backups(backup_location, max_backups)
            except Exception as e:
                logger.warning(f"Error rotating old database backups: {e}", exc_info=True)
                # Don't fail the entire backup if rotation fails

            # Count remaining backups
            remaining_backups = len(list(backup_location.glob("contacts_*.db")))

            message = f"Database backup created: {backup_file.name} ({remaining_backups} total backups)"

            return {
                "success": True,
                "backup_file": backup_file,
                "total_backups": remaining_backups,
                "message": message
            }

        except Exception as e:
            logger.error(f"Database backup failed: {e}", exc_info=True)
            return {
                "success": False,
                "backup_file": None,
                "total_backups": 0,
                "message": f"Database backup failed: {str(e)}"
            }

    def backup_adif_to_secondary(
        self,
        adif_source_dir: Optional[Path] = None,
        backup_destination: Optional[Path] = None,
        max_backups: int = 5
    ) -> Dict[str, Any]:
        """
        Backup most recent ADIF file to secondary location (USB/external drive)

        Args:
            adif_source_dir: Directory containing ADIF backups (default: ~/.w4gns_logger/Logs)
            backup_destination: Secondary backup destination directory
            max_backups: Maximum number of backup files to keep at destination

        Returns:
            Dictionary with:
            - success: True if backup created successfully
            - backup_file: Path to created backup file
            - total_backups: Number of backup files after cleanup
            - message: Human-readable status message
        """
        try:
            # Use default ADIF source location if not specified
            if adif_source_dir is None:
                adif_source_dir = Path.home() / ".w4gns_logger" / "Logs"

            if not backup_destination:
                raise ValueError("Backup destination is required")

            backup_destination = Path(backup_destination)

            if not backup_destination.exists():
                raise ValueError(f"Backup destination directory not found: {backup_destination}")

            if not backup_destination.is_dir():
                raise ValueError(f"Backup destination must be a directory: {backup_destination}")

            # Find most recent ADIF file
            most_recent_adif = self._find_most_recent_adif(adif_source_dir)

            if not most_recent_adif:
                logger.warning(f"No ADIF files found in {adif_source_dir} to backup to secondary location")
                return {
                    "success": False,
                    "backup_file": None,
                    "total_backups": 0,
                    "message": "No ADIF files found to backup to secondary location"
                }

            # Create timestamped filename at destination
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_destination / f"{timestamp}.adi"

            # Handle filename collision by adding counter
            counter = 1
            base_name = timestamp
            while backup_file.exists():
                backup_file = backup_destination / f"{base_name}_{counter}.adi"
                counter += 1

            # Copy ADIF file to secondary location
            try:
                shutil.copy2(most_recent_adif, backup_file)
                logger.info(f"ADIF backup copied to secondary location: {backup_file}")
            except Exception as e:
                logger.error(f"Failed to copy ADIF to secondary location: {e}", exc_info=True)
                raise

            # Rotate old ADIF backups at secondary location
            try:
                self._rotate_backups(backup_destination, max_backups)
            except Exception as e:
                logger.warning(f"Error rotating old ADIF backups at secondary location: {e}", exc_info=True)
                # Don't fail the entire backup if rotation fails

            # Count remaining backups
            remaining_backups = len(list(backup_destination.glob("*.adi")))

            message = f"ADIF backup to secondary location: {backup_file.name} ({remaining_backups} total backups)"

            return {
                "success": True,
                "backup_file": backup_file,
                "total_backups": remaining_backups,
                "message": message
            }

        except Exception as e:
            logger.error(f"ADIF backup to secondary location failed: {e}", exc_info=True)
            return {
                "success": False,
                "backup_file": None,
                "total_backups": 0,
                "message": f"ADIF backup to secondary location failed: {str(e)}"
            }

    def _rotate_db_backups(self, backup_location: Path, max_backups: int = 5) -> None:
        """
        Remove old database backup files, keeping only the most recent N files

        Args:
            backup_location: Directory containing backup files
            max_backups: Maximum number of files to keep

        Raises:
            OSError: If file deletion fails
        """
        try:
            # Get all contacts_*.db files sorted by modification time (newest first)
            db_files = sorted(
                backup_location.glob("contacts_*.db"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            # Remove files beyond the max_backups limit
            if len(db_files) > max_backups:
                files_to_remove = db_files[max_backups:]
                for old_file in files_to_remove:
                    try:
                        old_file.unlink()
                        logger.info(f"Removed old database backup: {old_file.name}")
                    except OSError as e:
                        logger.warning(f"Failed to remove old database backup {old_file}: {e}")
                        # Continue with other files even if one fails

                logger.info(f"Database backup rotation completed: Kept {min(len(db_files), max_backups)} recent backups")
            else:
                logger.debug(f"No database backup rotation needed: {len(db_files)} files <= {max_backups} limit")

        except Exception as e:
            logger.error(f"Error during database backup rotation: {e}", exc_info=True)
            raise

    def _rotate_backups(self, backup_location: Path, max_backups: int = 5) -> None:
        """
        Remove old backup files, keeping only the most recent N files

        Args:
            backup_location: Directory containing backup files
            max_backups: Maximum number of files to keep

        Raises:
            OSError: If file deletion fails
        """
        try:
            # Get all .adi files sorted by modification time (newest first)
            adi_files = sorted(
                backup_location.glob("*.adi"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            # Remove files beyond the max_backups limit
            if len(adi_files) > max_backups:
                files_to_remove = adi_files[max_backups:]
                for old_file in files_to_remove:
                    try:
                        old_file.unlink()
                        logger.info(f"Removed old backup: {old_file.name}")
                    except OSError as e:
                        logger.warning(f"Failed to remove old backup {old_file}: {e}")
                        # Continue with other files even if one fails

                logger.info(f"Backup rotation completed: Kept {min(len(adi_files), max_backups)} recent backups")
            else:
                logger.debug(f"No backup rotation needed: {len(adi_files)} files <= {max_backups} limit")

        except Exception as e:
            logger.error(f"Error during backup rotation: {e}", exc_info=True)
            raise
