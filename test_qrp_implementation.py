#!/usr/bin/env python3
"""
Test script for QRP Power Tracking Implementation
Tests all QRP model methods and repository methods
"""

import os
import sys
import tempfile
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from src.database.models import Contact, create_database
from src.database.repository import DatabaseRepository

def test_qrp_contact_model_methods():
    """Test Contact model QRP methods"""
    print("\n" + "="*80)
    print("TEST 1: Contact Model QRP Methods")
    print("="*80)

    # Test is_qrp_contact()
    contact_qrp = Contact(
        callsign="W5XYZ",
        qso_date="20241021",
        time_on="1430",
        band="40M",
        mode="CW",
        tx_power=3.5
    )
    print(f"✓ 3.5W contact is QRP: {contact_qrp.is_qrp_contact()} (expected True)")
    assert contact_qrp.is_qrp_contact() == True

    contact_high = Contact(
        callsign="K0ABC",
        qso_date="20241020",
        time_on="1200",
        band="80M",
        mode="CW",
        tx_power=25.0
    )
    print(f"✓ 25W contact is QRP: {contact_high.is_qrp_contact()} (expected False)")
    assert contact_high.is_qrp_contact() == False

    # Test is_qrp_two_way()
    contact_2way = Contact(
        callsign="N4DEF",
        qso_date="20241019",
        time_on="1530",
        band="20M",
        mode="CW",
        tx_power=2.0,
        rx_power=4.5
    )
    print(f"✓ 2W ↔ 4.5W is 2-way QRP: {contact_2way.is_qrp_two_way(4.5)} (expected True)")
    assert contact_2way.is_qrp_two_way(4.5) == True

    print(f"✓ 2W ↔ 25W is 2-way QRP: {contact_2way.is_qrp_two_way(25.0)} (expected False)")
    assert contact_2way.is_qrp_two_way(25.0) == False

    # Test calculate_mpw()
    contact_mpw = Contact(
        callsign="W1GHI",
        qso_date="20241018",
        time_on="0900",
        band="15M",
        mode="CW",
        tx_power=1.0
    )
    mpw = contact_mpw.calculate_mpw(1500.0)  # 1500 miles at 1W
    print(f"✓ 1500 miles at 1W = {mpw} MPW (expected 1500)")
    assert mpw == 1500.0

    # Test qualifies_for_mpw()
    qualifies = contact_mpw.qualifies_for_mpw(1500.0)
    print(f"✓ 1500 miles at 1W qualifies for MPW: {qualifies} (expected True, ≥1000)")
    assert qualifies == True

    does_not_qualify = contact_high.qualifies_for_mpw(100.0)
    print(f"✓ 100 miles at 25W qualifies for MPW: {does_not_qualify} (expected False, >5W)")
    assert does_not_qualify == False

    # Test get_qrp_category()
    contact_qrpp = Contact(
        callsign="VK3XYZ",
        qso_date="20241017",
        time_on="2000",
        band="10M",
        mode="CW",
        tx_power=0.2
    )
    print(f"✓ 0.2W category: {contact_qrpp.get_qrp_category()} (expected 'QRPp')")
    assert contact_qrpp.get_qrp_category() == "QRPp"

    print(f"✓ 3.5W category: {contact_qrp.get_qrp_category()} (expected 'QRP')")
    assert contact_qrp.get_qrp_category() == "QRP"

    print(f"✓ 25W category: {contact_high.get_qrp_category()} (expected 'STANDARD')")
    assert contact_high.get_qrp_category() == "STANDARD"

    contact_qro = Contact(
        callsign="JA2XYZ",
        qso_date="20241016",
        time_on="0530",
        band="6M",
        mode="CW",
        tx_power=1500.0
    )
    print(f"✓ 1500W category: {contact_qro.get_qrp_category()} (expected 'QRO')")
    assert contact_qro.get_qrp_category() == "QRO"

    print("\n✅ All Contact Model tests passed!")


def test_qrp_repository_methods():
    """Test DatabaseRepository QRP methods"""
    print("\n" + "="*80)
    print("TEST 2: DatabaseRepository QRP Methods")
    print("="*80)

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        repo = DatabaseRepository(db_path)

        # Create test data
        test_contacts = [
            # QRP x1 contacts on different bands
            Contact(callsign="W5XYZ", qso_date="20241021", time_on="1430", band="160M", mode="CW", tx_power=5.0),
            Contact(callsign="K0ABC", qso_date="20241020", time_on="1200", band="80M", mode="CW", tx_power=3.5),
            Contact(callsign="N4DEF", qso_date="20241019", time_on="1530", band="40M", mode="CW", tx_power=2.0, rx_power=4.5),
            Contact(callsign="W1GHI", qso_date="20241018", time_on="0900", band="20M", mode="CW", tx_power=1.0),
            Contact(callsign="VK3JKL", qso_date="20241017", time_on="2000", band="10M", mode="CW", tx_power=5.0),
            # Non-QRP contacts
            Contact(callsign="JA2MNO", qso_date="20241016", time_on="0530", band="15M", mode="CW", tx_power=25.0),
            Contact(callsign="ZL3PQR", qso_date="20241015", time_on="1800", band="12M", mode="CW", tx_power=100.0),
            # Additional QRP for 2-way
            Contact(callsign="W5STU", qso_date="20241014", time_on="1100", band="6M", mode="CW", tx_power=0.5, rx_power=3.0),
        ]

        for contact in test_contacts:
            repo.add_contact(contact)

        # Test get_qrp_contacts()
        qrp_contacts = repo.get_qrp_contacts()
        print(f"✓ Found {len(qrp_contacts)} QRP contacts (expected 6)")
        assert len(qrp_contacts) == 6

        # Test count_qrp_points_by_band()
        points_result = repo.count_qrp_points_by_band()
        print(f"✓ QRP x1 points breakdown:")
        for band, points in points_result["band_points"].items():
            print(f"    {band}: {points} points")
        print(f"✓ Total QRP x1 points: {points_result['total_points']} (160M:4 + 80M:3 + 40M:2 + 20M:1 + 10M:3 + 6M:0.5 = 13.5)")
        # 160M=4, 80M=3, 40M=2, 20M=1, 10M=3, 6M=0.5 = 13.5 points
        assert points_result["total_points"] == 13.5

        # Test analyze_qrp_award_progress()
        progress = repo.analyze_qrp_award_progress()
        print(f"\n✓ QRP Award Progress:")
        print(f"    QRP x1: {progress['qrp_x1']['points']} points (need 300)")
        print(f"    QRP x1 Qualified: {progress['qrp_x1']['qualified']}")
        print(f"    QRP x1 Contacts: {progress['qrp_x1']['contacts']}")
        print(f"    QRP x2: {progress['qrp_x2']['points']} points (need 150)")
        print(f"    QRP x2 Qualified: {progress['qrp_x2']['qualified']}")
        print(f"    QRP x2 Contacts: {progress['qrp_x2']['contacts']}")

        # x1 and x2 should have same points for our test data (all contacts have both power ≤5W)
        assert progress['qrp_x1']['qualified'] == False  # Only 13.5 points
        assert progress['qrp_x2']['qualified'] == False  # Only some contacts have 2-way QRP

        # Test get_power_statistics()
        stats = repo.get_power_statistics()
        print(f"\n✓ Power Statistics:")
        print(f"    Total with power data: {stats['total_with_power']}")
        print(f"    QRPp (<0.5W): {stats['qrpp_count']}")
        print(f"    QRP (0.5-5W): {stats['qrp_count']}")
        print(f"    STANDARD (5-100W): {stats['standard_count']}")
        print(f"    QRO (>100W): {stats['qro_count']}")
        print(f"    Average power: {stats['average_power']:.2f}W")
        print(f"    Min power: {stats['min_power']}W")
        print(f"    Max power: {stats['max_power']}W")

        assert stats['total_with_power'] == 8
        # Note: 0.5W is exactly at boundary, categorized as QRP not QRPp
        assert stats['qrpp_count'] == 0  # No contacts < 0.5W
        assert stats['qrp_count'] == 6   # 6 contacts in 0.5-5W range (includes 0.5W boundary)
        assert stats['standard_count'] == 2  # 25W and 100W (but 100W is boundary of 100)
        assert stats['qro_count'] == 0   # No contacts > 100W

        # Test calculate_mpw_qualifications()
        mpw_quals = repo.calculate_mpw_qualifications()
        print(f"\n✓ MPW Qualifications: {len(mpw_quals)} contacts qualify")
        # Without distance data, should have 0 qualifications
        assert len(mpw_quals) == 0

        print("\n✅ All Repository tests passed!")

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)


def test_qrp_with_distance_data():
    """Test MPW calculations with distance data"""
    print("\n" + "="*80)
    print("TEST 3: QRP MPW with Distance Data")
    print("="*80)

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        repo = DatabaseRepository(db_path)

        # Create contacts with distance data
        mpw_test_contacts = [
            # 500 miles at 0.5W = 1000 MPW (qualifies)
            Contact(callsign="W5XYZ", qso_date="20241021", time_on="1430", band="40M", mode="CW", tx_power=0.5, distance=500.0),
            # 1200 miles at 1W = 1200 MPW (qualifies)
            Contact(callsign="K0ABC", qso_date="20241020", time_on="1200", band="80M", mode="CW", tx_power=1.0, distance=1200.0),
            # 2500 miles at 5W = 500 MPW (doesn't qualify)
            Contact(callsign="N4DEF", qso_date="20241019", time_on="1530", band="20M", mode="CW", tx_power=5.0, distance=2500.0),
            # 100 miles at 0.1W = 1000 MPW (qualifies)
            Contact(callsign="W1GHI", qso_date="20241018", time_on="0900", band="15M", mode="CW", tx_power=0.1, distance=100.0),
        ]

        for contact in mpw_test_contacts:
            repo.add_contact(contact)

        mpw_quals = repo.calculate_mpw_qualifications()
        print(f"✓ MPW Qualifications found: {len(mpw_quals)} contacts")

        for qual in mpw_quals:
            print(f"    {qual['callsign']}: {qual['distance_miles']}mi ÷ {qual['tx_power']}W = {qual['mpw']:.0f} MPW ✓")

        assert len(mpw_quals) == 3  # 3 contacts qualify (≥1000 MPW)
        print("\n✅ MPW calculation tests passed!")

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    print("\n" + "="*80)
    print("W4GNS LOGGER - QRP POWER TRACKING IMPLEMENTATION TEST")
    print("="*80)

    try:
        test_qrp_contact_model_methods()
        test_qrp_repository_methods()
        test_qrp_with_distance_data()

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80)
        print("\nQRP Power Tracking Implementation Summary:")
        print("  ✓ Contact model QRP validation methods")
        print("  ✓ Repository QRP filtering methods")
        print("  ✓ QRP x1 and x2 award progress calculation")
        print("  ✓ MPW (Miles Per Watt) qualification tracking")
        print("  ✓ Power statistics and categorization")
        print("\nImplementation is ready for GUI integration!")
        print("="*80 + "\n")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
