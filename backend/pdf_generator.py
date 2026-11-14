
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable
)


def generate_project_pdf(report, file_path):
    """
    Generate a professional PDF construction estimation report.
    """

    if not isinstance(report, dict):
        raise ValueError("Invalid project report.")

    required = {
        "project_name",
        "report_date",
        "activities",
        "combined_material_quantities",
        "overall_cost_inr",
        "overall_cost_breakdown"
    }

    if not required.issubset(report):
        raise ValueError("Project report is incomplete.")

    if not file_path or not isinstance(file_path, str):
        raise ValueError("A valid PDF file path is required.")

    document = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        fontSize=23,
        leading=28,
        textColor=colors.HexColor("#17365D"),
        alignment=TA_CENTER,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="SectionHeading",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#17365D"),
        spaceBefore=12,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name="SmallText",
        parent=styles["Normal"],
        fontSize=9,
        leading=13
    ))

    styles.add(ParagraphStyle(
        name="TotalCost",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=colors.HexColor("#137547"),
        alignment=TA_CENTER,
        spaceBefore=8
    ))

    elements = []

    # Header
    elements.append(Paragraph(
        "SITEQUOTA",
        styles["ReportTitle"]
    ))

    elements.append(Paragraph(
        "CONSTRUCTION ESTIMATION REPORT",
        styles["Heading2"]
    ))

    elements.append(HRFlowable(
        width="100%",
        thickness=1.5,
        color=colors.HexColor("#2F75B5")
    ))

    elements.append(Spacer(1, 12))

    # Project details
    elements.append(Paragraph(
        "PROJECT DETAILS",
        styles["SectionHeading"]
    ))

    project_data = [
        ["Project Name", report["project_name"]],
        ["Report Date", report["report_date"]]
    ]

    project_table = Table(
        project_data,
        colWidths=[45 * mm, 115 * mm]
    )

    project_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1),
         colors.HexColor("#DCE6F1")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
    ]))

    elements.append(project_table)

    # Individual activity estimates
    elements.append(Paragraph(
        "INDIVIDUAL ACTIVITY ESTIMATES",
        styles["SectionHeading"]
    ))

    for activity, details in report["activities"].items():

        elements.append(Paragraph(
            activity.replace("_", " ").title(),
            styles["Heading3"]
        ))

        data = [
            ["Material", "Quantity", "Unit Rate (INR)", "Cost (INR)"]
        ]

        for item in details["cost_breakdown"]:
            data.append([
                item["material"].replace("_", " ").title(),
                f'{item["quantity"]:,.4f}'.rstrip("0").rstrip(".")
                if isinstance(item["quantity"], float)
                else f'{item["quantity"]:,}',
                f'{item["unit_rate_inr"]:,.2f}',
                f'{item["cost_inr"]:,.2f}'
            ])

        data.append([
            "Activity Total",
            "",
            "",
            f'{details["total_cost_inr"]:,.2f}'
        ])

        table = Table(
            data,
            colWidths=[55 * mm, 32 * mm, 36 * mm, 37 * mm],
            repeatRows=1
        )

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0),
             colors.HexColor("#17365D")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1),
             colors.HexColor("#DCE6F1")),
            ("PADDING", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
        ]))

        elements.append(table)
        elements.append(Spacer(1, 10))

    # Combined material quantities
    elements.append(Paragraph(
        "COMBINED MATERIAL QUANTITIES",
        styles["SectionHeading"]
    ))

    quantity_data = [["Material", "Total Quantity"]]

    for material, quantity in (
        report["combined_material_quantities"].items()
    ):
        formatted = (
            f"{quantity:,.4f}".rstrip("0").rstrip(".")
            if isinstance(quantity, float)
            else f"{quantity:,}"
        )

        quantity_data.append([
            material.replace("_", " ").title(),
            formatted
        ])

    quantity_table = Table(
        quantity_data,
        colWidths=[95 * mm, 65 * mm],
        repeatRows=1
    )

    quantity_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0),
         colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("PADDING", (0, 0), (-1, -1), 8)
    ]))

    elements.append(quantity_table)

    # Overall cost breakdown
    elements.append(Paragraph(
        "OVERALL PROJECT COST BREAKDOWN",
        styles["SectionHeading"]
    ))

    overall_data = [["Material", "Total Cost (INR)"]]

    for item in report["overall_cost_breakdown"]:
        overall_data.append([
            item["material"].replace("_", " ").title(),
            f'{item["cost_inr"]:,.2f}'
        ])

    overall_table = Table(
        overall_data,
        colWidths=[95 * mm, 65 * mm],
        repeatRows=1
    )

    overall_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0),
         colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("PADDING", (0, 0), (-1, -1), 8)
    ]))

    elements.append(overall_table)

    # Final project cost
    elements.append(Spacer(1, 18))

    elements.append(Paragraph(
        f"OVERALL MATERIAL COST: INR "
        f"{report['overall_cost_inr']:,.2f}",
        styles["TotalCost"]
    ))

    elements.append(Spacer(1, 12))

    elements.append(Paragraph(
        "Note: This is an estimated material cost. "
        "Labour, transportation, equipment, taxes and "
        "other expenses are not included.",
        styles["SmallText"]
    ))

    # Page footer
    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)

        canvas.drawString(
            18 * mm,
            12 * mm,
            "SiteQuota | Construction Estimation"
        )

        canvas.drawRightString(
            A4[0] - 18 * mm,
            12 * mm,
            f"Page {doc.page}"
        )

        canvas.restoreState()

    document.build(
        elements,
        onFirstPage=add_footer,
        onLaterPages=add_footer
    )

    return file_path
