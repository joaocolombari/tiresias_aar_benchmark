import unittest

from tiresias_benchmark.metrics.orientation import circular_difference_deg, normalize_yaw_360_deg


class CircularAngleTests(unittest.TestCase):
    def test_normalize_supports_negative_and_360_ranges(self):
        self.assertEqual(normalize_yaw_360_deg(-1), 359)
        self.assertEqual(normalize_yaw_360_deg(360), 0)
        self.assertEqual(normalize_yaw_360_deg(721), 1)

    def test_required_circular_error_examples(self):
        self.assertEqual(circular_difference_deg(359, 0), -1)
        self.assertEqual(circular_difference_deg(1, 360), 1)
        self.assertEqual(circular_difference_deg(2, 350), 12)
        self.assertEqual(circular_difference_deg(348, 10), -22)


if __name__ == "__main__":
    unittest.main()
