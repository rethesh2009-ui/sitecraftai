
import unittest

from backend.calculations import calculate_steel_quantity


class TestSteelCalculations(unittest.TestCase):

    def setUp(self):
        self.schedule = [
            {
                "diameter_mm": 12,
                "length_m": 10,
                "quantity": 2
            }
        ]

    def test_steel_weight(self):
        result = calculate_steel_quantity(self.schedule)
        self.assertEqual(result["total_weight_kg"], 17.78)

    def test_wastage_calculation(self):
        result = calculate_steel_quantity(self.schedule)
        self.assertEqual(
            result["estimated_weight_with_wastage_kg"],
            18.67
        )

    def test_stock_bars(self):
        result = calculate_steel_quantity(self.schedule)
        self.assertEqual(result["stock_bars_required"][12], 2)

    def test_multiple_diameters(self):
        schedule = self.schedule + [
            {
                "diameter_mm": 16,
                "length_m": 5,
                "quantity": 2
            }
        ]

        result = calculate_steel_quantity(schedule)
        self.assertEqual(len(result["steel_details"]), 2)

    def test_invalid_diameter(self):
        schedule = [
            {"diameter_mm": 0, "length_m": 10, "quantity": 2}
        ]

        with self.assertRaises(ValueError):
            calculate_steel_quantity(schedule)

    def test_invalid_wastage(self):
        with self.assertRaises(ValueError):
            calculate_steel_quantity(self.schedule, wastage=1.5)

    def test_invalid_quantity(self):
        schedule = [
            {"diameter_mm": 12, "length_m": 10, "quantity": 0}
        ]

        with self.assertRaises(ValueError):
            calculate_steel_quantity(schedule)


if __name__ == "__main__":
    unittest.main()
