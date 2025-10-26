"""
SKCC Centurion List Fetcher

Downloads the official SKCC Centurion member list daily and updates the database.
The list is fetched from: https://www.skccgroup.com/centurionlist.txt
"""

import logging
import csv
from datetime import datetime, timedelta
from io import StringIO
from typing import List, Dict, Optional
from urllib.request import urlopen
from urllib.error import URLError

from sqlalchemy.orm import Session

from src.database.models import CenturionMember

logger = logging.getLogger(__name__)

CENTURION_LIST_URL = "https://www.skccgroup.com/centurionlist.txt"
CENTURION_LIST_CACHE_HOURS = 24  # Refresh list every 24 hours


class CenturionFetcher:
    """Fetch and manage SKCC Centurion member list"""

    @staticmethod
    def fetch_centurion_list() -> Optional[str]:
        """
        Fetch the Centurion list from SKCC website

        Returns:
            Raw text content of the list, or None if fetch fails
        """
        try:
            logger.info(f"Fetching Centurion list from {CENTURION_LIST_URL}")
            with urlopen(CENTURION_LIST_URL, timeout=10) as response:
                content = response.read().decode('utf-8')
                logger.info(f"Successfully fetched Centurion list ({len(content)} bytes)")
                return content
        except URLError as e:
            logger.error(f"Failed to fetch Centurion list: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching Centurion list: {e}")
            return None

    @staticmethod
    def parse_centurion_list(raw_content: str) -> List[Dict[str, str]]:
        """
        Parse the Centurion list CSV format

        Format: cnr|call|skccnr|name|city|state|cdate|cendorsements

        Args:
            raw_content: Raw text content from centurionlist.txt

        Returns:
            List of parsed member dictionaries
        """
        members = []
        try:
            lines = raw_content.strip().split('\n')

            # First line is header
            if not lines or lines[0].startswith('cnr|call'):
                lines = lines[1:]

            # Parse CSV with | delimiter
            reader = csv.DictReader(
                lines,
                fieldnames=['cnr', 'call', 'skccnr', 'name', 'city', 'state', 'cdate', 'cendorsements'],
                delimiter='|'
            )

            for row in reader:
                # Skip empty rows
                if not row.get('call', '').strip():
                    continue

                # Parse rank (may have 'x' multiplier indicator like "9 x40")
                rank_str = row['cnr'].strip()
                rank_base = int(rank_str.split()[0])

                # Normalize date from "DD Mon YYYY" to YYYYMMDD format
                centurion_date_str = row['cdate'].strip() if row.get('cdate') else ''
                normalized_date = ''
                if centurion_date_str:
                    try:
                        date_obj = datetime.strptime(centurion_date_str, '%d %b %Y')
                        normalized_date = date_obj.strftime('%Y%m%d')
                    except ValueError:
                        # If parsing fails, try to keep original format
                        normalized_date = centurion_date_str
                        logger.warning(f"Could not parse Centurion date '{centurion_date_str}' for {row['call'].strip()}")

                members.append({
                    'rank': rank_base,
                    'callsign': row['call'].strip(),
                    'skcc_number': row['skccnr'].strip(),
                    'name': row['name'].strip() if row.get('name') else '',
                    'city': row['city'].strip() if row.get('city') else '',
                    'state': row['state'].strip() if row.get('state') else '',
                    'centurion_date': normalized_date,
                    'endorsements': row['cendorsements'].strip() if row.get('cendorsements') else ''
                })

            logger.info(f"Parsed {len(members)} Centurion members")
            return members

        except Exception as e:
            logger.error(f"Error parsing Centurion list: {e}")
            return []

    @staticmethod
    def update_database(db: Session, members: List[Dict[str, str]]) -> bool:
        """
        Update the database with parsed Centurion members

        Args:
            db: SQLAlchemy database session
            members: List of parsed member dictionaries

        Returns:
            True if update successful, False otherwise
        """
        try:
            # Clear old list
            old_count = db.query(CenturionMember).count()
            db.query(CenturionMember).delete()
            db.commit()
            logger.info(f"Cleared {old_count} old Centurion members from database")

            # Insert new members
            now = datetime.utcnow()
            for member_data in members:
                member = CenturionMember(
                    rank=member_data['rank'],
                    callsign=member_data['callsign'],
                    skcc_number=member_data['skcc_number'],
                    name=member_data['name'],
                    city=member_data['city'],
                    state=member_data['state'],
                    country='',  # Will be determined from SKCC data
                    centurion_date=member_data['centurion_date'],
                    endorsements=member_data['endorsements'],
                    last_list_update=now
                )
                db.add(member)

            db.commit()
            logger.info(f"Updated database with {len(members)} Centurion members")
            return True

        except Exception as e:
            logger.error(f"Error updating Centurion database: {e}")
            db.rollback()
            return False

    @staticmethod
    def should_update(db: Session) -> bool:
        """
        Check if Centurion list needs updating

        Returns:
            True if list hasn't been updated in the last 24 hours
        """
        try:
            latest_member = db.query(CenturionMember).order_by(
                CenturionMember.last_list_update.desc()
            ).first()

            if not latest_member:
                logger.info("No Centurion members in database, update needed")
                return True

            last_update = latest_member.last_list_update
            age = datetime.utcnow() - last_update
            should_update = age > timedelta(hours=CENTURION_LIST_CACHE_HOURS)

            if should_update:
                logger.info(f"Centurion list is {age.total_seconds() / 3600:.1f} hours old, update needed")
            else:
                hours_remaining = (timedelta(hours=CENTURION_LIST_CACHE_HOURS) - age).total_seconds() / 3600
                logger.info(f"Centurion list is current (update in {hours_remaining:.1f} hours)")

            return should_update

        except Exception as e:
            logger.error(f"Error checking Centurion list age: {e}")
            return True  # Try to update on error

    @staticmethod
    def refresh_centurion_list(db: Session, force: bool = False) -> bool:
        """
        Refresh the Centurion list from SKCC if needed

        Args:
            db: SQLAlchemy database session
            force: If True, refresh regardless of age

        Returns:
            True if list was updated successfully, False otherwise
        """
        try:
            if not force and not CenturionFetcher.should_update(db):
                logger.debug("Centurion list is current, skipping update")
                return True

            logger.info("Starting Centurion list refresh")
            raw_content = CenturionFetcher.fetch_centurion_list()

            if not raw_content:
                logger.error("Failed to fetch Centurion list, update aborted")
                return False

            members = CenturionFetcher.parse_centurion_list(raw_content)

            if not members:
                logger.error("Failed to parse Centurion list, update aborted")
                return False

            success = CenturionFetcher.update_database(db, members)

            if success:
                logger.info("Centurion list refresh completed successfully")
            else:
                logger.error("Failed to update Centurion database")

            return success

        except Exception as e:
            logger.error(f"Unexpected error during Centurion list refresh: {e}")
            return False

    @staticmethod
    def is_centurion_member(db: Session, skcc_number: str) -> bool:
        """
        Check if an SKCC member is on the Centurion list

        Args:
            db: SQLAlchemy database session
            skcc_number: SKCC member number (base number without suffix)

        Returns:
            True if member is on Centurion list
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

            member = db.query(CenturionMember).filter(
                CenturionMember.skcc_number == base_number
            ).first()

            return member is not None

        except Exception as e:
            logger.error(f"Error checking Centurion status: {e}")
            return False

    @staticmethod
    def get_centurion_member_count(db: Session) -> int:
        """
        Get total count of Centurion members in database

        Returns:
            Count of members
        """
        try:
            return db.query(CenturionMember).count()
        except Exception as e:
            logger.error(f"Error getting Centurion member count: {e}")
            return 0
