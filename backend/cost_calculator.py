
def calculate_material_cost(material_quantities, material_rates):
    """
    Calculate construction material costs.

    material_quantities: Dictionary of material names and quantities.
    material_rates: Dictionary of material names and rates per unit.

    Rates are assumed to be in INR.
    """

    if not isinstance(material_quantities, dict) or not material_quantities:
        raise ValueError("Material quantities must be a non-empty dictionary.")

    if not isinstance(material_rates, dict):
        raise ValueError("Material rates must be a dictionary.")

    breakdown = []
    total_cost = 0

    for material, quantity in material_quantities.items():

        if not isinstance(quantity, (int, float)) or isinstance(quantity, bool):
            raise ValueError(f"Invalid quantity for {material}.")

        if quantity < 0:
            raise ValueError(f"Quantity for {material} cannot be negative.")

        if material not in material_rates:
            raise ValueError(f"Rate missing for {material}.")

        rate = material_rates[material]

        if not isinstance(rate, (int, float)) or isinstance(rate, bool):
            raise ValueError(f"Invalid rate for {material}.")

        if rate < 0:
            raise ValueError(f"Rate for {material} cannot be negative.")

        item_cost = quantity * rate
        total_cost += item_cost

        breakdown.append({
            "material": material,
            "quantity": quantity,
            "unit_rate_inr": round(rate, 2),
            "cost_inr": round(item_cost, 2)
        })

    return {
        "breakdown": breakdown,
        "total_cost_inr": round(total_cost, 2)
    }
