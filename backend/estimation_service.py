
from backend.cost_calculator import calculate_material_cost


def estimate_project_cost(
    material_rates,
    concrete=None,
    brickwork=None,
    steel=None
):
    """
    Calculate individual activity costs and overall project cost.

    Rates:
        cement_bags: INR per bag
        sand_m3: INR per cubic metre
        aggregate_m3: INR per cubic metre
        bricks: INR per brick
        steel_kg: INR per kilogram
    """

    activities = {}

    # 1. Concrete quantities
    if concrete is not None:
        activities["concrete"] = {
            "cement_bags": concrete["cement_bags"],
            "sand_m3": concrete["sand_volume_m3"],
            "aggregate_m3": concrete["aggregate_volume_m3"]
        }

    # 2. Brickwork quantities
    if brickwork is not None:
        activities["brickwork"] = {
            "bricks": brickwork["bricks_required"],
            "cement_bags": brickwork["cement_bags"],
            "sand_m3": brickwork["sand_volume_m3"]
        }

    # 3. Steel quantities
    if steel is not None:
        activities["steel"] = {
            "steel_kg": steel["estimated_weight_with_wastage_kg"]
        }

    if not activities:
        raise ValueError("At least one activity must be provided.")

    # Calculate individual activity costs
    individual_costs = {}

    for activity, quantities in activities.items():
        result = calculate_material_cost(
            quantities,
            material_rates
        )

        individual_costs[activity] = {
            "material_quantities": quantities,
            "cost_breakdown": result["breakdown"],
            "total_cost_inr": result["total_cost_inr"]
        }

    # Combine quantities of repeated materials
    combined_quantities = {}

    for quantities in activities.values():
        for material, quantity in quantities.items():
            combined_quantities[material] = (
                combined_quantities.get(material, 0) + quantity
            )

    # Calculate overall project cost
    overall_cost = calculate_material_cost(
        combined_quantities,
        material_rates
    )

    return {
        "individual_costs": individual_costs,
        "combined_material_quantities": combined_quantities,
        "overall_cost": overall_cost
    }
