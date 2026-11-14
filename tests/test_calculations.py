
import unittest

from backend.calculations import calculate_concrete_materials


class TestConcreteCalculations(unittest.TestCase):

    def test_concrete_volume(self):
        result = calculate_concrete_materials(5, 4, 0.15)
        self.assertEqual(result["wet_concrete_volume_m3"], 3.0)

    def test_cement_bags(self):
        result = calculate_concrete_materials(5, 4, 0.15)
        self.assertEqual(result["cement_bags"], 20)

    def test_invalid_dimensions(self):
        with self.assertRaises(ValueError):
            calculate_concrete_materials(-5, 4, 0.15)

    def test_invalid_wastage(self):
        with self.assertRaises(ValueError):
            calculate_concrete_materials(5, 4, 0.15, wastage=1.5)

    def test_invalid_mix_ratio(self):
        with self.assertRaises(ValueError):
            calculate_concrete_materials(5, 4, 0.15, mix_ratio=(1, 0, 4))


if __name__ == "__main__":
    unittest.main()
