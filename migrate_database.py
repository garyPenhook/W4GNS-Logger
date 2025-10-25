#!/usr/bin/env python3
"""
Database Migration Script

Adds missing columns (skcc_number, key_type) to existing contacts table.
This allows the GUI to work with databases created before these fields were added.
"""

import sqlite3
import sys
from pathlib import Path

def migrate_database(db_path: str) -> bool:
    """
    Add missing columns to contacts table if they don't exist

    Args:
        db_path: Path to the SQLite database file

    Returns:
        True if migration successful, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print(f"Connecting to database: {db_path}")

        # Check if columns already exist
        cursor.execute("PRAGMA table_info(contacts)")
        columns = {row[1]: row for row in cursor.fetchall()}

        migrations_needed = []

        # Check for skcc_number column
        if 'skcc_number' not in columns:
            migrations_needed.append('skcc_number')
            print("✓ Migration needed: skcc_number column missing")
        else:
            print("✓ skcc_number column already exists")

        # Check for key_type column
        if 'key_type' not in columns:
            migrations_needed.append('key_type')
            print("✓ Migration needed: key_type column missing")
        else:
            print("✓ key_type column already exists")

        if not migrations_needed:
            print("\n✅ Database is already up to date!")
            conn.close()
            return True

        # Perform migrations
        print(f"\nPerforming {len(migrations_needed)} migration(s)...")

        if 'skcc_number' in migrations_needed:
            print("  Adding skcc_number column...")
            cursor.execute("""
                ALTER TABLE contacts
                ADD COLUMN skcc_number VARCHAR(20)
            """)
            print("    ✓ skcc_number column added")

        if 'key_type' in migrations_needed:
            print("  Adding key_type column...")
            cursor.execute("""
                ALTER TABLE contacts
                ADD COLUMN key_type VARCHAR(20) DEFAULT 'STRAIGHT'
            """)
            print("    ✓ key_type column added with default 'STRAIGHT'")

        # Commit changes
        conn.commit()
        print("\n✅ Database migration successful!")
        print(f"✓ {len(migrations_needed)} column(s) added to contacts table")

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def main():
    """Main entry point"""
    # Try to find database in default location
    db_path = "/home/w4gns/Projects/W4GNS Logger/database.db"

    if len(sys.argv) > 1:
        db_path = sys.argv[1]

    if not Path(db_path).exists():
        print(f"❌ Database file not found: {db_path}")
        print("\nUsage: python3 migrate_database.py [database_path]")
        sys.exit(1)

    print("═" * 70)
    print("W4GNS Logger - Database Migration")
    print("═" * 70)
    print()

    success = migrate_database(db_path)

    print()
    if success:
        print("✅ Migration complete! You can now run the application.")
        print("\nNext steps:")
        print("  1. Start the application: python3 -m src.main")
        print("  2. Add new contacts with TX/RX Power fields")
        print("  3. View QRP Progress and Power Stats tabs")
    else:
        print("❌ Migration failed. Please check the error above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
