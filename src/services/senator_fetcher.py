"""
SKCC Senator List Fetcher

Downloads the official SKCC Senator member list daily and updates the database.
The list is fetched from: https://www.skccgroup.com/senator.txt
"""

import logging
import csv
from datetime import datetime, timedelta
from io import StringIO
from typing import List, Dict, Optional
from urllib.request import urlopen
from urllib.error import URLError

from sqlalchemy.orm import Session

from src.database.models import SenatorMember

logger = logging.getLogger(__name__)

SENATOR_LIST_URL = "https://www.skccgroup.com/senator.txt"
SENATOR_LIST_CACHE_HOURS = 24  # Refresh list every 24 hours


class SenatorFetcher:
    """Fetch and manage SKCC Senator member list"""

    @staticmethod
    def fetch_senator_list() -> Optional[str]:
        """
        Fetch the Senator list from SKCC website

        Returns:
            Raw text content of the list, or None if fetch fails
        """
        try:
            logger.info(f"Fetching Senator list from {SENATOR_LIST_URL}")
            with urlopen(SENATOR_LIST_URL, timeout=10) as response:
                content = response.read().decode('utf-8')
                logger.info(f"Successfully fetched Senator list ({len(content)} bytes)")
                return content
        except URLError as e:
            logger.error(f"Failed to fetch Senator list: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching Senator list: {e}")
            return None

    @staticmethod
    def parse_senator_list(raw_content: str) -> List[Dict[str, str]]:
        """
        Parse the Senator list CSV format

        Format: senatornr|call|skccnr|name|city|state|issued|senatorendorsements

        Args:
            raw_content: Raw text content from senator.txt

        Returns:
            List of parsed member dictionaries
        """
        members = []
        try:
            lines = raw_content.strip().split('\n')

            # First line is header - skip it
            if not lines or lines[0].startswith('senatornr'):
                lines = lines[1:]

            # Parse CSV with | delimiter
            reader = csv.DictReader(
                lines,
                fieldnames=['senator_nr', 'call', 'skccnr', 'name', 'city', 'state', 'issued', 'endorsements'],
                delimiter='|'
            )

            for row in reader:
                # Skip empty rows
                if not row.get('call', '').strip():
                    continue

                # Parse rank from senator_nr (format: "1 x3", "2 x9", etc.)
                senator_nr_str = row['senator_nr'].strip()
                try:
                    rank_base = int(senator_nr_str.split()[0])
                except (ValueError, IndexError):
                    logger.warning(f"Could not parse senator_nr '{senator_nr_str}'")
                    continue

                # Normalize date from "DD Mon YYYY" to YYYYMMDD format
                senator_date_str = row['issued'].strip() if row.get('issued') else ''
                normalized_date = ''
                if senator_date_str:
                    try:
                        date_obj = datetime.strptime(senator_date_str, '%d %b %Y')
                        normalized_date = date_obj.strftime('%Y%m%d')
                    except ValueError:
                        # If parsing fails, try to keep original format
                        normalized_date = senator_date_str
                        logger.debug(f"Could not parse Senator date '{senator_date_str}' for {row['call'].strip()}")

                members.append({
                    'rank': rank_base,
                    'callsign': row['call'].strip(),
                    'skcc_number': row['skccnr'].strip(),
                    'name': row['name'].strip() if row.get('name') else '',
                    'city': row['city'].strip() if row.get('city') else '',
                    'state': row['state'].strip() if row.get('state') else '',
                    'senator_date': normalized_date,
                    'endorsements': row['endorsements'].strip() if row.get('endorsements') else ''
                })

            logger.info(f"Parsed {len(members)} Senator members")
            return members

        except Exception as e:
            logger.error(f"Error parsing Senator list: {e}")
            return []

    @staticmethod
    def update_database(db: Session, members: List[Dict[str, str]]) -> bool:
        """
        Update the database with parsed Senator members

        Args:
            db: SQLAlchemy database session
            members: List of parsed member dictionaries

        Returns:
            True if update successful, False otherwise
        """
        try:
            # Clear old list
            old_count = db.query(SenatorMember).count()
            db.query(SenatorMember).delete()
            db.commit()
            logger.info(f"Cleared {old_count} old Senator members from database")

            # Insert new members
            now = datetime.utcnow()
            for member_data in members:
                member = SenatorMember(
                    rank=member_data['rank'],
                    callsign=member_data['callsign'],
                    skcc_number=member_data['skcc_number'],
                    name=member_data['name'],
                    city=member_data['city'],
                    state=member_data['state'],
                    country='',  # Will be determined from SKCC data
                    senator_date=member_data['senator_date'],
                    endorsements=member_data['endorsements'],
                    last_list_update=now
                )
                db.add(member)

            db.commit()
            logger.info(f"Updated database with {len(members)} Senator members")
            return True

        except Exception as e:
            logger.error(f"Error updating Senator database: {e}")
            db.rollback()
            return False

    @staticmethod
    def refresh_senator_list(db: Session, force: bool = False) -> bool:
        """
        Refresh Senator list if needed (24-hour cache)

        Args:
            db: SQLAlchemy database session
            force: Force refresh even if cache is fresh

        Returns:
            True if list was refreshed or already current, False if error
        """
        try:
            # Check if we need to refresh (every 24 hours)
            last_update = db.query(SenatorMember).first()
            if last_update and not force:
                last_update_time = last_update.last_list_update
                if last_update_time:
                    hours_since = (datetime.utcnow() - last_update_time).total_seconds() / 3600
                    if hours_since < SENATOR_LIST_CACHE_HOURS:
                        logger.debug(f"Senator list cache is fresh ({hours_since:.1f} hours old)")
                        return True

            # Fetch new list
            raw_content = SenatorFetcher.fetch_senator_list()
            if not raw_content:
                logger.warning("Failed to fetch Senator list from SKCC")
                return False

            # Parse and update
            members = SenatorFetcher.parse_senator_list(raw_content)
            if not members:
                logger.warning("No Senator members parsed from list")
                return False

            success = SenatorFetcher.update_database(db, members)
            if success:
                logger.info(f"Senator list refreshed: {len(members)} members")
            return success

        except Exception as e:
            logger.error(f"Error refreshing Senator list: {e}")
            return False

    @staticmethod
    def is_senator_member(db: Session, skcc_number: str) -> bool:
        """
        Check if a given SKCC number belongs to a Senator member

        Args:
            db: SQLAlchemy database session
            skcc_number: SKCC member number to check

        Returns:
            True if member is on Senator list, False otherwise
        """
        try:
            if not skcc_number:
                return False

            # Extract base number (remove suffix and multiplier)
            base_number = skcc_number.strip().split()[0]
            if base_number and base_number[-1] in 'CTS':
                base_number = base_number[:-1]
            if base_number and 'x' in base_number:
                base_number = base_number.split('x')[0]

            # Check if this base number is in the Senator list
            member = db.query(SenatorMember).filter(
                SenatorMember.skcc_number.like(f"{base_number}%")
            ).first()

            return member is not None

        except Exception as e:
            logger.error(f"Error checking if Senator member: {e}")
            return False

    @staticmethod
    def get_senator_member_count(db: Session) -> int:
        """
        Get the total number of Senator members on record

        Args:
            db: SQLAlchemy database session

        Returns:
            Count of Senator members in database
        """
        try:
            return db.query(SenatorMember).count()
        except Exception as e:
            logger.error(f"Error getting Senator member count: {e}")
            return 0
