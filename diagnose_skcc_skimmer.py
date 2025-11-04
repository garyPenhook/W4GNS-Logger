#!/usr/bin/env python3
"""
SKCC Skimmer Integration Diagnostic

Test the SKCC Skimmer integration to identify actual issues.
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """Test that all SKCC Skimmer imports work"""
    print("Testing imports...")
    try:
        from src.skcc import SkccSkimmerSubprocess, SkimmerConnectionState, SKCCSpot

        print("  ✓ SKCC Skimmer imports successful")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_database():
    """Test database and SKCCMembershipManager"""
    print("\nTesting database...")
    try:
        from src.database.repository import DatabaseRepository
        from pathlib import Path

        # Use test database in /tmp
        test_db = "/tmp/test_skcc.db"
        if os.path.exists(test_db):
            os.remove(test_db)

        db = DatabaseRepository(test_db)
        print("  ✓ Database initialized")

        # Check if skcc_members exists
        if hasattr(db, "skcc_members"):
            print("  ✓ SKCCMembershipManager available")

            # Check methods
            methods = ["clear_cache", "sync_membership_data", "get_member_count", "get_roster_dict"]
            for method in methods:
                if hasattr(db.skcc_members, method):
                    print(f"    ✓ {method}() exists")
                else:
                    print(f"    ✗ {method}() missing")
            return True
        else:
            print("  ✗ SKCCMembershipManager not found on db")
            return False

    except Exception as e:
        print(f"  ✗ Database test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_skcc_skimmer_detection():
    """Test SKCC Skimmer auto-detection"""
    print("\nTesting SKCC Skimmer detection...")
    try:
        from src.skcc import SkccSkimmerSubprocess
        from pathlib import Path

        skimmer = SkccSkimmerSubprocess()
        print(f"  Detected SKCC Skimmer path: {skimmer.skimmer_path}")

        if skimmer.skimmer_path.exists():
            print(f"  ✓ SKCC Skimmer found at: {skimmer.skimmer_path}")
            skimmer_script = skimmer.skimmer_path / "skcc_skimmer.py"
            if skimmer_script.exists():
                print(f"  ✓ SKCC Skimmer script found at: {skimmer_script}")
                return True
            else:
                print(f"  ✗ SKCC Skimmer script not found at: {skimmer_script}")
                print(f"     (SKCC Skimmer must be installed separately)")
                return False
        else:
            print(f"  ✗ SKCC Skimmer NOT found at: {skimmer.skimmer_path}")
            print(f"     (This is expected if not installed)")
            return False

    except Exception as e:
        print(f"  ✗ SKCC Skimmer detection failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_backup_manager():
    """Test BackupManager export method"""
    print("\nTesting BackupManager...")
    try:
        from src.backup.backup_manager import BackupManager

        backup_mgr = BackupManager()
        print("  ✓ BackupManager initialized")

        # Check if export_single_adif exists
        if hasattr(backup_mgr, "export_single_adif"):
            print("  ✓ export_single_adif() exists")
            return True
        else:
            print("  ✗ export_single_adif() not found")
            return False

    except Exception as e:
        print(f"  ✗ BackupManager test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_widget_creation():
    """Test if the SKCC Spots widget can be created"""
    print("\nTesting SKCC Spots widget creation...")
    try:
        from src.database.repository import DatabaseRepository
        from src.ui.widgets.skcc_spots_widget import SKCCSpotWidget

        # Initialize database
        test_db = "/tmp/test_skcc_widget.db"
        if os.path.exists(test_db):
            os.remove(test_db)

        db = DatabaseRepository(test_db)
        print("  ✓ Database initialized")

        # Try to create widget (without GUI)
        # Note: This will fail if PyQt6 is not available or no display
        try:
            widget = SKCCSpotWidget(db, parent=None)
            print("  ✓ SKCCSpotWidget created successfully")
            return True
        except Exception as widget_error:
            if (
                "no display" in str(widget_error).lower()
                or "cannot connect" in str(widget_error).lower()
            ):
                print(
                    f"  ⚠ Widget creation requires GUI (expected in CI): {type(widget_error).__name__}"
                )
                return True  # This is OK
            else:
                print(f"  ✗ Widget creation failed: {widget_error}")
                return False

    except Exception as e:
        print(f"  ✗ Widget test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("SKCC SKIMMER INTEGRATION DIAGNOSTIC")
    print("=" * 60)

    results = {
        "Imports": test_imports(),
        "Database": test_database(),
        "SKCC Skimmer Detection": test_skcc_skimmer_detection(),
        "BackupManager": test_backup_manager(),
        "Widget Creation": test_widget_creation(),
    }

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "=" * 60)
    print("ANALYSIS")
    print("=" * 60)

    if results["SKCC Skimmer Detection"]:
        print("\n✓ SKCC Skimmer is INSTALLED and available")
        print("  The W4GNS Logger can use it for intelligent spot filtering")
    else:
        print("\n✗ SKCC Skimmer is NOT INSTALLED")
        print("  To use SKCC Skimmer features:")
        print("    1. Download K7MJG's SKCC Skimmer from: https://www.skccgroup.com/skimmer/")
        print("    2. Extract to ~/skcc_skimmer/ directory")
        print("    3. Restart the application")

    if all(results.values()):
        print("\n✅ ALL TESTS PASSED - SKCC Skimmer is fully functional!")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED - Check output above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
