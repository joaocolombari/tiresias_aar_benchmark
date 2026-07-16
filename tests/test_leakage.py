import unittest

import numpy as np

from tiresias_benchmark.separation.leakage import leakage_coefficient_from_sdr_db, mix_cross_source_leakage


class LeakageTests(unittest.TestCase):
    def test_sdr_to_coefficient(self):
        self.assertAlmostEqual(leakage_coefficient_from_sdr_db(20), 0.1)
        self.assertEqual(leakage_coefficient_from_sdr_db("inf"), 0.0)

    def test_cross_leakage(self):
        a, b = mix_cross_source_leakage(np.ones(3), np.zeros(3), 0.5)
        np.testing.assert_allclose(a, [1, 1, 1])
        np.testing.assert_allclose(b, [0.5, 0.5, 0.5])


if __name__ == "__main__":
    unittest.main()
