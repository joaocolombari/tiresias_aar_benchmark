import unittest

from tiresias_benchmark.orientation.calibration import TareCalibration
from tiresias_benchmark.orientation.quaternion import euler_to_quaternion


class CalibrationTests(unittest.TestCase):
    def test_first_packet_is_zero_yaw(self):
        calibration = TareCalibration()
        yaw = calibration.calibrated_yaw_deg(euler_to_quaternion(0, 0, 70))
        self.assertAlmostEqual(yaw, 0.0, places=6)


if __name__ == "__main__":
    unittest.main()
