
import unittest

from backend.cost_calculator import calculate_material_cost


class TestMaterialCostCalculator(unittest.TestCase):

    def setUp(self):
        self.quantities = {
            "cement": 20,
            "sand": 1.5,
            "aggregate": 2.5
        }

        self.rates = {
            "cement": 400,
            "sand": 1500,
            "aggregate": 1200
        }

    def test_total_cost(self):
        result = calculate_material_cost(
            self.quantities, self.rates
        )
        self.assertEqual(result["total_cost_inr"], 13250)

    def test_material_breakdown(self):
        result = calculate_material_cost(
            self.quantities, self.rates
        )
        self.assertEqual(len(result["breakdown"]), 3)

    def test_cement_cost(self):
        result = calculate_material_cost(
            self.quantities, self.rates
        )
        self.assertEqual(
            result["breakdown"][0]["cost_inr"], 8000
        )

    def test_missing_rate(self):
        rates = {"cement": 400}
        with self.assertRaises(ValueError):
            calculate_material_cost(self.quantities, rates)

    def test_negative_quantity(self):
        quantities = {"cement": -5}
        rates = {"cement": 400}
        with self.assertRaises(ValueError):
            calculate_material_cost(quantities, rates)

    def test_negative_rate(self):
        rates = {"cement": -400}
        quantities = {"cement": 20}
        with self.assertRaises(ValueError):
            calculate_material_cost(quantities, rates)

    def test_empty_quantities(self):
        with self.assertRaises(ValueError):
            calculate_material_cost({}, {})


if __name__ == "__main__":
    unittest.main()
