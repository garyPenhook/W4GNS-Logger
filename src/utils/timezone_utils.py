"""
Timezone Utilities for UTC-based Ham Radio Logging

All QSO times MUST be in UTC for consistency across time zones.
This module provides utilities to ensure all logging operations use UTC.
"""

from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


def get_utc_now() -> datetime:
    """
    Get current time in UTC.

    Returns:
        datetime: Current UTC time with timezone info
    """
    return datetime.now(timezone.utc)


def get_utc_datetime(local_dt: datetime) -> datetime:
    """
    Convert a local datetime to UTC.

    Args:
        local_dt: Datetime in local timezone (assumed to be naive/no timezone)

    Returns:
        datetime: UTC datetime
    """
    if local_dt.tzinfo is None:
        # Assume local timezone
        local_dt = local_dt.replace(tzinfo=None)
        # Get local timezone aware time
        import sys
        if sys.platform == 'win32':
            from datetime import timezone as tz
            # Windows uses different timezone handling
            local_aware = local_dt.replace(tzinfo=timezone.utc)
        else:
            # Unix-like systems
            local_aware = local_dt.astimezone()
        return local_aware.astimezone(timezone.utc)
    else:
        # Already has timezone info
        return local_dt.astimezone(timezone.utc)


def datetime_to_adif_date(dt: datetime) -> str:
    """
    Convert datetime to ADIF date format (YYYYMMDD).

    All input datetimes are assumed to be in UTC.

    Args:
        dt: Datetime object (should be in UTC)

    Returns:
        str: Date in YYYYMMDD format
    """
    if dt.tzinfo is None:
        # Assume UTC if no timezone
        logger.warning(f"datetime_to_adif_date received naive datetime: {dt}. Assuming UTC.")
    return dt.strftime("%Y%m%d")


def datetime_to_adif_time(dt: datetime) -> str:
    """
    Convert datetime to ADIF time format (HHMM).

    All input datetimes are assumed to be in UTC.

    Args:
        dt: Datetime object (should be in UTC)

    Returns:
        str: Time in HHMM format
    """
    if dt.tzinfo is None:
        # Assume UTC if no timezone
        logger.warning(f"datetime_to_adif_time received naive datetime: {dt}. Assuming UTC.")
    return dt.strftime("%H%M")


def adif_date_time_to_utc_datetime(date_str: str, time_str: str) -> datetime:
    """
    Convert ADIF date and time strings to UTC datetime.

    Args:
        date_str: Date in YYYYMMDD format
        time_str: Time in HHMM or HHMMSS format

    Returns:
        datetime: UTC datetime object with timezone info

    Raises:
        ValueError: If date or time format is invalid
    """
    try:
        # Parse date (YYYYMMDD)
        if len(date_str) != 8 or not date_str.isdigit():
            raise ValueError(f"Invalid ADIF date format: {date_str}. Expected YYYYMMDD.")

        year = int(date_str[0:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])

        # Parse time (HHMM or HHMMSS)
        time_str = time_str.strip()
        if len(time_str) == 4:  # HHMM
            hour = int(time_str[0:2])
            minute = int(time_str[2:4])
            second = 0
        elif len(time_str) == 6:  # HHMMSS
            hour = int(time_str[0:2])
            minute = int(time_str[2:4])
            second = int(time_str[4:6])
        else:
            raise ValueError(f"Invalid ADIF time format: {time_str}. Expected HHMM or HHMMSS.")

        # Create UTC datetime
        dt = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
        return dt

    except (ValueError, IndexError) as e:
        logger.error(f"Error converting ADIF date/time to datetime: {e}")
        raise ValueError(f"Invalid ADIF date/time: {date_str} {time_str}") from e


def format_utc_time_for_display(dt: datetime) -> str:
    """
    Format UTC datetime for user display.

    Shows time with explicit UTC indicator.

    Args:
        dt: Datetime object (should be in UTC)

    Returns:
        str: Formatted string like "2025-10-26 14:30 UTC"
    """
    if dt.tzinfo is None:
        logger.warning(f"format_utc_time_for_display received naive datetime: {dt}. Assuming UTC.")
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def format_utc_date_for_display(dt: datetime) -> str:
    """
    Format UTC date for user display.

    Args:
        dt: Datetime object (should be in UTC)

    Returns:
        str: Formatted string like "2025-10-26"
    """
    if dt.tzinfo is None:
        logger.warning(f"format_utc_date_for_display received naive datetime: {dt}. Assuming UTC.")
    return dt.strftime("%Y-%m-%d")


def is_utc_aware(dt: datetime) -> bool:
    """
    Check if a datetime is UTC-aware.

    Args:
        dt: Datetime to check

    Returns:
        bool: True if datetime has UTC timezone, False otherwise
    """
    return dt.tzinfo is not None and dt.tzinfo.tzname(dt) == 'UTC'
