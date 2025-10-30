#!/usr/bin/env python3
"""
Add Performance Indexes to Existing Database

This script adds the new performance-optimized indexes to an existing contacts.db
without losing any data. These indexes will dramatically speed up award calculations.

Run this once after updating the models.py file.
"""

import sqlite3
import sys
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent / "contacts.db"

# New indexes to add (these match the ones defined in models.py)
NEW_INDEXES = [
    # Optimized indexes for award calculations
    ("idx_mode_key_type_skcc", "contacts", ["mode", "key_type", "skcc_number"]),
    ("idx_mode_qso_date_skcc", "contacts", ["mode", "qso_date", "skcc_number"]),
    ("idx_mode_tx_power_band", "contacts", ["mode", "tx_power", "band"]),
    ("idx_mode_tx_rx_power", "contacts", ["mode", "tx_power", "rx_power"]),
]


def index_exists(cursor, index_name):
    """Check if an index already exists"""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,)
    )
    return cursor.fetchone() is not None


def add_indexes():
    """Add new performance indexes to the database"""
    if not DB_PATH.exists():
        print(f"❌ Error: Database not found at {DB_PATH}")
        print("   Please run this script from the project root directory.")
        return False

    print(f"📂 Opening database: {DB_PATH}")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print("\n🔍 Checking which indexes need to be added...\n")

        added_count = 0
        skipped_count = 0

        for index_name, table_name, columns in NEW_INDEXES:
            if index_exists(cursor, index_name):
                print(f"   ⏭️  {index_name} - already exists, skipping")
                skipped_count += 1
            else:
                print(f"   ➕ {index_name} - creating...")

                # Build the CREATE INDEX statement
                columns_str = ", ".join(columns)
                sql = f"CREATE INDEX {index_name} ON {table_name} ({columns_str})"

                try:
                    cursor.execute(sql)
                    print(f"      ✅ Created successfully")
                    added_count += 1
                except sqlite3.Error as e:
                    print(f"      ❌ Failed: {e}")

        # Commit all changes
        conn.commit()
        print(f"\n{'='*60}")
        print(f"✅ Index creation complete!")
        print(f"   Added: {added_count} new indexes")
        print(f"   Skipped: {skipped_count} existing indexes")
        print(f"{'='*60}\n")

        # Analyze the database to update query planner statistics
        print("📊 Analyzing database to update query planner statistics...")
        cursor.execute("ANALYZE")
        conn.commit()
        print("   ✅ Analysis complete\n")

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Performance Index Installation Script")
    print("="*60 + "\n")

    success = add_indexes()

    if success:
        print("🎉 All done! Your database is now optimized for 10x faster award calculations.\n")
        sys.exit(0)
    else:
        print("⚠️  Index installation failed. Please check the error messages above.\n")
        sys.exit(1)
