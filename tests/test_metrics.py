import unittest

import numpy as np

from tiresias_benchmark.metrics.audio import si_sdr_db, tir_improvement_db


class MetricsTests(unittest.TestCase):
    def test_tir_improvement(self):
        target = np.ones(10)
        interferer = np.ones(10)
        self.assertAlmostEqual(tir_improvement_db(target, interferer, 2 * target, interferer), 6.020599913, places=5)

    def test_si_sdr_finite(self):
        reference = np.array([1.0, -1.0, 1.0, -1.0])
        estimate = reference.copy()
        self.assertGreater(si_sdr_db(estimate, reference), 100)


if __name__ == "__main__":
    unittest.main()
