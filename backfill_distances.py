#!/usr/bin/env python3
"""
Backfill Distance Calculator

This script calculates and populates the distance field for all existing contacts
that have grid squares but are missing distance data.

Usage:
    python backfill_distances.py
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.database.repository import DatabaseRepository
from src.config.settings import get_config_manager
from src.utils.grid_calc import batch_calculate_distances, is_rust_available

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run distance backfill"""
    try:
        print("=" * 60)
        print("W4GNS Logger - Distance Backfill Utility")
        print("=" * 60)
        
        # Get configuration
        config = get_config_manager()
        home_grid = config.get('general.home_grid', '')
        db_path = config.get('database.path', '~/.w4gns_logger/contacts.db')
        
        # Expand path
        db_path = Path(db_path).expanduser()
        
        if not home_grid:
            print("\nERROR: Home grid square not configured!")
            print("Please set your home grid in Settings before running this script.")
            return 1
        
        print(f"\nHome Grid: {home_grid}")
        print(f"Database: {db_path}")
        
        # Check if Rust acceleration is available
        if is_rust_available():
            print("✓ Using Rust acceleration (high performance)")
        else:
            print("⚠ Using Python fallback (Rust module not available)")
        
        # Confirm
        response = input("\nCalculate distances for all contacts? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Cancelled.")
            return 0
        
        # Connect to database
        print("\nConnecting to database...")
        db = DatabaseRepository(str(db_path))
        
        # Run backfill
        print("\nCalculating distances...")
        print("(This may take a moment for large contact logs)")
        print()
        
        result = db.backfill_contact_distances(home_grid)
        
        # Display results
        print("\n" + "=" * 60)
        print("BACKFILL COMPLETE")
        print("=" * 60)
        print(f"Total contacts processed: {result['total']}")
        print(f"✓ Updated with distance: {result['updated']}")
        print(f"⊘ Skipped (invalid grid): {result['skipped']}")
        print(f"✗ Errors: {result['errors']}")
        print()
        
        if result['updated'] > 0:
            print("Success! Distances have been calculated.")
            print("\nYou can now:")
            print("  • View MPW values in the Contacts tab")
            print("  • Check QRP MPW progress in Awards → QRP MPW")
            print()
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during backfill: {e}", exc_info=True)
        print(f"\nERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
