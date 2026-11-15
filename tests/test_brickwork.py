import unittest

from backend.calculations import calculate_brickwork


class TestBrickworkCalculations(unittest.TestCase):

    def test_wall_volume(self):
        result = calculate_brickwork(1, 1, 0.1)
        self.assertEqual(result["net_wall_volume_m3"], 0.1)

    def test_brick_quantity(self):
        result = calculate_brickwork(1, 1, 0.1)
        self.assertEqual(result["bricks_required"], 53)

    def test_opening_deduction(self):
        result = calculate_brickwork(
            1, 1, 0.1,
            openings=[(0.2, 0.2)]
        )
        self.assertEqual(result["net_wall_volume_m3"], 0.096)

    def test_mortar_calculation(self):
        result = calculate_brickwork(1, 1, 0.1)
        self.assertGreater(result["wet_mortar_volume_m3"], 0)

    def test_invalid_dimensions(self):
        with self.assertRaises(ValueError):
            calculate_brickwork(-1, 1, 0.1)

    def test_invalid_opening(self):
        with self.assertRaises(ValueError):
            calculate_brickwork(
                1, 1, 0.1,
                openings=[(2, 2)]
            )


if __name__ == "__main__":
    unittest.main()
