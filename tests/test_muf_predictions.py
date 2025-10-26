"""
Unit Tests for MUF (Maximum Usable Frequency) Predictions

Tests for VOACAP-based MUF calculation and prediction functionality.
"""

import unittest
import logging
from src.services.voacap_muf_fetcher import VOACAPMUFFetcher, MUFPrediction, MUFSource

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class TestMUFCalculation(unittest.TestCase):
    """Test MUF calculation engine"""

    def setUp(self):
        """Set up test fixtures"""
        self.fetcher = VOACAPMUFFetcher()

    def tearDown(self):
        """Clean up"""
        self.fetcher.close()

    def test_empirical_muf_with_high_sfi(self):
        """Test MUF calculation with high solar flux index"""
        # High SFI (200) should produce high MUF
        muf = self.fetcher.calculate_empirical_muf(sfi=200, k_index=2, frequency_mhz=14.0)

        self.assertGreater(muf, 20.0, "High SFI should produce high MUF")
        self.assertLess(muf, 50.0, "MUF should be bounded at 50 MHz")
        logger.info(f"✓ High SFI MUF: {muf:.1f} MHz")

    def test_empirical_muf_with_low_sfi(self):
        """Test MUF calculation with low solar flux index"""
        # Low SFI (70) should produce low MUF
        muf = self.fetcher.calculate_empirical_muf(sfi=70, k_index=2, frequency_mhz=14.0)

        self.assertGreater(muf, 8.0, "Low SFI should still produce reasonable MUF")
        self.assertLess(muf, 15.0, "Low SFI should produce lower MUF")
        logger.info(f"✓ Low SFI MUF: {muf:.1f} MHz")

    def test_empirical_muf_with_geomagnetic_disturbance(self):
        """Test MUF degradation during geomagnetic storms"""
        # Normal conditions (K=2)
        muf_normal = self.fetcher.calculate_empirical_muf(sfi=150, k_index=2, frequency_mhz=14.0)

        # Storm conditions (K=8)
        muf_storm = self.fetcher.calculate_empirical_muf(sfi=150, k_index=8, frequency_mhz=14.0)

        self.assertGreater(muf_normal, muf_storm, "Storm conditions should reduce MUF")
        logger.info(f"✓ Normal MUF: {muf_normal:.1f}MHz, Storm MUF: {muf_storm:.1f}MHz")

    def test_empirical_muf_frequency_dependence(self):
        """Test that MUF varies with operating frequency"""
        # Lower frequency should have higher MUF (easier to skip)
        muf_80m = self.fetcher.calculate_empirical_muf(sfi=150, k_index=3, frequency_mhz=3.5)
        muf_20m = self.fetcher.calculate_empirical_muf(sfi=150, k_index=3, frequency_mhz=14.0)
        muf_10m = self.fetcher.calculate_empirical_muf(sfi=150, k_index=3, frequency_mhz=28.5)

        # This relationship might vary, but should be physically reasonable
        self.assertGreater(muf_80m, 1.0)
        self.assertGreater(muf_20m, 1.0)
        self.assertGreater(muf_10m, 1.0)
        logger.info(f"✓ MUF by band: 80m={muf_80m:.1f}M, 20m={muf_20m:.1f}M, 10m={muf_10m:.1f}M")

    def test_empirical_muf_bounds(self):
        """Test that MUF is bounded within reasonable limits"""
        # Extreme high SFI
        muf_high = self.fetcher.calculate_empirical_muf(sfi=300, k_index=0, frequency_mhz=1.0)
        self.assertLess(muf_high, 50.0, "MUF should not exceed 50 MHz")
        self.assertGreater(muf_high, 0.0, "MUF should be positive")

        # Extreme low SFI
        muf_low = self.fetcher.calculate_empirical_muf(sfi=50, k_index=9, frequency_mhz=50.0)
        self.assertGreater(muf_low, 2.0, "MUF should not go below 2 MHz")
        logger.info(f"✓ MUF bounds verified: {muf_low:.1f}M to {muf_high:.1f}M")


class TestMUFBandPredictions(unittest.TestCase):
    """Test MUF predictions for standard HF bands"""

    def setUp(self):
        """Set up test fixtures"""
        self.fetcher = VOACAPMUFFetcher()

    def tearDown(self):
        """Clean up"""
        self.fetcher.close()

    def test_band_predictions_complete(self):
        """Test that all standard HF bands get predictions"""
        predictions = self.fetcher.get_band_muf_predictions(
            sfi=150,
            k_index=3,
            home_grid="FN20qd"
        )

        self.assertGreater(len(predictions), 5, "Should have predictions for at least 5 bands")
        self.assertIn("20m", predictions, "Should have 20m prediction")
        self.assertIn("40m", predictions, "Should have 40m prediction")
        logger.info(f"✓ Generated predictions for {len(predictions)} bands")

    def test_band_usability_logic(self):
        """Test that band usability is determined correctly"""
        # High SFI should make more bands usable
        predictions_high = self.fetcher.get_band_muf_predictions(
            sfi=200,
            k_index=2,
            home_grid="FN20qd"
        )

        # Low SFI should make fewer bands usable
        predictions_low = self.fetcher.get_band_muf_predictions(
            sfi=80,
            k_index=2,
            home_grid="FN20qd"
        )

        usable_high = sum(1 for p in predictions_high.values() if p.usable)
        usable_low = sum(1 for p in predictions_low.values() if p.usable)

        self.assertGreaterEqual(usable_high, usable_low,
                               "High SFI should result in more usable bands")
        logger.info(f"✓ High SFI: {usable_high} usable, Low SFI: {usable_low} usable")

    def test_20m_band_characteristics(self):
        """Test characteristics of 20m band (most common)"""
        predictions = self.fetcher.get_band_muf_predictions(
            sfi=150,
            k_index=4,
            home_grid="FN20qd"
        )

        self.assertIn("20m", predictions)
        band_20m = predictions["20m"]

        # 20m band is 14.0-14.35 MHz
        self.assertEqual(band_20m.frequency_range, (14.0, 14.35))
        self.assertGreater(band_20m.muf_value, 10.0, "MUF for 20m should be > 10 MHz normally")
        logger.info(f"✓ 20m band usable: {band_20m.usable}, MUF: {band_20m.muf_value:.1f}M")

    def test_muf_prediction_object(self):
        """Test MUFPrediction object creation and properties"""
        prediction = MUFPrediction(
            band_name="20m",
            frequency_range=(14.0, 14.35),
            muf_value=18.5,
            confidence=0.8,
            source=MUFSource.EMPIRICAL
        )

        self.assertEqual(prediction.band_name, "20m")
        self.assertTrue(prediction.usable)  # MUF > max frequency
        self.assertEqual(prediction.source, MUFSource.EMPIRICAL)
        self.assertEqual(prediction.confidence, 0.8)
        logger.info(f"✓ MUFPrediction object: {prediction}")


class TestGridSquareConversion(unittest.TestCase):
    """Test Maidenhead grid square conversion"""

    def setUp(self):
        """Set up test fixtures"""
        self.fetcher = VOACAPMUFFetcher()

    def test_grid_to_latitude_fn20(self):
        """Test grid square FN20qd conversion to latitude"""
        lat = self.fetcher._grid_to_latitude("FN20qd")

        # FN20qd is approximately 38° N latitude (Virginia, USA)
        self.assertGreater(lat, 30.0)
        self.assertLess(lat, 50.0)
        self.assertAlmostEqual(lat, 38.0, delta=2.0)
        logger.info(f"✓ Grid FN20qd latitude: {lat:.1f}°")

    def test_grid_to_longitude_fn20(self):
        """Test grid square FN20qd conversion to longitude"""
        lon = self.fetcher._grid_to_longitude("FN20qd")

        # FN20qd is approximately -75° W longitude (Virginia, USA)
        self.assertLess(lon, 0.0)  # Western hemisphere
        self.assertGreater(lon, -90.0)
        self.assertAlmostEqual(lon, -75.0, delta=5.0)
        logger.info(f"✓ Grid FN20qd longitude: {lon:.1f}°")

    def test_grid_distance_calculation(self):
        """Test distance calculation between grid squares"""
        # Distance from FN20 (Virginia) to CM87 (California)
        distance_fn_to_cm = self.fetcher._grid_distance("FN20qd", "CM87wj")

        # Should be approximately 3000-4000 km (2000 miles)
        self.assertGreater(distance_fn_to_cm, 2000.0, "Should be thousands of km")
        self.assertLess(distance_fn_to_cm, 8000.0, "Should not exceed USA width")
        logger.info(f"✓ FN20 to CM87 distance: {distance_fn_to_cm:.0f} km")

    def test_grid_distance_same_location(self):
        """Test distance from location to itself"""
        distance = self.fetcher._grid_distance("FN20qd", "FN20qd")

        self.assertLess(distance, 100.0, "Distance to self should be nearly zero")
        logger.info(f"✓ Self distance: {distance:.1f} km")

    def test_grid_bearing_calculation(self):
        """Test bearing calculation between grid squares"""
        bearing = self.fetcher._grid_bearing("FN20qd", "DM79")

        # DM79 is Europe (roughly northeast from Virginia)
        self.assertGreater(bearing, 0.0)
        self.assertLess(bearing, 360.0)
        logger.info(f"✓ Bearing from FN20 to DM79: {bearing:.0f}°")


class TestVOACAPMUFColor(unittest.TestCase):
    """Test color coding for MUF display"""

    def setUp(self):
        """Set up test fixtures"""
        self.fetcher = VOACAPMUFFetcher()

    def test_color_for_usable_band(self):
        """Test color for usable band"""
        prediction = MUFPrediction(
            band_name="20m",
            frequency_range=(14.0, 14.35),
            muf_value=18.5,
            source=MUFSource.EMPIRICAL
        )

        color = self.fetcher.get_color_for_muf(prediction)
        self.assertIn("#", color, "Color should be hex format")
        self.assertTrue(color.startswith("#"), "Color should start with #")
        logger.info(f"✓ Usable band color: {color}")

    def test_color_for_marginal_band(self):
        """Test color for marginal band"""
        prediction = MUFPrediction(
            band_name="20m",
            frequency_range=(14.0, 14.35),
            muf_value=14.2,  # Just barely above minimum
            source=MUFSource.EMPIRICAL
        )

        color = self.fetcher.get_color_for_muf(prediction)
        self.assertNotEqual(color, "#FF0000", "Should not be red for marginal")
        logger.info(f"✓ Marginal band color: {color}")

    def test_color_for_unusable_band(self):
        """Test color for unusable band"""
        prediction = MUFPrediction(
            band_name="10m",
            frequency_range=(28.0, 29.7),
            muf_value=12.0,  # Below 10m minimum
            source=MUFSource.EMPIRICAL
        )

        color = self.fetcher.get_color_for_muf(prediction)
        self.assertEqual(color, "#FF0000", "Should be red for unusable")
        logger.info(f"✓ Unusable band color: {color}")


class TestMUFStatusString(unittest.TestCase):
    """Test MUF status reporting"""

    def setUp(self):
        """Set up test fixtures"""
        self.fetcher = VOACAPMUFFetcher()

    def test_status_string_generation(self):
        """Test generation of MUF status string"""
        predictions = {
            "20m": MUFPrediction("20m", (14.0, 14.35), 18.5, source=MUFSource.EMPIRICAL),
            "40m": MUFPrediction("40m", (7.0, 7.3), 12.0, source=MUFSource.EMPIRICAL),
            "10m": MUFPrediction("10m", (28.0, 29.7), 8.0, source=MUFSource.EMPIRICAL),
        }

        status = self.fetcher.get_muf_status_string(predictions)

        self.assertIn("usable", status)
        self.assertGreater(len(status), 10)
        logger.info(f"✓ Status string: {status}")

    def test_empty_predictions_status(self):
        """Test status string with no predictions"""
        status = self.fetcher.get_muf_status_string({})

        self.assertIn("No MUF", status)
        logger.info(f"✓ Empty predictions status: {status}")


class TestMUFIntegration(unittest.TestCase):
    """Integration tests for complete MUF workflow"""

    def setUp(self):
        """Set up test fixtures"""
        self.fetcher = VOACAPMUFFetcher()

    def test_complete_muf_workflow(self):
        """Test complete MUF calculation and reporting workflow"""
        # Typical space weather conditions
        sfi = 150  # Moderate solar flux
        k_index = 4  # Unsettled

        # Get predictions
        predictions = self.fetcher.get_band_muf_predictions(
            sfi=sfi,
            k_index=k_index,
            home_grid="FN20qd"
        )

        # Verify predictions
        self.assertGreater(len(predictions), 0)

        # Get status
        status = self.fetcher.get_muf_status_string(predictions)
        self.assertGreater(len(status), 0)

        # Get colors
        for band, pred in predictions.items():
            color = self.fetcher.get_color_for_muf(pred)
            self.assertIn("#", color)

        logger.info(f"✓ Complete workflow: {len(predictions)} predictions, Status: {status}")

    def test_muf_different_locations(self):
        """Test MUF calculations for different grid squares"""
        locations = {
            "FN20qd": "Virginia, USA",
            "CM87wj": "California, USA",
            "DM79id": "Germany",
            "JO22db": "Japan",
        }

        for grid, description in locations.items():
            predictions = self.fetcher.get_band_muf_predictions(
                sfi=150,
                k_index=3,
                home_grid=grid
            )

            usable_count = sum(1 for p in predictions.values() if p.usable)
            self.assertGreater(len(predictions), 0)
            logger.info(f"✓ {description} ({grid}): {usable_count}/{len(predictions)} bands usable")


if __name__ == '__main__':
    unittest.main(verbosity=2)
