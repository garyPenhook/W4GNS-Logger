import unittest
from datetime import datetime, timezone

from src.skcc.spot_fetcher import SKCCSpot
from src.skcc.spot_adapter import SpotAdapter


class TestSpotAdapter(unittest.TestCase):
    def test_from_skcc_spot_and_back(self):
        spot = SKCCSpot(
            callsign="W1AW",
            frequency=14.05,
            mode="CW",
            grid=None,
            reporter="K4TEST",
            strength=25,
            speed=30,
            timestamp=datetime.now(timezone.utc),
            is_skcc=True,
            skcc_number="100T",
        )

        unified = SpotAdapter.from_skcc_spot(spot)
        self.assertEqual(unified.callsign, "W1AW")
        self.assertEqual(unified.frequency, 14.05)
        self.assertEqual(unified.mode, "CW")
        self.assertEqual(unified.source, "rbn")

        back = unified.to_skcc_spot()
        self.assertEqual(back.callsign, spot.callsign)
        self.assertEqual(back.frequency, spot.frequency)
        self.assertEqual(back.mode, spot.mode)
        self.assertIsNone(back.grid)
        self.assertEqual(back.reporter, spot.reporter)
        self.assertEqual(back.speed, spot.speed)

    def test_from_skcc_spot_handles_none_speed(self):
        spot = SKCCSpot(
            callsign="K4ABC",
            frequency=7.035,
            mode="CW",
            grid=None,
            reporter="TEST",
            strength=18,
            speed=None,
            timestamp=datetime.now(timezone.utc),
            is_skcc=False,
            skcc_number=None,
        )
        unified = SpotAdapter.from_skcc_spot(spot)
        self.assertIsNone(unified.wpm)


if __name__ == "__main__":
    unittest.main(verbosity=2)
