#!/usr/bin/env python3
"""Quick test - emit a spot and check if it appears in the table"""
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")

from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)

from src.ui.widgets.skcc_spots_widget import SKCCSpotWidget
from src.rbn.rbn_fetcher import RBNSpot

print("\n✓ Creating widget...")
widget = SKCCSpotWidget(db=None)

print(f"✓ Bands selected: {[b for b,c in widget.band_checks.items() if c.isChecked()]}")

print("\n✓ Emitting test spot...")
spot = RBNSpot(callsign="W1AW", frequency=14.056, reporter="N4IF", strength=25, speed=28)
widget.rbn_spot_received.emit(spot)
app.processEvents()

print(f"✓ Spots in widget.spots: {len(widget.spots)}")
print(f"✓ Spots in filtered_spots: {len(widget.filtered_spots)}")
print(f"✓ Table rows: {widget.spots_table.rowCount()}")

if widget.spots_table.rowCount() > 0:
    print("\n✅ SUCCESS - Spot is in table!")
    print(
        f"   Row 0: {widget.spots_table.item(0, 0).text()} @ {widget.spots_table.item(0, 1).text()}"
    )
else:
    print("\n❌ FAILED - Spot not in table")
    if len(widget.spots) > 0:
        print(f"   Spot is in widget.spots but not displayed")
        print(f"   First spot: {widget.spots[0].callsign}")
    if len(widget.filtered_spots) == 0:
        print(f"   Spot was filtered out!")
