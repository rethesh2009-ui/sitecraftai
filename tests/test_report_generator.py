
import unittest
import os
import tempfile

from backend.report_generator import (
    create_project_report,
    format_project_report,
    save_project_report
)


class TestReportGenerator(unittest.TestCase):

    def setUp(self):
        self.estimation = {
            "individual_costs": {
                "concrete": {
                    "material_quantities": {
                        "cement_bags": 20
                    },
                    "cost_breakdown": [
                        {
                            "material": "cement_bags",
                            "quantity": 20,
                            "unit_rate_inr": 400,
                            "cost_inr": 8000
                        }
                    ],
                    "total_cost_inr": 8000
                }
            },
            "combined_material_quantities": {
                "cement_bags": 20
            },
            "overall_cost": {
                "breakdown": [
                    {
                        "material": "cement_bags",
                        "quantity": 20,
                        "unit_rate_inr": 400,
                        "cost_inr": 8000
                    }
                ],
                "total_cost_inr": 8000
            }
        }

        self.report = create_project_report(
            "Test Construction Project",
            self.estimation
        )

    def test_project_name(self):
        self.assertEqual(
            self.report["project_name"],
            "Test Construction Project"
        )

    def test_overall_cost(self):
        self.assertEqual(self.report["overall_cost_inr"], 8000)

    def test_combined_quantities(self):
        self.assertEqual(
            self.report["combined_material_quantities"]["cement_bags"],
            20
        )

    def test_empty_project_name(self):
        with self.assertRaises(ValueError):
            create_project_report("", self.estimation)

    def test_invalid_estimation(self):
        with self.assertRaises(ValueError):
            create_project_report("Test Project", {})

    def test_format_report(self):
        text = format_project_report(self.report)

        self.assertIn("SITEQUOTA PROJECT REPORT", text)
        self.assertIn("Test Construction Project", text)
        self.assertIn("Rs. 8000.00", text)

    def test_save_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "report.txt")

            saved_path = save_project_report(self.report, path)

            self.assertTrue(os.path.exists(saved_path))

            with open(saved_path, encoding="utf-8") as file:
                content = file.read()

            self.assertIn("SITEQUOTA PROJECT REPORT", content)


if __name__ == "__main__":
    unittest.main()
