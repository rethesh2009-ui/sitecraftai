
from backend.calculations import (
    calculate_concrete_materials,
    calculate_brickwork,
    calculate_steel_quantity
)

from backend.estimation_service import estimate_project_cost

from backend.report_generator import (
    create_project_report,
    format_project_report,
    save_project_report
)
from backend.pdf_generator import generate_project_pdf

# 1. Calculate concrete
concrete = calculate_concrete_materials(
    length=5,
    width=4,
    thickness=0.15
)


# 2. Calculate brickwork
brickwork = calculate_brickwork(
    length=5,
    height=3,
    thickness=0.20
)


# 3. Calculate steel
steel = calculate_steel_quantity(
    bar_schedule=[
        {
            "diameter_mm": 12,
            "length_m": 10,
            "quantity": 20
        },
        {
            "diameter_mm": 16,
            "length_m": 8,
            "quantity": 10
        }
    ]
)


# 4. Define sample material rates (INR)
material_rates = {
    "cement_bags": 400,
    "sand_m3": 1500,
    "aggregate_m3": 1200,
    "bricks": 10,
    "steel_kg": 70
}


# 5. Estimate individual and overall costs
estimation = estimate_project_cost(
    material_rates=material_rates,
    concrete=concrete,
    brickwork=brickwork,
    steel=steel
)


# 6. Generate project report
report = create_project_report(
    project_name="SiteQuota Sample Construction",
    estimation_result=estimation
)


# 7. Display report
print(format_project_report(report))


# 8. Save report
save_project_report(
    report,
    "sitequota_sample_report.txt"
)

print("\nReport saved successfully!")
# Generate PDF report
generate_project_pdf(
    report,
    "sitequota_sample_report.pdf"
)

print("PDF report generated successfully!")
