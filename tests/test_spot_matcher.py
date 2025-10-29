import unittest
from types import SimpleNamespace
from datetime import datetime, timedelta

from src.ui.spot_matcher import SpotMatcher
from src.skcc.spot_fetcher import SKCCSpot


class _FakeConfig:
    def __init__(self):
        self._data = {
            "spots.highlight_worked": True,
            "spots.highlight_recent_days": 30,
            "spots.enable_matching": True,
        }

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value


class _FakeDB:
    def __init__(self, contacts):
        self._contacts = contacts

    def get_all_contacts(self):
        return self._contacts


class TestSpotMatcher(unittest.TestCase):
    def test_matcher_recent_and_worked(self):
        # Prepare fake DB contacts
        today = datetime.utcnow().strftime("%Y%m%d")
        forty_days_ago = (datetime.utcnow() - timedelta(days=40)).strftime("%Y%m%d")

        contacts = [
            SimpleNamespace(callsign="K4TEST", qso_date=today),
            SimpleNamespace(callsign="W1AW", qso_date=forty_days_ago),
        ]

        # Using a lightweight fake DB; ignore type narrowing for test
        matcher = SpotMatcher(db=_FakeDB(contacts), config_manager=_FakeConfig())  # type: ignore[arg-type]

        recent_spot = SKCCSpot(
            callsign="K4TEST",
            frequency=14.05,
            mode="CW",
            grid=None,
            reporter="RBN",
            strength=20,
            speed=25,
            timestamp=datetime.utcnow(),
            is_skcc=True,
            skcc_number="12345",
        )
        worked_spot = SKCCSpot(
            callsign="W1AW",
            frequency=7.035,
            mode="CW",
            grid=None,
            reporter="RBN",
            strength=18,
            speed=24,
            timestamp=datetime.utcnow(),
            is_skcc=True,
            skcc_number="100T",
        )
        new_spot = SKCCSpot(
            callsign="N0CALL",
            frequency=7.01,
            mode="CW",
            grid=None,
            reporter="RBN",
            strength=15,
            speed=20,
            timestamp=datetime.utcnow(),
            is_skcc=False,
            skcc_number=None,
        )

        recent_match = matcher.match_spot(recent_spot)
        worked_match = matcher.match_spot(worked_spot)
        new_match = matcher.match_spot(new_spot)

        self.assertEqual(recent_match.match_type, "RECENT")
        self.assertEqual(worked_match.match_type, "WORKED")
        self.assertEqual(new_match.match_type, "NONE")

        # Check colors
        self.assertIsNotNone(matcher.get_highlight_color(recent_match))
        self.assertIsNotNone(matcher.get_highlight_color(worked_match))
        self.assertIsNone(matcher.get_highlight_color(new_match))


if __name__ == "__main__":
    unittest.main(verbosity=2)
