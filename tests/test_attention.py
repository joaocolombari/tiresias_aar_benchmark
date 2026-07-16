import unittest

from tiresias_benchmark.attention.gaussian import Source, compute_attention_from_yaw


class AttentionTests(unittest.TestCase):
    def test_looking_at_source_maximizes_gain(self):
        sources = [Source("a", -45), Source("b", 45)]
        gains = compute_attention_from_yaw(-45, sources, sigma_deg=20, bmax_db=10)
        self.assertGreater(gains[0].gain_linear, gains[1].gain_linear)
        self.assertAlmostEqual(gains[0].gain_db, 10.0, places=6)


if __name__ == "__main__":
    unittest.main()
