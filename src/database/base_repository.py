"""
Base Repository - Shared Database Infrastructure

Provides database connection management, session factory, and schema migrations
for all repository classes.
"""

import logging
from sqlalchemy import create_engine, pool, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from .models import Base

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository with shared database infrastructure"""

    def __init__(self, db_path: str):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file

        Raises:
            SQLAlchemyError: If database connection fails
        """
        self.db_path = db_path
        try:
            # Create engine with timeout protection and connection pooling
            self.engine = create_engine(
                f"sqlite:///{db_path}",
                echo=False,
                connect_args={
                    'timeout': 10.0,  # 10 second timeout for database lock
                    'check_same_thread': False  # Allow multi-threaded access
                },
                poolclass=pool.SingletonThreadPool,  # Use singleton pool for SQLite
                pool_pre_ping=True  # Verify connections before use
            )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

            # Create tables if they don't exist
            Base.metadata.create_all(self.engine)

            # Perform schema migrations
            self._migrate_schema()

            logger.info(f"BaseRepository initialized: {db_path}")
        except SQLAlchemyError as e:
            logger.error(f"Failed to initialize database at {db_path}: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error initializing database: {e}", exc_info=True)
            raise

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()

    def _migrate_schema(self) -> None:
        """
        Perform schema migrations by adding missing columns to existing tables.

        This handles cases where the model definition has been updated with new columns
        but the existing database hasn't been updated yet.
        """
        session = self.get_session()
        try:
            # Define columns that need to exist in the contacts table
            columns_to_add = [
                ("my_rig_make", "VARCHAR(50)", "My rig manufacturer"),
                ("my_rig_model", "VARCHAR(50)", "My rig model number"),
                ("my_antenna_make", "VARCHAR(50)", "My antenna manufacturer"),
                ("my_antenna_model", "VARCHAR(50)", "My antenna model"),
            ]

            # Check which columns are missing and add them
            for column_name, column_type, _description in columns_to_add:
                try:
                    # Try to query the column to see if it exists
                    session.execute(text(f"SELECT {column_name} FROM contacts LIMIT 1"))
                except Exception:
                    # Column doesn't exist, add it
                    try:
                        session.execute(text(f"ALTER TABLE contacts ADD COLUMN {column_name} {column_type}"))
                        session.commit()
                        logger.info(f"Added missing column '{column_name}' to contacts table")
                    except Exception as alter_error:
                        logger.error(f"Failed to add column '{column_name}': {alter_error}", exc_info=True)
                        session.rollback()

            logger.info("Schema migration completed successfully")
        except Exception as e:
            logger.error(f"Error during schema migration: {e}", exc_info=True)
            session.rollback()
        finally:
            session.close()
