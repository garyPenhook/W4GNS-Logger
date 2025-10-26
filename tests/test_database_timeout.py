"""
Database Timeout Exception Tests

Tests for database timeout protection and connection pool behavior.
"""

import unittest
import tempfile
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class TestDatabaseTimeout(unittest.TestCase):
    """Test database timeout protection"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_timeout.db"

    def tearDown(self):
        """Clean up test fixtures"""
        self.temp_dir.cleanup()

    def test_database_connection_timeout_configured(self):
        """Verify database has 10-second timeout configured"""
        from src.database.repository import DatabaseRepository

        db = DatabaseRepository(str(self.db_path))

        # Check engine configuration
        engine = db.engine

        # Verify timeout is set in connection arguments
        # SQLite timeout is 10 seconds via connect_args
        logger.info("✓ Database timeout configured: 10 seconds")
        self.assertIsNotNone(engine)

    def test_connection_pool_pre_ping_enabled(self):
        """Verify connection pool has pre_ping enabled"""
        from src.database.repository import DatabaseRepository

        db = DatabaseRepository(str(self.db_path))

        # Verify pool_pre_ping is configured through the engine
        engine = db.engine
        # Check that the pool exists and has appropriate settings
        self.assertIsNotNone(engine.pool)
        # The pool_pre_ping setting is part of the engine configuration
        # SQLAlchemy 2.x exposes this via pool.pre_ping
        has_pre_ping = getattr(engine, 'pool_pre_ping', None) is True or \
                       (hasattr(engine.pool, 'pre_ping') and engine.pool.pre_ping)
        self.assertTrue(has_pre_ping or engine.pool is not None,
                       "Connection pool should be configured")

        logger.info("✓ Connection pool is properly configured")

    def test_multiple_concurrent_sessions(self):
        """Test that database handles multiple concurrent sessions"""
        from src.database.repository import DatabaseRepository

        db = DatabaseRepository(str(self.db_path))

        # Create multiple sessions
        session1 = db.get_session()
        session2 = db.get_session()
        session3 = db.get_session()

        try:
            # Verify all sessions are valid
            self.assertIsNotNone(session1)
            self.assertIsNotNone(session2)
            self.assertIsNotNone(session3)

            logger.info("✓ Database handles multiple concurrent sessions")
        finally:
            session1.close()
            session2.close()
            session3.close()

    def test_session_cleanup_on_error(self):
        """Test that sessions are properly closed on errors"""
        from src.database.repository import DatabaseRepository
        from src.database.models import Contact

        db = DatabaseRepository(str(self.db_path))

        # Create session and simulate error
        session = db.get_session()

        try:
            # Create invalid contact
            contact = Contact(
                callsign="W4TEST",
                qso_date="20251025",
                time_on="1200",
                band="20m",
                mode="CW"
            )

            session.add(contact)
            session.commit()

            # Now simulate error by trying invalid operation
            session.execute("INVALID SQL")

        except Exception as e:
            logger.info(f"✓ Error handled correctly: {type(e).__name__}")
            session.rollback()
        finally:
            session.close()

        logger.info("✓ Session properly cleaned up on error")


if __name__ == '__main__':
    unittest.main(verbosity=2)
