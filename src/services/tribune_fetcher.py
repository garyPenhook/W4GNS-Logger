"""
SKCC Tribune List Fetcher

Downloads the official SKCC Tribune member list daily and updates the database.
The list is fetched from: https://www.skccgroup.com/tribunelist.txt
"""

import logging
import csv
from datetime import datetime, timedelta
from io import StringIO
from typing import List, Dict, Optional
from urllib.request import urlopen
from urllib.error import URLError

from sqlalchemy.orm import Session

from src.database.models import TribuneeMember

logger = logging.getLogger(__name__)

TRIBUNE_LIST_URL = "https://www.skccgroup.com/tribunelist.txt"
TRIBUNE_LIST_CACHE_HOURS = 24  # Refresh list every 24 hours


class TribuneFetcher:
    """Fetch and manage SKCC Tribune member list"""

    @staticmethod
    def fetch_tribune_list() -> Optional[str]:
        """
        Fetch the Tribune list from SKCC website

        Returns:
            Raw text content of the list, or None if fetch fails
        """
        try:
            logger.info(f"Fetching Tribune list from {TRIBUNE_LIST_URL}")
            with urlopen(TRIBUNE_LIST_URL, timeout=10) as response:
                content = response.read().decode('utf-8')
                logger.info(f"Successfully fetched Tribune list ({len(content)} bytes)")
                return content
        except URLError as e:
            logger.error(f"Failed to fetch Tribune list: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching Tribune list: {e}")
            return None

    @staticmethod
    def parse_tribune_list(raw_content: str) -> List[Dict[str, str]]:
        """
        Parse the Tribune list CSV format

        Format: tnr|call|skccnr|name|city|state|tdate|tendorsements

        Args:
            raw_content: Raw text content from tribunelist.txt

        Returns:
            List of parsed member dictionaries
        """
        members = []
        try:
            lines = raw_content.strip().split('\n')

            # First line is header
            if not lines or lines[0].startswith('tnr|call'):
                lines = lines[1:]

            # Parse CSV with | delimiter
            reader = csv.DictReader(
                lines,
                fieldnames=['tnr', 'call', 'skccnr', 'name', 'city', 'state', 'tdate', 'tendorsements'],
                delimiter='|'
            )

            for row in reader:
                # Skip empty rows
                if not row.get('call', '').strip():
                    continue

                # Parse rank (may have 'x' multiplier indicator like "9 x40")
                rank_str = row['tnr'].strip()
                rank_base = int(rank_str.split()[0])

                members.append({
                    'rank': rank_base,
                    'callsign': row['call'].strip(),
                    'skcc_number': row['skccnr'].strip(),
                    'name': row['name'].strip() if row.get('name') else '',
                    'city': row['city'].strip() if row.get('city') else '',
                    'state': row['state'].strip() if row.get('state') else '',
                    'tribune_date': row['tdate'].strip() if row.get('tdate') else '',
                    'endorsements': row['tendorsements'].strip() if row.get('tendorsements') else ''
                })

            logger.info(f"Parsed {len(members)} Tribune members")
            return members

        except Exception as e:
            logger.error(f"Error parsing Tribune list: {e}")
            return []

    @staticmethod
    def update_database(db: Session, members: List[Dict[str, str]]) -> bool:
        """
        Update the database with parsed Tribune members

        Args:
            db: SQLAlchemy database session
            members: List of parsed member dictionaries

        Returns:
            True if update successful, False otherwise
        """
        try:
            # Clear old list
            old_count = db.query(TribuneeMember).count()
            db.query(TribuneeMember).delete()
            db.commit()
            logger.info(f"Cleared {old_count} old Tribune members from database")

            # Insert new members
            now = datetime.utcnow()
            for member_data in members:
                member = TribuneeMember(
                    rank=member_data['rank'],
                    callsign=member_data['callsign'],
                    skcc_number=member_data['skcc_number'],
                    name=member_data['name'],
                    city=member_data['city'],
                    state=member_data['state'],
                    country='',  # Will be determined from SKCC data
                    tribune_date=member_data['tribune_date'],
                    endorsements=member_data['endorsements'],
                    last_list_update=now
                )
                db.add(member)

            db.commit()
            logger.info(f"Updated database with {len(members)} Tribune members")
            return True

        except Exception as e:
            logger.error(f"Error updating Tribune database: {e}")
            db.rollback()
            return False

    @staticmethod
    def should_update(db: Session) -> bool:
        """
        Check if Tribune list needs updating

        Returns:
            True if list hasn't been updated in the last 24 hours
        """
        try:
            latest_member = db.query(TribuneeMember).order_by(
                TribuneeMember.last_list_update.desc()
            ).first()

            if not latest_member:
                logger.info("No Tribune members in database, update needed")
                return True

            last_update = latest_member.last_list_update
            age = datetime.utcnow() - last_update
            should_update = age > timedelta(hours=TRIBUNE_LIST_CACHE_HOURS)

            if should_update:
                logger.info(f"Tribune list is {age.total_seconds() / 3600:.1f} hours old, update needed")
            else:
                hours_remaining = (timedelta(hours=TRIBUNE_LIST_CACHE_HOURS) - age).total_seconds() / 3600
                logger.info(f"Tribune list is current (update in {hours_remaining:.1f} hours)")

            return should_update

        except Exception as e:
            logger.error(f"Error checking Tribune list age: {e}")
            return True  # Try to update on error

    @staticmethod
    def refresh_tribune_list(db: Session, force: bool = False) -> bool:
        """
        Refresh the Tribune list from SKCC if needed

        Args:
            db: SQLAlchemy database session
            force: If True, refresh regardless of age

        Returns:
            True if list was updated successfully, False otherwise
        """
        try:
            if not force and not TribuneFetcher.should_update(db):
                logger.debug("Tribune list is current, skipping update")
                return True

            logger.info("Starting Tribune list refresh")
            raw_content = TribuneFetcher.fetch_tribune_list()

            if not raw_content:
                logger.error("Failed to fetch Tribune list, update aborted")
                return False

            members = TribuneFetcher.parse_tribune_list(raw_content)

            if not members:
                logger.error("Failed to parse Tribune list, update aborted")
                return False

            success = TribuneFetcher.update_database(db, members)

            if success:
                logger.info("Tribune list refresh completed successfully")
            else:
                logger.error("Failed to update Tribune database")

            return success

        except Exception as e:
            logger.error(f"Unexpected error during Tribune list refresh: {e}")
            return False

    @staticmethod
    def is_tribune_member(db: Session, skcc_number: str) -> bool:
        """
        Check if an SKCC member is on the Tribune list

        Args:
            db: SQLAlchemy database session
            skcc_number: SKCC member number (base number without suffix)

        Returns:
            True if member is on Tribune list
        """
        try:
            # Remove any suffix (C, T, S, x, etc.)
            base_number = skcc_number.split()[0]  # Remove spaces first
            # Remove letter suffix if present (C, T, S at the end)
            if base_number and base_number[-1] in 'CTS':
                base_number = base_number[:-1]
            # Remove x multiplier if present (xN at the end)
            if base_number and 'x' in base_number:
                base_number = base_number.split('x')[0]

            member = db.query(TribuneeMember).filter(
                TribuneeMember.skcc_number == base_number
            ).first()

            return member is not None

        except Exception as e:
            logger.error(f"Error checking Tribune status: {e}")
            return False

    @staticmethod
    def get_tribune_member_count(db: Session) -> int:
        """
        Get total count of Tribune members in database

        Returns:
            Count of members
        """
        try:
            return db.query(TribuneeMember).count()
        except Exception as e:
            logger.error(f"Error getting Tribune member count: {e}")
            return 0
