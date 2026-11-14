
import math


def calculate_concrete_materials(
    length,
    width,
    thickness,
    mix_ratio=(1, 2, 4),
    wastage=0.05
):
    """
    Calculate cement, sand and aggregate requirements.

    Dimensions must be in metres.
    Default mix ratio: 1:2:4
    Default dry volume factor: 1.54
    """

    # Validate dimensions
    if length <= 0 or width <= 0 or thickness <= 0:
        raise ValueError("All dimensions must be greater than zero.")

    if not 0 <= wastage <= 1:
        raise ValueError("Wastage must be between 0 and 1.")

    if len(mix_ratio) != 3 or any(x <= 0 for x in mix_ratio):
        raise ValueError("Mix ratio must contain three positive values.")

    # Calculate wet concrete volume
    wet_volume = length * width * thickness

    # Add wastage allowance
    adjusted_volume = wet_volume * (1 + wastage)

    # Calculate dry volume
    dry_volume = adjusted_volume * 1.54

    # Extract mix proportions
    cement_ratio, sand_ratio, aggregate_ratio = mix_ratio
    total_ratio = sum(mix_ratio)

    # Calculate individual material volumes
    cement_volume = dry_volume * cement_ratio / total_ratio
    sand_volume = dry_volume * sand_ratio / total_ratio
    aggregate_volume = dry_volume * aggregate_ratio / total_ratio

    # Cement conversion
    cement_density = 1440  # kg/m³
    cement_bag_weight = 50  # kg

    cement_weight = cement_volume * cement_density
    cement_bags = math.ceil(cement_weight / cement_bag_weight)

    return {
        "wet_concrete_volume_m3": round(wet_volume, 3),
        "dry_material_volume_m3": round(dry_volume, 3),
        "cement_volume_m3": round(cement_volume, 3),
        "cement_weight_kg": round(cement_weight, 2),
        "cement_bags": cement_bags,
        "sand_volume_m3": round(sand_volume, 3),
        "aggregate_volume_m3": round(aggregate_volume, 3),
        "mix_ratio": mix_ratio,
        "wastage_percentage": wastage * 100
    }


if __name__ == "__main__":

    result = calculate_concrete_materials(
        length=5,
        width=4,
        thickness=0.15,
        mix_ratio=(1, 2, 4),
        wastage=0.05
    )

    print("\n===== SITEQUOTA CONCRETE ESTIMATION =====")

    for material, quantity in result.items():
        print(f"{material}: {quantity}")


def calculate_brickwork(
    length,
    height,
    thickness,
    brick_size=(0.19, 0.09, 0.09),
    mortar_joint=0.01,
    openings=None,
    wastage=0.05,
    mortar_ratio=(1, 6)
):
    """
    Estimate bricks, cement and sand for brickwork.

    Dimensions are in metres.
    Brick size defaults to 190 x 90 x 90 mm.
    Mortar joint defaults to 10 mm.
    Mortar ratio defaults to 1:6.
    """

    # Validate wall dimensions
    if length <= 0 or height <= 0 or thickness <= 0:
        raise ValueError("Wall dimensions must be positive.")

    if len(brick_size) != 3 or any(x <= 0 for x in brick_size):
        raise ValueError("Brick dimensions must be positive.")

    if mortar_joint <= 0:
        raise ValueError("Mortar joint must be positive.")

    if not 0 <= wastage <= 1:
        raise ValueError("Wastage must be between 0 and 1.")

    if len(mortar_ratio) != 2 or any(x <= 0 for x in mortar_ratio):
        raise ValueError("Mortar ratio must contain two positive values.")

    # Calculate gross wall volume
    gross_volume = length * height * thickness

    # Calculate opening deductions
    opening_volume = 0

    if openings is not None:
        for opening in openings:
            if len(opening) != 2:
                raise ValueError("Each opening must have width and height.")

            opening_width, opening_height = opening

            if opening_width <= 0 or opening_height <= 0:
                raise ValueError("Opening dimensions must be positive.")

            if opening_width > length or opening_height > height:
                raise ValueError("Opening cannot exceed wall dimensions.")

            opening_volume += (
                opening_width * opening_height * thickness
            )

    net_volume = gross_volume - opening_volume

    if net_volume <= 0:
        raise ValueError("Openings must be smaller than the wall.")

    # Calculate brick module volume including mortar joints
    brick_length, brick_width, brick_height = brick_size

    module_volume = (
        (brick_length + mortar_joint)
        * (brick_width + mortar_joint)
        * (brick_height + mortar_joint)
    )

    actual_brick_volume = brick_length * brick_width * brick_height

    # Calculate brick quantities
    theoretical_bricks = net_volume / module_volume

    bricks_required = math.ceil(
        theoretical_bricks * (1 + wastage)
    )

    # Calculate wet mortar volume
    wet_mortar = max(
        0,
        net_volume - theoretical_bricks * actual_brick_volume
    )

    # Convert wet mortar to dry material volume
    dry_mortar = wet_mortar * 1.33

    # Calculate cement and sand
    cement_ratio, sand_ratio = mortar_ratio
    total_ratio = cement_ratio + sand_ratio

    cement_volume = dry_mortar * cement_ratio / total_ratio
    sand_volume = dry_mortar * sand_ratio / total_ratio

    # Convert cement volume into bags
    cement_weight = cement_volume * 1440
    cement_bags = math.ceil(cement_weight / 50)

    return {
        "gross_wall_volume_m3": round(gross_volume, 3),
        "opening_volume_m3": round(opening_volume, 3),
        "net_wall_volume_m3": round(net_volume, 3),
        "bricks_required": bricks_required,
        "wet_mortar_volume_m3": round(wet_mortar, 4),
        "dry_mortar_volume_m3": round(dry_mortar, 4),
        "cement_volume_m3": round(cement_volume, 4),
        "cement_weight_kg": round(cement_weight, 2),
        "cement_bags": cement_bags,
        "sand_volume_m3": round(sand_volume, 4),
        "mortar_ratio": mortar_ratio,
        "wastage_percentage": wastage * 100
    }

def calculate_steel_quantity(bar_schedule, wastage=0.05, stock_length=12):
    """
    Estimate reinforcement steel quantity from an approved bar schedule.

    Each schedule entry contains:
    - diameter_mm
    - length_m
    - quantity

    Stock bar count is a preliminary estimate, not a cutting plan.
    """

    if not bar_schedule:
        raise ValueError("Bar schedule cannot be empty.")

    if not 0 <= wastage <= 1:
        raise ValueError("Wastage must be between 0 and 1.")

    if stock_length <= 0:
        raise ValueError("Stock length must be positive.")

    steel_details = {}
    total_length = 0
    total_weight = 0

    for bar in bar_schedule:

        diameter = bar.get("diameter_mm")
        length = bar.get("length_m")
        quantity = bar.get("quantity")

        if diameter is None or diameter <= 0:
            raise ValueError("Bar diameter must be positive.")

        if length is None or length <= 0:
            raise ValueError("Bar length must be positive.")

        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Quantity must be a positive integer.")

        # Standard approximate unit weight formula
        unit_weight = (diameter ** 2) / 162

        # Calculate total length and weight
        bar_total_length = length * quantity
        bar_total_weight = unit_weight * bar_total_length

        total_length += bar_total_length
        total_weight += bar_total_weight

        if diameter not in steel_details:
            steel_details[diameter] = {
                "diameter_mm": diameter,
                "total_length_m": 0,
                "weight_kg": 0
            }

        steel_details[diameter]["total_length_m"] += bar_total_length
        steel_details[diameter]["weight_kg"] += bar_total_weight

    # Apply wastage allowance
    final_weight = total_weight * (1 + wastage)

    # Preliminary stock bar count by diameter
    stock_bars = {}

    for diameter, details in steel_details.items():
        stock_bars[diameter] = math.ceil(
            details["total_length_m"] / stock_length
        )

        details["total_length_m"] = round(
            details["total_length_m"], 2
        )
        details["weight_kg"] = round(
            details["weight_kg"], 2
        )

    return {
        "steel_details": list(steel_details.values()),
        "total_length_m": round(total_length, 2),
        "total_weight_kg": round(total_weight, 2),
        "wastage_percentage": wastage * 100,
        "estimated_weight_with_wastage_kg": round(final_weight, 2),
        "stock_length_m": stock_length,
        "stock_bars_required": stock_bars
    }
