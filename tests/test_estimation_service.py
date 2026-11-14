
import unittest

from backend.estimation_service import estimate_project_cost


class TestEstimationService(unittest.TestCase):

    def setUp(self):
        self.rates = {
            "cement_bags": 400,
            "sand_m3": 1500,
            "aggregate_m3": 1200,
            "bricks": 10,
            "steel_kg": 70
        }

        self.concrete = {
            "cement_bags": 20,
            "sand_volume_m3": 1.5,
            "aggregate_volume_m3": 2.5
        }

        self.brickwork = {
            "bricks_required": 100,
            "cement_bags": 5,
            "sand_volume_m3": 0.5
        }

        self.steel = {
            "estimated_weight_with_wastage_kg": 20
        }

    def test_individual_costs(self):
        result = estimate_project_cost(
            self.rates,
            concrete=self.concrete,
            brickwork=self.brickwork,
            steel=self.steel
        )

        self.assertEqual(
            set(result["individual_costs"].keys()),
            {"concrete", "brickwork", "steel"}
        )

    def test_concrete_cost(self):
        result = estimate_project_cost(
            self.rates,
            concrete=self.concrete
        )

        self.assertEqual(
            result["individual_costs"]["concrete"]["total_cost_inr"],
            13250
        )

    def test_brickwork_cost(self):
        result = estimate_project_cost(
            self.rates,
            brickwork=self.brickwork
        )

        self.assertEqual(
            result["individual_costs"]["brickwork"]["total_cost_inr"],
            3750
        )

    def test_steel_cost(self):
        result = estimate_project_cost(
            self.rates,
            steel=self.steel
        )

        self.assertEqual(
            result["individual_costs"]["steel"]["total_cost_inr"],
            1400
        )

    def test_combined_cement_quantity(self):
        result = estimate_project_cost(
            self.rates,
            concrete=self.concrete,
            brickwork=self.brickwork
        )

        self.assertEqual(
            result["combined_material_quantities"]["cement_bags"],
            25
        )

    def test_overall_cost(self):
        result = estimate_project_cost(
            self.rates,
            concrete=self.concrete,
            brickwork=self.brickwork,
            steel=self.steel
        )

        self.assertEqual(
            result["overall_cost"]["total_cost_inr"],
            18400
        )

    def test_no_activity(self):
        with self.assertRaises(ValueError):
            estimate_project_cost(self.rates)


if __name__ == "__main__":
    unittest.main()
