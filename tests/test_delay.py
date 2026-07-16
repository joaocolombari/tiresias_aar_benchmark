import unittest

import numpy as np

from tiresias_benchmark.telemetry.replay import delayed_yaw_series


class DelayTests(unittest.TestCase):
    def test_hold_delay(self):
        t = np.array([0.0, 0.1, 0.2, 0.3])
        yaw = np.array([0.0, 10.0, 20.0, 30.0])
        delayed = delayed_yaw_series(t, yaw, 100)
        np.testing.assert_allclose(delayed, [0.0, 0.0, 10.0, 20.0])


if __name__ == "__main__":
    unittest.main()
