import unittest

from tiresias_benchmark.orientation.quaternion import (
    angular_distance_deg,
    euler_to_quaternion,
    quaternion_to_euler,
    source_relative_angle,
    wrap_angle_deg,
)


class QuaternionTests(unittest.TestCase):
    def test_yaw_round_trip(self):
        q = euler_to_quaternion(0, 0, 45)
        self.assertAlmostEqual(quaternion_to_euler(*q)[2], 45.0, places=6)

    def test_wrap(self):
        self.assertAlmostEqual(wrap_angle_deg(181), -179)
        self.assertAlmostEqual(wrap_angle_deg(-181), 179)
        self.assertAlmostEqual(angular_distance_deg(179, -179), 2)

    def test_source_relative_angle(self):
        q = euler_to_quaternion(0, 0, 45)
        self.assertAlmostEqual(source_relative_angle(q, [1, 1, 0]), 0.0, places=5)


if __name__ == "__main__":
    unittest.main()
