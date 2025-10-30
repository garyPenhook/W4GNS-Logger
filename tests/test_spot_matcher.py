import unittest
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

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


class _FakeSession:
    """Fake database session for testing"""
    def __init__(self, contacts_by_callsign):
        self._contacts_by_callsign = contacts_by_callsign

    def query(self, *args):
        """Return a fake query object"""
        return _FakeQuery(self._contacts_by_callsign)

    def close(self):
        """No-op close"""
        pass


class _FakeQuery:
    """Fake SQLAlchemy query for testing"""
    def __init__(self, contacts_by_callsign):
        self._contacts_by_callsign = contacts_by_callsign
        self._callsign_filter = None

    def filter(self, condition):
        """Extract callsign from filter and store it"""
        # The condition will be a boolean expression like: func.upper(Contact.callsign) == "K4TEST"
        # We need to extract the callsign value
        # Since we can't easily parse the SQLAlchemy expression, we'll use a hack:
        # Store the condition and evaluate it in scalar()
        self._condition = condition
        return self

    def scalar(self):
        """Return the max date for the filtered callsign"""
        # Try to extract callsign from the condition by evaluating its right side
        # The condition is: func.upper(Contact.callsign) == "CALLSIGN"
        # We'll check each contact to see if it matches
        if hasattr(self, '_condition'):
            # Extract the callsign by getting the right operand
            # This is a hack but works for testing
            try:
                # The condition is a BinaryExpression with right side being the callsign
                callsign = str(self._condition.right.value)
                contact = self._contacts_by_callsign.get(callsign)
                if contact:
                    return contact.qso_date
            except:
                pass
        return None


class _FakeDB:
    def __init__(self, contacts):
        self._contacts = contacts
        self._contacts_by_callsign = {c.callsign: c for c in contacts}

    def get_all_contacts(self):
        return self._contacts

    def get_session(self):
        """Return a fake session for testing"""
        return _FakeSession(self._contacts_by_callsign)


class TestSpotMatcher(unittest.TestCase):
    def test_matcher_recent_and_worked(self):
        # Prepare fake DB contacts
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y%m%d")
        forty_days_ago = (now - timedelta(days=40)).strftime("%Y%m%d")

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
            timestamp=datetime.now(timezone.utc),
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
            timestamp=datetime.now(timezone.utc),
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
            timestamp=datetime.now(timezone.utc),
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
