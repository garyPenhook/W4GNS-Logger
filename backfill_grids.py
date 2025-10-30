#!/usr/bin/env python3
"""
Backfill Grid Squares from QRZ.com

Looks up missing grid squares for contacts via QRZ XML API and updates the database.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database.repository import DatabaseRepository
from src.config.settings import ConfigManager, get_config_manager
from src.qrz.qrz_api import QRZAPIClient, QRZError


def backfill_grids():
    """Backfill missing grid squares from QRZ lookups"""
    
    print("=" * 70)
    print("QRZ Grid Square Backfill Utility")
    print("=" * 70)
    print()
    
    # Initialize components
    config = get_config_manager()
    db_path = Path(config.get('database.path', '~/.w4gns_logger/contacts.db')).expanduser()
    repo = DatabaseRepository(db_path)
    
    # Get QRZ credentials
    qrz_username = config.get("qrz.username", "")
    qrz_password = config.get("qrz.password", "")
    
    if not qrz_username or not qrz_password:
        print("ERROR: QRZ credentials not configured!")
        print("Please configure QRZ username/password in config/qrz.yaml")
        return
    
    print(f"Using QRZ account: {qrz_username}")
    print()
    
    # Find contacts missing grid squares
    with repo.get_session() as session:
        from src.database.models import Contact
        contacts = session.query(Contact).filter(
            (Contact.gridsquare == None) | (Contact.gridsquare == "")
        ).all()
        
        if not contacts:
            print("No contacts found missing grid squares!")
            return
        
        print(f"Found {len(contacts)} contacts missing grid squares")
        print()
        
        # Show sample
        print("Sample contacts to update:")
        for contact in contacts[:5]:
            print(f"  - {contact.callsign} ({contact.qso_date} {contact.time_on})")
        if len(contacts) > 5:
            print(f"  ... and {len(contacts) - 5} more")
        print()
        
        # Confirm
        response = input(f"Look up grid squares for {len(contacts)} contacts? (yes/no): ").strip().lower()
        if response not in ('yes', 'y'):
            print("Cancelled.")
            return
        
        print()
        print("=" * 70)
        print("Starting QRZ lookups...")
        print("=" * 70)
        print()
        
        # Initialize QRZ client
        qrz = QRZAPIClient(qrz_username, qrz_password, timeout=15)
        
        stats = {
            'updated': 0,
            'not_found': 0,
            'no_grid': 0,
            'errors': 0,
            'total': len(contacts)
        }
        
        # Process contacts
        for i, contact in enumerate(contacts, 1):
            callsign = contact.callsign
            print(f"[{i}/{len(contacts)}] Looking up {callsign}...", end=' ')
            
            try:
                # Lookup callsign
                info = qrz.lookup_callsign(callsign, use_cache=False)
                
                if info is None:
                    print("not found in QRZ")
                    stats['not_found'] += 1
                    continue
                
                if not info.grid:
                    print("no grid in QRZ")
                    stats['no_grid'] += 1
                    continue
                
                # Update contact
                contact.gridsquare = info.grid
                session.commit()
                
                print(f"✓ {info.grid}")
                stats['updated'] += 1
                
                # Rate limiting - QRZ allows ~100 lookups per minute
                if i % 50 == 0:
                    print(f"\nPausing 30s for rate limiting...")
                    time.sleep(30)
                else:
                    time.sleep(0.6)  # ~100/minute
                
            except QRZError as e:
                print(f"QRZ error: {e}")
                stats['errors'] += 1
            except Exception as e:
                print(f"ERROR: {e}")
                stats['errors'] += 1
                session.rollback()
        
        print()
        print("=" * 70)
        print("Backfill Complete!")
        print("=" * 70)
        print()
        print(f"Total contacts processed: {stats['total']}")
        print(f"  ✓ Grid squares updated: {stats['updated']}")
        print(f"  - Not found in QRZ: {stats['not_found']}")
        print(f"  - No grid in QRZ: {stats['no_grid']}")
        print(f"  - Errors: {stats['errors']}")
        print()
        
        if stats['updated'] > 0:
            print("Next step: Run distance backfill")
            print("  python backfill_distances.py")
            print()


if __name__ == "__main__":
    try:
        backfill_grids()
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
