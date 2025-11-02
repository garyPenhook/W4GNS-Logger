"""
SKCC Membership Data Management

Handles downloading, parsing, caching, and querying SKCC membership roster data.
Implements local caching for fast lookups and minimal network traffic.
"""

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class SKCCMembershipManager:
    """Manages SKCC membership data synchronization and caching"""

    # SKCC membership roster sources
    PRIMARY_SOURCE = "https://www.skccgroup.com/membership_data/membership_roster.php"

    # Member data fields
    MEMBER_FIELDS = [
        'skcc_number',      # Unique SKCC member number
        'call_sign',        # Ham radio callsign
        'member_name',      # Member's name
        'join_date',        # Date joined (YYYY-MM-DD format)
        'current_suffix',   # Current award level (C, T, S, etc.)
        'current_score',    # Points toward next award
    ]

    def __init__(self, db_path: str):
        """
        Initialize membership manager

        Args:
            db_path: Path to SQLite database file

        Raises:
            ValueError: If db_path is invalid
        """
        if not db_path:
            raise ValueError("db_path cannot be empty")

        self.db_path = db_path
        self._ensure_table_exists()
        logger.info(f"SKCCMembershipManager initialized with database: {db_path}")

    def _ensure_table_exists(self) -> None:
        """Create skcc_members table if it doesn't exist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skcc_members (
                    id INTEGER PRIMARY KEY,
                    skcc_number VARCHAR(20) UNIQUE NOT NULL,
                    call_sign VARCHAR(12),
                    member_name VARCHAR(100),
                    join_date VARCHAR(10),
                    current_suffix VARCHAR(3),
                    current_score INTEGER,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for fast lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_skcc_number
                ON skcc_members(skcc_number)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_call_sign
                ON skcc_members(call_sign)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_updated
                ON skcc_members(last_updated)
            """)

            conn.commit()
            conn.close()
            logger.debug("SKCC members table ensured")

        except sqlite3.Error as e:
            logger.error(f"Database error creating skcc_members table: {e}")
            raise

    def get_member(self, skcc_number: str) -> Optional[Dict[str, Any]]:
        """
        Get member information from cache

        Args:
            skcc_number: SKCC member number to look up

        Returns:
            Dictionary with member info or None if not found
        """
        if not skcc_number:
            return None

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM skcc_members
                WHERE skcc_number = ?
            """, (skcc_number.strip(),))

            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return None

        except sqlite3.Error as e:
            logger.error(f"Database error querying member: {e}")
            return None

    def get_member_by_callsign(self, callsign: str) -> Optional[Dict[str, Any]]:
        """
        Get member information by callsign

        Args:
            callsign: Ham radio callsign to look up

        Returns:
            Dictionary with member info or None if not found
        """
        if not callsign:
            return None

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM skcc_members
                WHERE call_sign = ?
            """, (callsign.strip().upper(),))

            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return None

        except sqlite3.Error as e:
            logger.error(f"Database error querying member by callsign: {e}")
            return None

    def cache_member(self, member_data: Dict[str, Any]) -> bool:
        """
        Cache/store member data in database

        Args:
            member_data: Dictionary with member information
                Required keys: skcc_number, call_sign, member_name, join_date,
                              current_suffix, current_score

        Returns:
            True if successful, False otherwise
        """
        if not member_data or 'skcc_number' not in member_data:
            logger.warning("Invalid member data for caching")
            return False

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO skcc_members
                (skcc_number, call_sign, member_name, join_date,
                 current_suffix, current_score, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                member_data.get('skcc_number'),
                member_data.get('call_sign'),
                member_data.get('member_name'),
                member_data.get('join_date'),
                member_data.get('current_suffix'),
                member_data.get('current_score', 0),
            ))

            conn.commit()
            conn.close()
            return True

        except sqlite3.Error as e:
            logger.error(f"Database error caching member: {e}")
            return False

    def cache_members_batch(self, members_list: List[Dict[str, Any]]) -> int:
        """
        Cache multiple members at once

        Args:
            members_list: List of member dictionaries

        Returns:
            Number of members successfully cached
        """
        if not members_list:
            return 0

        successful = 0
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for member in members_list:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO skcc_members
                        (skcc_number, call_sign, member_name, join_date,
                         current_suffix, current_score, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (
                        member.get('skcc_number'),
                        member.get('call_sign'),
                        member.get('member_name'),
                        member.get('join_date'),
                        member.get('current_suffix'),
                        member.get('current_score', 0),
                    ))
                    successful += 1

                except sqlite3.Error as e:
                    logger.warning(f"Error caching member {member.get('skcc_number')}: {e}")
                    continue

            conn.commit()
            conn.close()
            logger.info(f"Cached {successful}/{len(members_list)} members")
            return successful

        except sqlite3.Error as e:
            logger.error(f"Database error in batch cache: {e}")
            return successful

    def get_last_update_time(self) -> Optional[datetime]:
        """
        Get timestamp of last cache update

        Returns:
            Datetime of last update or None if never updated
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT MAX(last_updated) as last_update
                FROM skcc_members
            """)

            result = cursor.fetchone()
            conn.close()

            if result and result[0]:
                # SQLite CURRENT_TIMESTAMP is UTC without tzinfo; mark as UTC
                return datetime.fromisoformat(result[0]).replace(tzinfo=timezone.utc)
            return None

        except sqlite3.Error as e:
            logger.error(f"Database error getting last update time: {e}")
            return None

    def is_cache_stale(self, max_age_hours: int = 24) -> bool:
        """
        Check if cached data is stale

        Args:
            max_age_hours: Maximum age of cache in hours (default: 24)

        Returns:
            True if cache is stale or empty, False otherwise
        """
        last_update = self.get_last_update_time()

        if not last_update:
            logger.debug("Cache is empty (never updated)")
            return True

        # Use timezone-aware UTC for consistency
        age = datetime.now(timezone.utc) - last_update
        is_stale = age > timedelta(hours=max_age_hours)

        if is_stale:
            logger.debug(f"Cache is stale (age: {age.total_seconds() / 3600:.1f} hours)")
        else:
            logger.debug(f"Cache is fresh (age: {age.total_seconds() / 3600:.1f} hours)")

        return is_stale

    def clear_cache(self) -> bool:
        """
        Clear all cached membership data

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM skcc_members")
            conn.commit()
            conn.close()

            logger.info("SKCC membership cache cleared")
            return True

        except sqlite3.Error as e:
            logger.error(f"Database error clearing cache: {e}")
            return False

    def get_member_count(self) -> int:
        """
        Get count of cached members

        Returns:
            Number of members in cache
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM skcc_members")
            count = cursor.fetchone()[0]
            conn.close()

            return count

        except sqlite3.Error as e:
            logger.error(f"Database error counting members: {e}")
            return 0

    def get_roster_dict(self) -> Dict[str, str]:
        """
        Get all cached members as a dictionary mapping callsign to SKCC number

        Returns:
            Dictionary with callsign as key and SKCC number as value
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT call_sign, skcc_number FROM skcc_members WHERE call_sign IS NOT NULL")
            roster = {row[0].upper(): row[1] for row in cursor.fetchall()}
            conn.close()

            return roster

        except sqlite3.Error as e:
            logger.error(f"Database error retrieving roster: {e}")
            return {}

    def search_members(self, query: str, field: str = 'skcc_number') -> List[Dict[str, Any]]:
        """
        Search for members by field

        Args:
            query: Search query string
            field: Field to search ('skcc_number', 'call_sign', 'member_name')

        Returns:
            List of matching members
        """
        if not query or field not in ['skcc_number', 'call_sign', 'member_name']:
            return []

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Use LIKE for partial matching
            cursor.execute(f"""
                SELECT * FROM skcc_members
                WHERE {field} LIKE ?
                LIMIT 100
            """, (f"%{query}%",))

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except sqlite3.Error as e:
            logger.error(f"Database error searching members: {e}")
            return []

    # TODO: Implement roster download and parsing
    # These methods will be implemented when data source is determined
    # (CSV download, API, web scraping, etc.)

    async def download_roster(self) -> bool:
        """
        Download SKCC membership roster from official source

        TODO: Implement based on data source format
        - Check if CSV download available
        - Fallback to web scraping if needed
        - Parse and cache results
        - Return success/failure

        Returns:
            True if successful, False otherwise
        """
        logger.warning("download_roster() not yet implemented - needs data source investigation")
        return False

    def parse_roster_csv(self, csv_data: str) -> List[Dict[str, Any]]:
        """
        Parse CSV roster data

        Expects format: SKCC#,Callsign,Name,JoinDate,Level,Score
        Or variations with different column orders

        Args:
            csv_data: CSV data as string

        Returns:
            List of parsed member dictionaries
        """
        try:
            import csv
            from io import StringIO

            members = []
            reader = csv.DictReader(StringIO(csv_data))

            if not reader.fieldnames:
                logger.warning("CSV has no headers")
                return []

            logger.debug(f"CSV columns: {reader.fieldnames}")

            for row_num, row in enumerate(reader, start=1):
                try:
                    # Handle various column name variations
                    skcc_num = (
                        row.get('SKCC#') or
                        row.get('skcc_number') or
                        row.get('SKCC Number') or
                        row.get('Number') or
                        ""
                    ).strip()

                    callsign = (
                        row.get('Callsign') or
                        row.get('Call Sign') or
                        row.get('Call') or
                        ""
                    ).strip().upper()

                    name = (
                        row.get('Name') or
                        row.get('Member Name') or
                        ""
                    ).strip()

                    if skcc_num and callsign:
                        member = {
                            'skcc_number': skcc_num,
                            'call_sign': callsign,
                            'member_name': name,
                            'join_date': row.get('JoinDate', row.get('Join Date', '')).strip(),
                            'current_suffix': row.get('Level', row.get('Suffix', '')).strip(),
                            'current_score': 0,
                        }
                        members.append(member)

                except Exception as e:
                    logger.debug(f"Error parsing CSV row {row_num}: {e}")
                    continue

            logger.info(f"Parsed {len(members)} members from CSV roster")
            return members

        except Exception as e:
            logger.error(f"Error parsing CSV roster: {e}")
            return []

    def parse_roster_html(self, html_data: str) -> List[Dict[str, Any]]:
        """
        Parse HTML roster data (for web scraping)

        Extracts table data from HTML

        Args:
            html_data: HTML data as string

        Returns:
            List of parsed member dictionaries
        """
        try:
            import re
            from html.parser import HTMLParser

            members = []

            # Simple regex-based table parser
            # Look for table rows
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html_data, re.DOTALL | re.IGNORECASE)

            if not rows:
                logger.warning("No table rows found in HTML")
                return []

            logger.debug(f"Found {len(rows)} potential table rows")

            for row_idx, row in enumerate(rows):
                try:
                    # Extract cells
                    cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                    if not cells:
                        cells = re.findall(r'<th[^>]*>(.*?)</th>', row, re.DOTALL | re.IGNORECASE)

                    if len(cells) < 2:
                        continue

                    # Clean cell data
                    cells = [
                        re.sub(r'<[^>]+>', '', cell).strip()
                        for cell in cells
                    ]

                    # Try to identify columns by position
                    # Common format: SKCC# | Callsign | Name | Date | Level | Score
                    if len(cells) >= 2:
                        skcc_num = cells[0].strip()
                        callsign = cells[1].strip().upper()

                        # Skip header rows
                        if skcc_num.lower() in ['skcc', 'skcc#', 'number'] or not skcc_num or not skcc_num[0].isdigit():
                            continue

                        member = {
                            'skcc_number': skcc_num,
                            'call_sign': callsign,
                            'member_name': cells[2].strip() if len(cells) > 2 else '',
                            'join_date': cells[3].strip() if len(cells) > 3 else '',
                            'current_suffix': cells[4].strip() if len(cells) > 4 else '',
                            'current_score': 0,
                        }
                        members.append(member)

                except Exception as e:
                    logger.debug(f"Error parsing HTML row {row_idx}: {e}")
                    continue

            logger.info(f"Parsed {len(members)} members from HTML roster")
            return members

        except Exception as e:
            logger.error(f"Error parsing HTML roster: {e}")
            return []

    def sync_membership_data(self, force_refresh: bool = False) -> bool:
        """
        Synchronize membership data with official SKCC roster

        Checks if cache is stale, downloads fresh data if needed

        Args:
            force_refresh: If True, always download fresh data and skip cache check

        Returns:
            True if sync successful or cache still valid, False otherwise
        """
        try:
            # Check if we have any cached members
            member_count = self.get_member_count()
            if member_count > 0 and not force_refresh:
                # Check if cache is fresh
                if not self.is_cache_stale(max_age_hours=24):
                    logger.info(f"Using fresh cached membership data ({member_count} members)")
                    return True

            # Cache is empty or stale, try to download fresh data
            logger.info("Downloading fresh SKCC membership data from official source...")

            try:
                import requests
            except ImportError:
                logger.error("requests library not available, cannot download roster")
                return self.get_member_count() > 0

            # Try primary source
            try:
                response = requests.get(
                    self.PRIMARY_SOURCE,
                    timeout=30,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (W4GNS-Logger/1.0)',
                        'Accept': 'text/csv, text/html, application/json'
                    }
                )
                response.raise_for_status()

                logger.debug(f"Downloaded {len(response.text)} bytes from {self.PRIMARY_SOURCE}")
                logger.debug(f"Content-Type: {response.headers.get('content-type', 'unknown')}")

                # Try parsing as CSV first, then HTML
                members = self.parse_roster_csv(response.text)

                if not members:
                    logger.debug("CSV parsing returned no members, trying HTML parser...")
                    members = self.parse_roster_html(response.text)

                if members:
                    # Clear old data and cache new members
                    logger.info(f"Clearing old cache and caching {len(members)} new members...")
                    self.clear_cache()
                    cached = self.cache_members_batch(members)
                    logger.info(f"Successfully synced {cached} SKCC members from official source")
                    return True
                else:
                    logger.warning(f"Downloaded roster but failed to parse members. Response sample: {response.text[:200]}")
                    return False

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout downloading from {self.PRIMARY_SOURCE} (30s)")
                return self.get_member_count() > 0
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error downloading roster: {e}")
                return self.get_member_count() > 0
            except requests.exceptions.HTTPError as e:
                logger.warning(f"HTTP error downloading roster: {e}")
                return self.get_member_count() > 0

        except Exception as e:
            logger.error(f"Error syncing membership data: {e}", exc_info=True)
            return self.get_member_count() > 0

    def load_test_data(self) -> bool:
        """
        Load test SKCC members for development/testing

        Loads sample SKCC members so the spotting system can be tested
        without relying on external roster download

        Returns:
            True if test data loaded successfully
        """
        try:
            test_members = [
                {'skcc_number': '1', 'call_sign': 'W4GNS', 'member_name': 'Test User 1'},
                {'skcc_number': '2', 'call_sign': 'W5XYZ', 'member_name': 'Test User 2'},
                {'skcc_number': '3', 'call_sign': 'K7ABC', 'member_name': 'Test User 3'},
                {'skcc_number': '4', 'call_sign': 'N0DEF', 'member_name': 'Test User 4'},
                {'skcc_number': '5', 'call_sign': 'VE3GHI', 'member_name': 'Test User 5'},
                {'skcc_number': '6', 'call_sign': 'W1JKL', 'member_name': 'Test User 6'},
                {'skcc_number': '7', 'call_sign': 'W3MNO', 'member_name': 'Test User 7'},
                {'skcc_number': '8', 'call_sign': 'W9PQR', 'member_name': 'Test User 8'},
                {'skcc_number': '9', 'call_sign': 'K0STU', 'member_name': 'Test User 9'},
                {'skcc_number': '10', 'call_sign': 'W6VWX', 'member_name': 'Test User 10'},
            ]

            self.clear_cache()
            cached = self.cache_members_batch(test_members)
            logger.warning(f"Loaded {cached} TEST SKCC members (for development only)")
            return True

        except Exception as e:
            logger.error(f"Error loading test data: {e}")
            return False
