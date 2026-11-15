
from datetime import date


def create_project_report(project_name, estimation_result):
    """
    Create a structured report from project estimation results.
    """

    if not isinstance(project_name, str) or not project_name.strip():
        raise ValueError("Project name cannot be empty.")

    if not isinstance(estimation_result, dict):
        raise ValueError("Invalid estimation result.")

    required_keys = {
        "individual_costs",
        "combined_material_quantities",
        "overall_cost"
    }

    if not required_keys.issubset(estimation_result):
        raise ValueError("Estimation result is incomplete.")

    return {
        "project_name": project_name.strip(),
        "report_date": date.today().isoformat(),
        "activities": estimation_result["individual_costs"],
        "combined_material_quantities":
            estimation_result["combined_material_quantities"],
        "overall_cost_inr":
            estimation_result["overall_cost"]["total_cost_inr"],
        "overall_cost_breakdown":
            estimation_result["overall_cost"]["breakdown"]
    }


def format_project_report(report):
    """
    Convert the structured project report into readable text.
    """

    lines = [
        "=" * 55,
        "                 SITEQUOTA PROJECT REPORT",
        "=" * 55,
        "",
        f"Project Name: {report['project_name']}",
        f"Report Date: {report['report_date']}",
        "",
        "-" * 55,
        "INDIVIDUAL ACTIVITY ESTIMATES",
        "-" * 55
    ]

    # Individual activity costs
    for activity, details in report["activities"].items():

        lines.append("")
        lines.append(activity.upper())

        for item in details["cost_breakdown"]:
            lines.append(
                f"  {item['material']}: "
                f"{item['quantity']} x "
                f"Rs. {item['unit_rate_inr']:.2f} = "
                f"Rs. {item['cost_inr']:.2f}"
            )

        lines.append(
            f"  Activity Total: Rs. "
            f"{details['total_cost_inr']:.2f}"
        )

    # Combined material quantities
    lines.extend([
        "",
        "-" * 55,
        "COMBINED MATERIAL QUANTITIES",
        "-" * 55
    ])

    for material, quantity in (
        report["combined_material_quantities"].items()
    ):
        formatted_quantity = (
            f"{quantity:,.4f}".rstrip("0").rstrip(".")
            if isinstance(quantity, float)
            else f"{quantity:,}"
        )

        lines.append(f"{material}: {formatted_quantity}")

    # Overall material cost breakdown
    lines.extend([
        "",
        "-" * 55,
        "OVERALL MATERIAL COST BREAKDOWN",
        "-" * 55
    ])

    for item in report["overall_cost_breakdown"]:
        lines.append(
            f"{item['material']}: "
            f"Rs. {item['cost_inr']:,.2f}"
        )

    # Final project cost
    lines.extend([
        "",
        "=" * 55,
        f"OVERALL PROJECT MATERIAL COST: "
        f"Rs. {report['overall_cost_inr']:,.2f}",
        "=" * 55,
        "",
        "Note: This is an estimated material cost.",
        "Labour, transport, equipment and other expenses",
        "are not included."
    ])

    return "\n".join(lines)


def save_project_report(report, file_path):
    """
    Save the formatted project report as a text file.
    """

    if not isinstance(file_path, str) or not file_path.strip():
        raise ValueError("A valid file path is required.")

    report_text = format_project_report(report)

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(report_text)

    return file_path
