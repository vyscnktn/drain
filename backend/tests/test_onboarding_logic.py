import unittest
from app.api.endpoints.onboarding import get_calibration_levels

class TestOnboardingLogic(unittest.TestCase):
    def test_calibration_levels_a1(self):
        self.assertEqual(get_calibration_levels("A1"), ["A1", "A1", "A2"])

    def test_calibration_levels_a2(self):
        self.assertEqual(get_calibration_levels("A2"), ["A1", "A2", "B1"])

    def test_calibration_levels_b1(self):
        self.assertEqual(get_calibration_levels("B1"), ["A2", "B1", "B2"])

    def test_calibration_levels_b2(self):
        self.assertEqual(get_calibration_levels("B2"), ["B1", "B2", "C1"])

    def test_calibration_levels_c1(self):
        self.assertEqual(get_calibration_levels("C1"), ["B2", "C1", "C1"])

    def test_calibration_levels_fallback_on_invalid(self):
        self.assertEqual(get_calibration_levels("UNKNOWN"), ["A1", "A2", "B1"])
        self.assertEqual(get_calibration_levels(""), ["A1", "A2", "B1"])

if __name__ == '__main__':
    unittest.main()
