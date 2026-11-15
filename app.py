import streamlit as st
import pandas as pd
import re
import math
import hashlib
import uuid
from io import BytesIO
from datetime import date, datetime
from xml.sax.saxutils import escape
from google import genai
from google.genai import types


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="SiteCraft | Smart Construction",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Change these if your Gemini account uses different model names.
ANALYSIS_MODEL = "gemini-3.5-flash"
IMAGE_MODEL = "gemini-3.8-flash-image"

MAX_IMAGE_MB = 10
MAX_DESIGN_TEXT = 1500

PROJECT_STATUSES = ["Planning", "In Progress", "On Hold", "Completed", "Cancelled"]

MIME_BY_EXT = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp"
}


# =========================================================
# SESSION STATE
# =========================================================

DEFAULTS = {
    "projects": [],
    "page": "Dashboard",
    "main_menu": "Dashboard",
    "new_project_data": {},
    "project_stage": "construction",
    "created_project_name": "",
    "show_balloons": False,
    "profile_name": "",
    "profile_email": "",
    "company_name": "",
    "profile_phone": "",
    "currency": "INR (₹)",
    "notifications": True,
    "invoice_items_editor": pd.DataFrame([
        {
            "Description": "Cement",
            "Quantity": 10.0,
            "Unit Price (₹)": 400.0,
            "Tax (%)": 0.0
        },
        {
            "Description": "Labour Charges",
            "Quantity": 1.0,
            "Unit Price (₹)": 15000.0,
            "Tax (%)": 0.0
        }
    ])
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# NAVIGATION & HELPERS
# =========================================================

def navigate_to(page, reset_project=False):
    """Use only as an on_click callback (runs before the script reruns)."""
    if reset_project:
        st.session_state.new_project_data = {}
        st.session_state.project_stage = "construction"
        st.session_state.created_project_name = ""
        st.session_state.show_balloons = False
    st.session_state.page = page
    st.session_state.main_menu = page


def sync_navigation():
    selected_page = st.session_state.main_menu

    # Opening "New Project" from the sidebar must not show an old success screen.
    if (
        selected_page == "New Project"
        and st.session_state.page != "New Project"
        and st.session_state.project_stage == "success"
    ):
        st.session_state.new_project_data = {}
        st.session_state.project_stage = "construction"
        st.session_state.created_project_name = ""
        st.session_state.show_balloons = False

    st.session_state.page = selected_page


def selected_index(options, value):
    return options.index(value) if value in options else 0


def safe_float(value, default=0.0):
    try:
        if value is None or pd.isna(value):
            return default

        result = float(value)

        if not math.isfinite(result):
            return default

        return result

    except (TypeError, ValueError, OverflowError):
        return default


def money(value):
    """Display monetary values using the selected currency."""
    symbols = {
        "INR (₹)": "₹",
        "USD ($)": "$",
        "EUR (€)": "€",
        "GBP (£)": "£"
    }
    symbol = symbols.get(st.session_state.currency, "₹")
    return f"{symbol}{safe_float(value):,.2f}"


def money_short(value):
    """Money without decimals, for dashboard cards."""
    return money(value).rsplit(".", 1)[0]


def update_project_status(project_id):
    """on_change callback for the status selectbox in Project History."""
    new_status = st.session_state.get(f"status_{project_id}")

    if new_status not in PROJECT_STATUSES:
        return

    for project in st.session_state.projects:
        if project.get("ID") == project_id:
            project["Status"] = new_status
            project["Status Updated"] = date.today().strftime("%d-%m-%Y")
            st.toast(f"{project.get('Project', 'Project')} marked as {new_status}")
            break


# ---------- AI helpers ----------

def get_mime(uploaded_file):
    mime = getattr(uploaded_file, "type", None)

    if mime in MIME_BY_EXT.values():
        return mime

    name = getattr(uploaded_file, "name", "") or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return MIME_BY_EXT.get(ext)


def is_valid_image(data):
    """Check that bytes are a real, readable image."""
    try:
        from PIL import Image
        with Image.open(BytesIO(data)) as img:
            img.verify()
        return True
    except Exception:
        return False


def reset_ai_state():
    """Clear every AI result so stale suggestions or images are never shown."""
    for key in [
        "sitecraft_suggestions",
        "sitecraft_generated_image",
        "sitecraft_wall_image",
        "sitecraft_wall_mime",
        "sitecraft_selected_design",
        "selected_ai_design",
        "custom_design"
    ]:
        st.session_state.pop(key, None)


def get_gemini_client():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        raise RuntimeError(
            "Gemini API key not found. Add GEMINI_API_KEY to "
            ".streamlit/secrets.toml and restart the app."
        )

    if not api_key or not str(api_key).strip():
        raise RuntimeError("GEMINI_API_KEY is empty in your secrets file.")

    return genai.Client(
        api_key=str(api_key).strip(),
        http_options=types.HttpOptions(timeout=120000)
    )


def friendly_api_error(error):
    """Turn raw API exceptions into messages a user can act on."""
    if isinstance(error, RuntimeError):
        return str(error)

    text = str(error)
    lowered = text.lower()

    if "429" in text or "resource_exhausted" in lowered or "quota" in lowered:
        return "Gemini usage limit reached. Please wait a minute and try again."

    if (
        "api key" in lowered or "api_key" in lowered
        or "401" in text or "403" in text
        or "permission_denied" in lowered or "unauthenticated" in lowered
    ):
        return "Gemini rejected the API key. Check GEMINI_API_KEY in your secrets file."

    if "404" in text or "not_found" in lowered or "not found" in lowered:
        return (
            "The Gemini model was not found. Update ANALYSIS_MODEL / IMAGE_MODEL "
            "at the top of app.py to a model available to your account."
        )

    if "timeout" in lowered or "timed out" in lowered or "deadline" in lowered:
        return "The request to Gemini timed out. Please try again."

    if any(w in lowered for w in ["connection", "network", "resolve", "unreachable"]):
        return "Could not reach Gemini. Check your internet connection and try again."

    if "503" in text or "unavailable" in lowered or "overloaded" in lowered:
        return "Gemini is temporarily overloaded. Please try again shortly."

    return f"Gemini request failed: {text[:300]}"


def block_reason(response):
    feedback = getattr(response, "prompt_feedback", None)
    reason = getattr(feedback, "block_reason", None) if feedback else None
    return str(reason) if reason else None


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;700;800&display=swap');

.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
    background: #f4f6fa !important;
    color: #172a43 !important;
    font-family: 'DM Sans', sans-serif;
}

[data-testid="stSidebar"] {
    background: #142238 !important;
}

[data-testid="stSidebar"] * {
    color: #ffffff;
}

[data-testid="stMain"] h1,
[data-testid="stMain"] h2,
[data-testid="stMain"] h3,
[data-testid="stMain"] p,
[data-testid="stMain"] label,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] {
    color: #172a43;
}

[data-testid="stMain"] input,
[data-testid="stMain"] textarea,
[data-testid="stMain"] [data-baseweb="select"] > div {
    background-color: #ffffff !important;
    color: #172a43 !important;
    border-color: #dce4ed !important;
}

[data-testid="stMain"] input::placeholder,
[data-testid="stMain"] textarea::placeholder {
    color: #8492a6 !important;
}

[data-testid="stForm"] {
    background: #ffffff;
    padding: 22px;
    border: 1px solid #e5eaf0;
    border-radius: 16px;
}

[data-testid="stMain"] h1,
[data-testid="stMain"] h2,
[data-testid="stMain"] h3 {
    font-weight: 800;
}

.hero {
    background: linear-gradient(120deg, #142238, #24516a);
    padding: 38px;
    border-radius: 20px;
    margin-bottom: 28px;
    min-height: 195px;
}

.hero h1 {
    color: white !important;
    font-size: 38px;
    font-weight: 800;
}

.hero p {
    color: #d5e2ee !important;
    font-size: 16px;
}

.metric {
    background: #ffffff !important;
    padding: 22px;
    border-radius: 16px;
    border: 1px solid #e5eaf0;
    box-shadow: 0 3px 12px rgba(20,34,56,0.05);
    min-height: 115px;
}

.metric-label {
    color: #78869a !important;
    font-size: 12px;
    font-weight: 700;
}

.metric-value {
    color: #172a43 !important;
    font-size: 27px;
    font-weight: 800;
    margin-top: 9px;
}

[data-testid="stAlert"] {
    background: #ffffff !important;
    color: #172a43 !important;
    border: 1px solid #e5eaf0;
    border-radius: 12px;
}

div.stButton > button,
div.stDownloadButton > button {
    background-color: #167d83 !important;
    color: #ffffff !important;
    border: 1px solid #167d83 !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    min-height: 44px;
}

div.stButton > button p,
div.stButton > button span,
div.stDownloadButton > button p,
div.stDownloadButton > button span {
    color: #ffffff !important;
}

div.stButton > button:hover,
div.stDownloadButton > button:hover {
    background-color: #11676c !important;
    border-color: #11676c !important;
}

[data-testid="stDataFrame"] {
    background-color: #ffffff !important;
    border-radius: 12px;
}

[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e5eaf0;
    border-radius: 12px;
    padding: 12px;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown("# 🏗️ SiteCraft")
    st.caption("SMART CONSTRUCTION WORKSPACE")
    st.divider()

    st.markdown("##### MAIN MENU")

    pages = [
        "Dashboard",
        "New Project",
        "AI Estimation",
        "Material Calculator",
        "Invoice Generator",
        "Project History",
        "Settings"
    ]

    st.radio(
        "Navigation",
        pages,
        key="main_menu",
        label_visibility="collapsed",
        on_change=sync_navigation
    )

    st.divider()
    st.caption("BUILD SMARTER. PLAN BETTER.")
    st.caption("SiteCraft v1.0")


# =========================================================
# INVOICE PDF GENERATOR
# =========================================================

def format_date(value):
    return value.strftime("%d-%m-%Y") if hasattr(value, "strftime") else str(value or "N/A")


def generate_invoice_pdf(invoice_data):

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle
    )

    items = invoice_data.get("items") or []

    if not items:
        raise ValueError("The invoice has no items.")

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm
    )

    styles = getSampleStyleSheet()
    cell = styles["Normal"]
    elements = []

    elements.append(Paragraph("<b>SITECRAFT</b>", styles["Title"]))
    elements.append(Paragraph("Construction Management & Billing", styles["Normal"]))

    elements.append(Spacer(1, 15))
    elements.append(Paragraph("<b>INVOICE</b>", styles["Heading1"]))

    # Text inside Paragraph must be XML-escaped; plain strings must not be.
    info = [
        ["Invoice Number",
         Paragraph(escape(str(invoice_data.get("invoice_number") or "N/A")), cell)],
        ["Invoice Date", format_date(invoice_data.get("invoice_date"))],
        ["Due Date", format_date(invoice_data.get("due_date"))],
        ["Project",
         Paragraph(escape(str(invoice_data.get("project") or "N/A")), cell)]
    ]

    info_table = Table(info, colWidths=[45 * mm, 110 * mm])

    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF0F5")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE4ED")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 8)
    ]))

    elements.append(info_table)
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("<b>Bill To</b>", styles["Heading2"]))

    client_fields = [
        ("client_name", ""),
        ("client_email", "Email: "),
        ("client_phone", "Phone: "),
        ("client_address", "")
    ]

    client_written = False

    for field, label in client_fields:
        value = str(invoice_data.get(field) or "").strip()
        if value:
            elements.append(
                Paragraph(
                    label + escape(value).replace("\n", "<br/>"),
                    styles["Normal"]
                )
            )
            client_written = True

    if not client_written:
        elements.append(Paragraph("Client details not provided.", styles["Normal"]))

    elements.append(Spacer(1, 15))

    table_data = [["Description", "Qty", "Unit Price", "Tax %", "Amount"]]

    for item in items:
        table_data.append([
            Paragraph(escape(str(item.get("description", ""))), cell),
            f"{safe_float(item.get('quantity')):g}",
            f"Rs. {safe_float(item.get('unit_price')):,.2f}",
            f"{safe_float(item.get('tax_rate')):g}%",
            f"Rs. {safe_float(item.get('amount')):,.2f}"
        ])

    item_table = Table(
        table_data,
        colWidths=[65 * mm, 18 * mm, 32 * mm, 18 * mm, 35 * mm],
        repeatRows=1
    )

    item_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#142238")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE4ED")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor("#F4F6FA")
        ]),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 7)
    ]))

    elements.append(item_table)
    elements.append(Spacer(1, 15))

    totals = [
        ["Subtotal", f"Rs. {safe_float(invoice_data.get('subtotal')):,.2f}"],
        ["Tax", f"Rs. {safe_float(invoice_data.get('tax_total')):,.2f}"],
        ["Discount", f"Rs. {safe_float(invoice_data.get('discount')):,.2f}"],
        ["Grand Total", f"Rs. {safe_float(invoice_data.get('grand_total')):,.2f}"]
    ]

    totals_table = Table(totals, colWidths=[105 * mm, 55 * mm], hAlign="RIGHT")

    totals_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#167D83")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EAF5F4"))
    ]))

    elements.append(totals_table)
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("<b>Payment Notes</b>", styles["Heading2"]))

    notes = escape(str(invoice_data.get("notes") or "").strip()).replace("\n", "<br/>")
    elements.append(Paragraph(notes or "No additional notes.", styles["Normal"]))

    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Thank you for choosing SiteCraft!", styles["Italic"]))

    doc.build(elements)

    pdf_bytes = buffer.getvalue()

    # Verify the output really is a complete PDF before offering a download.
    if not pdf_bytes.startswith(b"%PDF") or b"%%EOF" not in pdf_bytes[-1024:]:
        raise ValueError("The generated PDF failed its integrity check.")

    return pdf_bytes


# =========================================================
# DASHBOARD
# =========================================================

if st.session_state.page == "Dashboard":

    st.markdown("""
    <div class="hero">
        <h1>Build with clarity.</h1>
        <p>
        Welcome to SiteCraft — your intelligent construction
        estimation and invoice management workspace.
        </p>
    </div>
    """, unsafe_allow_html=True)

    projects = st.session_state.projects

    total_projects = len(projects)

    total_value = sum(safe_float(p.get("Budget (₹)", 0)) for p in projects)

    completed_projects = sum(1 for p in projects if p.get("Status") == "Completed")

    col1, col2, col3, col4 = st.columns(4)

    metrics = [
        (col1, "TOTAL PROJECTS", str(total_projects)),
        (col2, "ESTIMATED VALUE", money_short(total_value)),
        (col3, "COMPLETED PROJECTS", str(completed_projects)),
        (col4, "AI STATUS", "Ready")
    ]

    for col, label, value in metrics:
        with col:
            st.markdown(f"""
            <div class="metric">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    st.write("")

    left, right = st.columns([1.7, 1])

    with left:

        st.subheader("📋 Recent Projects")

        if projects:
            recent_cols = [
                "Project", "Client", "Type", "Building Type",
                "Budget (₹)", "Status", "Date Created"
            ]
            recent_df = pd.DataFrame(projects).tail(5)
            recent_df = recent_df[[c for c in recent_cols if c in recent_df.columns]]
            st.dataframe(recent_df, use_container_width=True, hide_index=True)
        else:
            st.info("No projects yet. Create your first project to get started!")

    with right:

        st.subheader("⚡ Quick Actions")

        actions = [
            ("＋ Create New Project", "New Project"),
            ("✦ AI Estimation", "AI Estimation"),
            ("🧮 Material Calculator", "Material Calculator"),
            ("▤ Generate Invoice", "Invoice Generator"),
            ("📁 Project History", "Project History")
        ]

        for label, page in actions:
            st.button(
                label,
                key=f"qa_{page}",
                use_container_width=True,
                on_click=navigate_to,
                args=(page, page == "New Project")
            )


# =========================================================
# NEW PROJECT
# =========================================================

elif st.session_state.page == "New Project":

    data = st.session_state.new_project_data

    st.title("🏗️ Create New Project")
    st.caption("Set up your construction project in three simple steps.")

    if st.session_state.project_stage == "success":

        st.success("Project created successfully!")

        # Fire the balloons once, not on every rerun of this page.
        if st.session_state.show_balloons:
            st.balloons()
            st.session_state.show_balloons = False

        st.subheader("Your project is ready.")
        st.write(f"**Project:** {st.session_state.get('created_project_name', '')}")

        st.info("Your project has been added to Project History.")

        st.button(
            "＋ Create Another Project",
            type="primary",
            on_click=navigate_to,
            args=("New Project", True)
        )

        st.button(
            "View Project History",
            on_click=navigate_to,
            args=("Project History",)
        )

    else:

        stages = [
            "Construction Details",
            "Project Requirements",
            "Review & Submission"
        ]

        current_stage = {
            "construction": 1,
            "requirements": 2,
            "review": 3
        }.get(st.session_state.project_stage, 1)

        progress_cols = st.columns(3)

        for col, number, name in zip(progress_cols, [1, 2, 3], stages):
            with col:
                if number < current_stage:
                    st.success(f"✓ {number}. {name}")
                elif number == current_stage:
                    st.info(f"● {number}. {name}")
                else:
                    st.caption(f"{number}. {name}")

        st.divider()

        # -------------------------------------------------
        # STEP 1: CONSTRUCTION DETAILS
        # -------------------------------------------------

        if st.session_state.project_stage == "construction":

            st.subheader("1. Construction Details")

            project_name = st.text_input(
                "Project Name *",
                value=data.get("project_name", ""),
                placeholder="Example: Dream Villa",
                key="new_project_name"
            )

            client_name = st.text_input(
                "Client Name *",
                value=data.get("client_name", ""),
                placeholder="Enter client name",
                key="new_client_name"
            )

            construction_types = ["Residential", "Commercial"]

            construction_type = st.selectbox(
                "Construction Type",
                construction_types,
                index=selected_index(
                    construction_types,
                    data.get("construction_type", "Residential")
                ),
                key="new_construction_type"
            )

            if construction_type == "Residential":
                building_options = [
                    "Individual House",
                    "Apartment",
                    "Villa",
                    "Duplex House",
                    "Other"
                ]
            else:
                building_options = [
                    "Office Building",
                    "Shopping Complex",
                    "Warehouse",
                    "Industrial Building",
                    "Other"
                ]

            building_type = st.selectbox(
                "Building Type",
                building_options,
                index=selected_index(building_options, data.get("building_type", "")),
                key="new_building_type"
            )

            unit_options = ["sq.ft", "sq.m"]

            unit = st.selectbox(
                "Measurement Unit",
                unit_options,
                index=selected_index(unit_options, data.get("unit", "sq.ft")),
                key="new_unit"
            )

            with st.form("construction_details_form"):

                col1, col2 = st.columns(2)

                with col1:
                    floors = st.number_input(
                        "Number of Floors",
                        min_value=1,
                        max_value=100,
                        value=int(data.get("floors", 1))
                    )

                    plot_length = st.number_input(
                        f"Plot Length ({unit})",
                        min_value=0.0,
                        value=float(data.get("plot_length", 0.0))
                    )

                with col2:
                    plot_width = st.number_input(
                        f"Plot Width ({unit})",
                        min_value=0.0,
                        value=float(data.get("plot_width", 0.0))
                    )

                    built_up_area = st.number_input(
                        f"Built-up Area ({unit})",
                        min_value=0.0,
                        value=float(data.get("built_up_area", 0.0))
                    )

                construction_area = st.number_input(
                    f"Total Construction Area ({unit})",
                    min_value=0.0,
                    value=float(data.get("construction_area", 0.0))
                )

                budget = st.number_input(
                    "Estimated Budget (₹)",
                    min_value=0.0,
                    value=float(data.get("budget", 1000000.0)),
                    step=50000.0
                )

                additional_requirements = st.text_area(
                    "Additional Construction Requirements",
                    value=data.get("additional_requirements", ""),
                    placeholder="Parking, garden, lift, basement, etc."
                )

                construction_submit = st.form_submit_button(
                    "Save & Continue →",
                    type="primary",
                    use_container_width=True
                )

            if construction_submit:

                if not project_name.strip():
                    st.error("Please enter the project name.")

                elif not client_name.strip():
                    st.error("Please enter the client name.")

                elif any(
                    p.get("Project", "").strip().lower() == project_name.strip().lower()
                    for p in st.session_state.projects
                ):
                    st.error("A project with this name already exists.")

                elif plot_length <= 0 or plot_width <= 0:
                    st.error("Plot length and width must be greater than zero.")

                elif built_up_area <= 0 or construction_area <= 0:
                    st.error("Built-up area and construction area must be greater than zero.")

                elif budget <= 0:
                    st.error("Please enter a valid estimated budget.")

                else:
                    data.update({
                        "project_name": project_name.strip(),
                        "client_name": client_name.strip(),
                        "construction_type": construction_type,
                        "building_type": building_type,
                        "unit": unit,
                        "floors": int(floors),
                        "plot_length": plot_length,
                        "plot_width": plot_width,
                        "built_up_area": built_up_area,
                        "construction_area": construction_area,
                        "budget": budget,
                        "additional_requirements": additional_requirements
                    })

                    st.session_state.new_project_data = data
                    st.session_state.project_stage = "requirements"
                    st.rerun()

        # -------------------------------------------------
        # STEP 2: PROJECT REQUIREMENTS
        # -------------------------------------------------

        elif st.session_state.project_stage == "requirements":

            st.subheader("2. Project Requirements")
            st.caption("Specify your preferred construction materials and requirements.")

            foundation_options = [
                "Not Decided",
                "Isolated Footing",
                "Combined Footing",
                "Raft Foundation",
                "Pile Foundation",
                "Strip Foundation"
            ]

            wall_options = [
                "Not Decided",
                "Red Brick",
                "Fly Ash Brick",
                "Concrete Block",
                "AAC Block",
                "Other"
            ]

            thickness_options = [
                "Not Decided",
                "4.5 inches",
                "6 inches",
                "9 inches",
                "Other"
            ]

            roof_options = [
                "Not Decided",
                "RCC Slab",
                "Metal Roofing",
                "Tiled Roof",
                "Concrete Roof",
                "Other"
            ]

            flooring_options = [
                "Not Decided",
                "Ceramic Tiles",
                "Vitrified Tiles",
                "Marble",
                "Granite",
                "Wooden Flooring",
                "Other"
            ]

            with st.form("project_requirements_form"):

                col1, col2 = st.columns(2)

                with col1:
                    foundation = st.selectbox(
                        "Foundation Type",
                        foundation_options,
                        index=selected_index(
                            foundation_options, data.get("foundation", "Not Decided")
                        )
                    )

                    wall_material = st.selectbox(
                        "Wall Material",
                        wall_options,
                        index=selected_index(
                            wall_options, data.get("wall_material", "Not Decided")
                        )
                    )

                    wall_thickness = st.selectbox(
                        "Wall Thickness",
                        thickness_options,
                        index=selected_index(
                            thickness_options, data.get("wall_thickness", "Not Decided")
                        )
                    )

                with col2:
                    roof_type = st.selectbox(
                        "Roof Type",
                        roof_options,
                        index=selected_index(
                            roof_options, data.get("roof_type", "Not Decided")
                        )
                    )

                    flooring = st.selectbox(
                        "Flooring Preference",
                        flooring_options,
                        index=selected_index(
                            flooring_options, data.get("flooring", "Not Decided")
                        )
                    )

                special_requirements = st.text_area(
                    "Special Requirements",
                    value=data.get("special_requirements", ""),
                    placeholder="Electrical, plumbing, ventilation, etc."
                )

                project_description = st.text_area(
                    "Project Description",
                    value=data.get("project_description", ""),
                    placeholder="Describe your construction project."
                )

                requirements_submit = st.form_submit_button(
                    "Save Requirements & Continue →",
                    type="primary",
                    use_container_width=True
                )

            if st.button("← Back to Construction Details"):
                st.session_state.project_stage = "construction"
                st.rerun()

            if requirements_submit:
                data.update({
                    "foundation": foundation,
                    "wall_material": wall_material,
                    "wall_thickness": wall_thickness,
                    "roof_type": roof_type,
                    "flooring": flooring,
                    "special_requirements": special_requirements,
                    "project_description": project_description
                })

                st.session_state.new_project_data = data
                st.session_state.project_stage = "review"
                st.rerun()

        # -------------------------------------------------
        # STEP 3: REVIEW
        # -------------------------------------------------

        elif st.session_state.project_stage == "review":

            st.subheader("3. Review & Submission")

            st.markdown("### Basic Project Information")

            col1, col2 = st.columns(2)

            unit_label = data.get("unit", "")

            with col1:
                st.write("**Project Name:**", data.get("project_name", ""))
                st.write("**Client Name:**", data.get("client_name", ""))
                st.write("**Construction Type:**", data.get("construction_type", ""))
                st.write("**Building Type:**", data.get("building_type", ""))

            with col2:
                st.write("**Number of Floors:**", data.get("floors", ""))
                st.write("**Measurement Unit:**", unit_label)
                st.write(
                    "**Plot Dimensions:**",
                    f"{data.get('plot_length', 0)} × {data.get('plot_width', 0)} {unit_label}"
                )
                st.write(
                    "**Built-up Area:**",
                    f"{data.get('built_up_area', 0)} {unit_label}"
                )
                st.write(
                    "**Construction Area:**",
                    f"{data.get('construction_area', 0)} {unit_label}"
                )
                st.write("**Estimated Budget:**", money(data.get("budget", 0)))

            st.write(
                "**Additional Construction Requirements:**",
                data.get("additional_requirements") or "Not specified"
            )

            st.divider()
            st.markdown("### Material & Construction Preferences")

            col1, col2 = st.columns(2)

            with col1:
                st.write("**Foundation:**", data.get("foundation", "Not Decided"))
                st.write("**Wall Material:**", data.get("wall_material", "Not Decided"))
                st.write("**Wall Thickness:**", data.get("wall_thickness", "Not Decided"))

            with col2:
                st.write("**Roof Type:**", data.get("roof_type", "Not Decided"))
                st.write("**Flooring:**", data.get("flooring", "Not Decided"))

            st.write(
                "**Special Requirements:**",
                data.get("special_requirements") or "Not specified"
            )

            st.write(
                "**Project Description:**",
                data.get("project_description") or "Not specified"
            )

            st.divider()

            edit_col1, edit_col2, submit_col = st.columns([1, 1, 2])

            with edit_col1:
                if st.button("← Edit Construction Details"):
                    st.session_state.project_stage = "construction"
                    st.rerun()

            with edit_col2:
                if st.button("← Edit Requirements"):
                    st.session_state.project_stage = "requirements"
                    st.rerun()

            with submit_col:
                if st.button(
                    "Create Project ✓",
                    type="primary",
                    use_container_width=True
                ):

                    project = {
                        "ID": uuid.uuid4().hex[:8],
                        "Project": data.get("project_name", ""),
                        "Client": data.get("client_name", ""),
                        "Type": data.get("construction_type", ""),
                        "Building Type": data.get("building_type", ""),
                        "Floors": data.get("floors", 1),
                        "Plot Length": data.get("plot_length", 0),
                        "Plot Width": data.get("plot_width", 0),
                        "Unit": data.get("unit", "sq.ft"),
                        "Area": data.get("construction_area", 0),
                        "Budget (₹)": data.get("budget", 0),
                        "Foundation": data.get("foundation", ""),
                        "Wall Material": data.get("wall_material", ""),
                        "Roof": data.get("roof_type", ""),
                        "Flooring": data.get("flooring", ""),
                        "Status": "Planning",
                        "Date Created": date.today().strftime("%d-%m-%Y"),
                        "project_description": data.get("project_description", ""),
                        "additional_requirements": data.get("additional_requirements", "")
                    }

                    st.session_state.projects.append(project)
                    st.session_state.created_project_name = data.get("project_name", "")
                    st.session_state.new_project_data = {}
                    st.session_state.project_stage = "success"
                    st.session_state.show_balloons = True
                    st.rerun()


# =========================================================
# AI ESTIMATION / INTERIOR DESIGN
# =========================================================

elif st.session_state.page == "AI Estimation":

    st.title("✦ AI Interior Designer")

    st.caption(
        "Upload your wall photo, explore AI design ideas "
        "and generate your customised interior design."
    )

    st.divider()
    st.subheader("1. Upload Your Wall Photo")

    uploaded_file = st.file_uploader(
        "Choose a photo of your wall",
        type=["jpg", "jpeg", "png", "webp"],
        help=f"Upload a clear photo of the wall you want to decorate (max {MAX_IMAGE_MB} MB)."
    )

    if uploaded_file is None:

        # Photo removed (or page revisited): never keep results for a missing photo.
        if (
            st.session_state.get("sitecraft_image_hash") is not None
            or st.session_state.get("sitecraft_suggestions")
            or st.session_state.get("sitecraft_generated_image")
        ):
            reset_ai_state()
            st.session_state["sitecraft_image_hash"] = None

    else:

        image_bytes = uploaded_file.getvalue()
        mime_type = get_mime(uploaded_file)
        current_image_hash = hashlib.sha256(image_bytes).hexdigest()

        # A different photo invalidates all earlier suggestions and results.
        if st.session_state.get("sitecraft_image_hash") != current_image_hash:
            reset_ai_state()
            st.session_state["sitecraft_image_hash"] = current_image_hash

        image_ok = True

        if not image_bytes:
            st.error("The uploaded file is empty. Please choose another photo.")
            image_ok = False

        elif len(image_bytes) > MAX_IMAGE_MB * 1024 * 1024:
            st.error(f"The photo is larger than {MAX_IMAGE_MB} MB. Please upload a smaller one.")
            image_ok = False

        elif not mime_type:
            st.error("Unsupported image type. Please upload a JPG, PNG or WEBP photo.")
            image_ok = False

        elif not is_valid_image(image_bytes):
            st.error("This file could not be read as an image. Please upload another photo.")
            image_ok = False

        if image_ok:

            st.image(image_bytes, caption="Your original wall", use_container_width=True)

            if st.button("Analyse My Wall & Suggest Designs", type="primary"):

                try:
                    client = get_gemini_client()

                    prompt = """
                    Analyse this wall photograph for interior design.

                    Suggest exactly THREE different, practical
                    interior wall design ideas.

                    Consider the existing wall, its appearance,
                    lighting and visible surroundings.

                    Return exactly three numbered suggestions, formatted as
                    "1. ...", "2. ...", "3. ...".
                    Each suggestion should include:
                    - Design style
                    - Suggested materials
                    - Colour combination
                    - Decorative elements

                    Keep each suggestion concise.
                    Do not provide prices.
                    """

                    with st.spinner("Gemini is analysing your wall..."):
                        analysis = client.models.generate_content(
                            model=ANALYSIS_MODEL,
                            contents=[
                                types.Part.from_bytes(
                                    data=image_bytes,
                                    mime_type=mime_type
                                ),
                                prompt
                            ]
                        )

                    blocked = block_reason(analysis)

                    if blocked:
                        st.error(
                            "Gemini could not analyse this photo "
                            f"({blocked}). Please try a different image."
                        )

                    else:
                        suggestions_text = analysis.text or ""

                        # Split on numbered headings so multi-line suggestions stay together.
                        parts = re.split(r"(?m)^[\s*#]*(?=\d+[.)]\s)", suggestions_text)
                        suggestions = [
                            re.sub(r"^\d+[.)]\s*", "", p).strip()
                            for p in parts
                            if p.strip() and re.match(r"^\d+[.)]\s", p.strip())
                        ][:3]

                        if len(suggestions) < 3:
                            st.error(
                                "Gemini did not return three suggestions. "
                                "Please try again."
                            )
                        else:
                            # New analysis: drop old choices and results.
                            st.session_state.pop("sitecraft_generated_image", None)
                            st.session_state.pop("selected_ai_design", None)
                            st.session_state["sitecraft_wall_image"] = image_bytes
                            st.session_state["sitecraft_wall_mime"] = mime_type
                            st.session_state["sitecraft_suggestions"] = suggestions
                            st.success("Your wall analysis is complete!")

                except Exception as e:
                    st.error(friendly_api_error(e))

    if st.session_state.get("sitecraft_suggestions"):

        st.divider()
        st.subheader("2. Explore AI Design Suggestions")

        suggestions = st.session_state["sitecraft_suggestions"]

        for index, suggestion in enumerate(suggestions, start=1):
            with st.container(border=True):
                st.markdown(f"**Design Option {index}**")
                st.write(suggestion)

        st.divider()
        st.subheader("3. Choose Your Design")

        design_choice = st.radio(
            "How would you like to continue?",
            ["Choose an AI suggestion", "Create my own design idea"],
            key="design_choice"
        )

        if design_choice == "Choose an AI suggestion":
            selected_design = st.selectbox(
                "Select your favourite design",
                suggestions,
                key="selected_ai_design"
            )
        else:
            selected_design = st.text_area(
                "Describe your dream wall design",
                placeholder=(
                    "Example: I want a modern wooden panel wall "
                    "with warm LED lighting and a marble finish."
                ),
                key="custom_design"
            )

        if st.button("Generate My Interior Design", type="primary"):

            design_text = (selected_design or "").strip()
            wall_image = st.session_state.get("sitecraft_wall_image")
            wall_mime = st.session_state.get("sitecraft_wall_mime")

            if not design_text:
                st.error("Please select or describe a design first.")

            elif len(design_text) > MAX_DESIGN_TEXT:
                st.error(
                    f"Please keep your design description under {MAX_DESIGN_TEXT} characters."
                )

            elif (
                not wall_image
                or hashlib.sha256(wall_image).hexdigest()
                != st.session_state.get("sitecraft_image_hash")
            ):
                st.error(
                    "Your photo has changed. Please analyse the wall again "
                    "before generating a design."
                )

            else:
                try:
                    client = get_gemini_client()

                    prompt = f"""
                    Redesign the wall in the provided photograph.

                    Customer's chosen design:
                    {design_text}

                    Create a realistic interior design
                    visualisation of this same wall.

                    Preserve the original room layout,
                    wall position and camera perspective
                    as much as possible.

                    Apply the requested materials,
                    colours, lighting and decorations.

                    Make the result look like a
                    professionally designed interior.
                    """

                    with st.spinner("Gemini is creating your interior design..."):
                        response = client.models.generate_content(
                            model=IMAGE_MODEL,
                            contents=[
                                types.Part.from_bytes(
                                    data=wall_image,
                                    mime_type=wall_mime
                                ),
                                prompt
                            ]
                        )

                    blocked = block_reason(response)
                    generated_bytes = None
                    model_text = ""

                    candidates = getattr(response, "candidates", None) or []

                    if candidates and getattr(candidates[0], "content", None):
                        for part in candidates[0].content.parts or []:
                            inline = getattr(part, "inline_data", None)

                            if inline and inline.data and generated_bytes is None:
                                generated_bytes = inline.data
                            elif getattr(part, "text", None):
                                model_text += part.text

                    if blocked:
                        st.error(
                            f"Gemini blocked this request ({blocked}). "
                            "Try a different description."
                        )

                    elif not generated_bytes:
                        message = "Gemini did not return an image. Please try again."
                        if model_text.strip():
                            message += f" Gemini said: {model_text.strip()[:300]}"
                        st.error(message)

                    elif not is_valid_image(generated_bytes):
                        st.error(
                            "Gemini returned data that is not a valid image. "
                            "Please try again."
                        )

                    else:
                        st.session_state["sitecraft_generated_image"] = generated_bytes
                        st.session_state["sitecraft_selected_design"] = design_text

                except Exception as e:
                    st.error(friendly_api_error(e))

        if st.session_state.get("sitecraft_generated_image"):

            st.divider()
            st.subheader("4. Your Custom Interior Design")

            st.image(
                st.session_state["sitecraft_generated_image"],
                caption="AI-generated interior design concept",
                use_container_width=True
            )

            st.success("Your interior design preview is ready!")

            st.download_button(
                "⬇️ Download Design Image",
                data=st.session_state["sitecraft_generated_image"],
                file_name="sitecraft_interior_design.png",
                mime="image/png"
            )

            st.info(
                "Next: We will connect this design to the "
                "AI construction cost estimation feature."
            )


# =========================================================
# MATERIAL CALCULATOR
# =========================================================

elif st.session_state.page == "Material Calculator":

    st.title("🧮 Material Calculator")
    st.caption("Estimate construction material quantities.")

    st.warning(
        "These calculators provide preliminary quantity estimates only. "
        "They are not structural design calculations or construction approval. "
        "Verify actual quantities with a qualified professional."
    )

    tab1, tab2, tab3 = st.tabs([
        "Concrete Calculator",
        "Brickwork Calculator",
        "Steel Calculator"
    ])

    # -----------------------------------------------------
    # CONCRETE
    # -----------------------------------------------------

    with tab1:

        st.subheader("Concrete Quantity Calculator")

        col1, col2 = st.columns(2)

        with col1:
            length = st.number_input(
                "Length (m)", min_value=0.0, value=5.0, key="concrete_length"
            )
            width = st.number_input(
                "Width (m)", min_value=0.0, value=4.0, key="concrete_width"
            )

        with col2:
            depth = st.number_input(
                "Depth (m)", min_value=0.0, value=0.15, key="concrete_depth"
            )
            mix_ratio = st.selectbox(
                "Concrete Mix", ["M10", "M15", "M20"], index=2, key="concrete_mix"
            )

        wastage = st.number_input(
            "Wastage (%)",
            min_value=0.0,
            max_value=100.0,
            value=5.0,
            key="concrete_wastage"
        )

        ratios = {
            "M10": (1, 3, 6),
            "M15": (1, 2, 4),
            "M20": (1, 1.5, 3)
        }

        if st.button("Calculate Concrete", key="calculate_concrete", type="primary"):

            # Always drop the previous result first so an invalid
            # calculation never leaves an old answer on screen.
            st.session_state.pop("concrete_result", None)

            if length <= 0 or width <= 0 or depth <= 0:
                st.error("All concrete dimensions must be greater than zero.")
            else:
                wet_volume = length * width * depth
                adjusted_volume = wet_volume * (1 + wastage / 100)
                dry_volume = adjusted_volume * 1.54

                cement_ratio, sand_ratio, aggregate_ratio = ratios[mix_ratio]
                total_ratio = cement_ratio + sand_ratio + aggregate_ratio

                cement_volume = dry_volume * cement_ratio / total_ratio
                sand_volume = dry_volume * sand_ratio / total_ratio
                aggregate_volume = dry_volume * aggregate_ratio / total_ratio

                cement_bags = cement_volume / 0.0347

                st.session_state["concrete_result"] = {
                    "Wet Concrete Volume (m³)": round(wet_volume, 3),
                    "Adjusted Concrete Volume (m³)": round(adjusted_volume, 3),
                    "Cement (bags)": round(cement_bags, 2),
                    "Sand (m³)": round(sand_volume, 3),
                    "Aggregate (m³)": round(aggregate_volume, 3)
                }

        if st.session_state.get("concrete_result"):

            st.divider()
            st.subheader("Concrete Calculation Results")

            result = st.session_state["concrete_result"]

            c1, c2, c3 = st.columns(3)

            c1.metric("Concrete Volume", f"{result['Wet Concrete Volume (m³)']} m³")
            c2.metric("Cement Required", f"{result['Cement (bags)']} bags")
            c3.metric("Sand Required", f"{result['Sand (m³)']} m³")

            st.dataframe(
                pd.DataFrame(result.items(), columns=["Material", "Estimated Quantity"]),
                use_container_width=True,
                hide_index=True
            )

    # -----------------------------------------------------
    # BRICKWORK
    # -----------------------------------------------------

    with tab2:

        st.subheader("Brickwork Quantity Calculator")

        col1, col2 = st.columns(2)

        with col1:
            wall_length = st.number_input(
                "Wall Length (m)", min_value=0.0, value=5.0, key="brick_length"
            )
            wall_height = st.number_input(
                "Wall Height (m)", min_value=0.0, value=3.0, key="brick_height"
            )

        with col2:
            brick_thickness_options = {
                "4.5 inches": 0.1143,
                "6 inches": 0.1524,
                "9 inches": 0.2286
            }

            selected_thickness = st.selectbox(
                "Wall Thickness",
                list(brick_thickness_options.keys()),
                key="brick_thickness"
            )

            opening_area = st.number_input(
                "Door/Window Opening Area (m²)",
                min_value=0.0,
                value=0.0,
                key="brick_openings"
            )

        brick_wastage = st.number_input(
            "Brick Wastage (%)",
            min_value=0.0,
            max_value=100.0,
            value=5.0,
            key="brick_wastage"
        )

        if st.button("Calculate Brickwork", key="calculate_brickwork", type="primary"):

            st.session_state.pop("brick_result", None)

            face_area = wall_length * wall_height

            if wall_length <= 0 or wall_height <= 0:
                st.error("Wall length and height must be greater than zero.")

            elif opening_area >= face_area:
                st.error(
                    "Opening area must be smaller than the wall face area "
                    f"({face_area:.2f} m²). Otherwise no brickwork remains."
                )

            else:
                thickness = brick_thickness_options[selected_thickness]
                gross_volume = face_area * thickness
                opening_volume = opening_area * thickness

                net_volume = gross_volume - opening_volume
                adjusted_volume = net_volume * (1 + brick_wastage / 100)

                brick_count = adjusted_volume * 500
                mortar_volume = adjusted_volume * 0.30

                st.session_state["brick_result"] = {
                    "Wall Volume (m³)": round(net_volume, 3),
                    "Adjusted Volume (m³)": round(adjusted_volume, 3),
                    "Estimated Bricks": round(brick_count),
                    "Estimated Mortar (m³)": round(mortar_volume, 3)
                }

        if st.session_state.get("brick_result"):

            st.divider()
            st.subheader("Brickwork Calculation Results")

            result = st.session_state["brick_result"]

            c1, c2, c3 = st.columns(3)

            c1.metric("Wall Volume", f"{result['Wall Volume (m³)']} m³")
            c2.metric("Bricks Required", f"{result['Estimated Bricks']:,}")
            c3.metric("Mortar Volume", f"{result['Estimated Mortar (m³)']} m³")

            st.dataframe(
                pd.DataFrame(result.items(), columns=["Material", "Estimated Quantity"]),
                use_container_width=True,
                hide_index=True
            )

    # -----------------------------------------------------
    # STEEL
    # -----------------------------------------------------

    with tab3:

        st.subheader("Steel Quantity Calculator")

        col1, col2 = st.columns(2)

        with col1:
            diameter = st.selectbox(
                "Steel Bar Diameter (mm)",
                [8, 10, 12, 16, 20, 25, 32],
                key="steel_diameter"
            )

            bar_length = st.number_input(
                "Length of Each Bar (m)",
                min_value=0.0,
                value=12.0,
                key="steel_length"
            )

        with col2:
            number_of_bars = st.number_input(
                "Number of Bars",
                min_value=1,
                value=10,
                step=1,
                key="steel_count"
            )

            steel_wastage = st.number_input(
                "Wastage (%)",
                min_value=0.0,
                max_value=100.0,
                value=5.0,
                key="steel_wastage"
            )

        if st.button("Calculate Steel", key="calculate_steel", type="primary"):

            st.session_state.pop("steel_result", None)

            if bar_length <= 0:
                st.error("Bar length must be greater than zero.")
            else:
                unit_weight = diameter ** 2 / 162
                total_length = bar_length * number_of_bars
                base_weight = unit_weight * total_length

                final_weight = base_weight * (1 + steel_wastage / 100)

                st.session_state["steel_result"] = {
                    "Bar Diameter (mm)": diameter,
                    "Unit Weight (kg/m)": round(unit_weight, 3),
                    "Total Length (m)": round(total_length, 2),
                    "Steel Weight (kg)": round(final_weight, 2)
                }

        if st.session_state.get("steel_result"):

            st.divider()
            st.subheader("Steel Calculation Results")

            result = st.session_state["steel_result"]

            c1, c2, c3 = st.columns(3)

            c1.metric("Unit Weight", f"{result['Unit Weight (kg/m)']} kg/m")
            c2.metric("Total Length", f"{result['Total Length (m)']} m")
            c3.metric("Steel Required", f"{result['Steel Weight (kg)']} kg")

            st.dataframe(
                pd.DataFrame(result.items(), columns=["Parameter", "Estimated Value"]),
                use_container_width=True,
                hide_index=True
            )


# =========================================================
# INVOICE GENERATOR
# =========================================================

elif st.session_state.page == "Invoice Generator":

    st.title("🧾 Invoice Generator")
    st.caption("Create, preview and download construction invoices.")

    st.divider()
    st.subheader("1. Invoice Information")

    col1, col2 = st.columns(2)

    with col1:
        invoice_number = st.text_input(
            "Invoice Number",
            value=f"INV-{datetime.now():%Y%m%d}-001",
            key="invoice_number"
        )

        invoice_date = st.date_input(
            "Invoice Date",
            value=date.today(),
            key="invoice_date"
        )

    with col2:
        project_names = [
            p.get("Project", "")
            for p in st.session_state.projects
            if p.get("Project")
        ]

        project_options = ["Manual Entry"] + project_names

        selected_project = st.selectbox(
            "Select Project",
            project_options,
            key="invoice_project"
        )

        due_date = st.date_input(
            "Payment Due Date",
            value=date.today(),
            key="invoice_due_date"
        )

    selected_project_data = next(
        (p for p in st.session_state.projects if p.get("Project") == selected_project),
        {}
    )

    st.divider()
    st.subheader("2. Client Information")

    client_col1, client_col2 = st.columns(2)

    with client_col1:
        client_name = st.text_input(
            "Client Name",
            value=selected_project_data.get("Client", ""),
            key=f"invoice_client_{selected_project}"
        )

        client_email = st.text_input(
            "Client Email",
            placeholder="client@example.com",
            key=f"invoice_email_{selected_project}"
        )

    with client_col2:
        client_phone = st.text_input(
            "Client Phone",
            placeholder="Enter phone number",
            key=f"invoice_phone_{selected_project}"
        )

        client_address = st.text_area(
            "Client Address",
            placeholder="Enter complete billing address",
            key=f"invoice_address_{selected_project}"
        )

    st.divider()
    st.subheader("3. Items & Charges")

    st.caption("Add materials, labour charges and other services.")

    edited_items = st.data_editor(
        st.session_state["invoice_items_editor"],
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="invoice_items_table",
        column_config={
            "Description": st.column_config.TextColumn("Description", required=True),
            "Quantity": st.column_config.NumberColumn(
                "Quantity", min_value=0.0, format="%.2f"
            ),
            "Unit Price (₹)": st.column_config.NumberColumn(
                "Unit Price (₹)", min_value=0.0, format="%.2f"
            ),
            "Tax (%)": st.column_config.NumberColumn(
                "Tax (%)", min_value=0.0, max_value=100.0, format="%.2f"
            )
        }
    )

    st.divider()
    st.subheader("4. Additional Details")

    col1, col2 = st.columns(2)

    with col1:
        discount_percentage = st.number_input(
            "Discount (%)",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=1.0,
            key="invoice_discount"
        )

    with col2:
        notes = st.text_area(
            "Payment Notes",
            value="Please make the payment before the due date.",
            key="invoice_notes"
        )

    # -----------------------------------------------------
    # CALCULATE & VALIDATE
    # -----------------------------------------------------

    subtotal = 0.0
    tax_total = 0.0
    valid_items = []
    invoice_errors = []

    for _, row in edited_items.iterrows():

        description_value = row.get("Description", "")
        description = (
            "" if pd.isna(description_value) else str(description_value).strip()
        )

        quantity = safe_float(row.get("Quantity", 0))
        unit_price = safe_float(row.get("Unit Price (₹)", 0))
        tax_rate = safe_float(row.get("Tax (%)", 0))

        if not description:
            if quantity != 0 or unit_price != 0 or tax_rate != 0:
                invoice_errors.append("An item is missing its description.")
            continue

        if quantity <= 0:
            invoice_errors.append(f"{description}: quantity must be greater than zero.")
            continue

        if unit_price < 0:
            invoice_errors.append(f"{description}: unit price cannot be negative.")
            continue

        if tax_rate < 0 or tax_rate > 100:
            invoice_errors.append(f"{description}: tax must be between 0 and 100.")
            continue

        amount = quantity * unit_price
        item_tax = amount * tax_rate / 100

        subtotal += amount
        tax_total += item_tax

        valid_items.append({
            "description": description,
            "quantity": quantity,
            "unit_price": unit_price,
            "tax_rate": tax_rate,
            "amount": amount
        })

    item_error_count = len(invoice_errors)

    discount = subtotal * discount_percentage / 100
    grand_total = subtotal + tax_total - discount

    # Header / client / totals validation.
    clean_invoice_number = invoice_number.strip()

    if not clean_invoice_number:
        invoice_errors.append("Invoice number is required.")
    elif len(clean_invoice_number) > 40:
        invoice_errors.append("Invoice number must be 40 characters or fewer.")

    if not client_name.strip():
        invoice_errors.append("Client name is required.")

    if client_email.strip() and not re.match(
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$", client_email.strip()
    ):
        invoice_errors.append("Client email is not a valid email address.")

    if client_phone.strip() and not re.match(
        r"^\+?[\d\s\-()]{7,20}$", client_phone.strip()
    ):
        invoice_errors.append("Client phone number is not valid.")

    if due_date < invoice_date:
        invoice_errors.append("Due date cannot be earlier than the invoice date.")

    if not 0 <= discount_percentage <= 100:
        invoice_errors.append("Discount must be between 0% and 100%.")

    if not valid_items and item_error_count == 0:
        invoice_errors.append("Add at least one invoice item.")

    if valid_items:
        if not math.isfinite(grand_total):
            invoice_errors.append("The invoice total is not a valid number.")
        elif grand_total <= 0:
            invoice_errors.append("The invoice grand total must be greater than zero.")

    # -----------------------------------------------------
    # INVOICE PREVIEW
    # -----------------------------------------------------

    st.divider()
    st.subheader("5. Invoice Preview")

    if invoice_errors:

        st.error("Please fix the following before previewing or downloading the invoice:")

        for issue in invoice_errors:
            st.write(f"- {issue}")

    else:

        st.markdown("""
        <div style="
            background: #142238;
            padding: 22px;
            border-radius: 14px;
        ">
            <h2 style="color:white; margin:0;">SITECRAFT</h2>
            <p style="color:#d5e2ee; margin:5px 0 0 0;">
                Construction Management & Billing
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.write("")

        preview_col1, preview_col2 = st.columns(2)

        with preview_col1:
            st.markdown("**BILL TO**")
            st.write(client_name.strip())
            st.write(client_email.strip() or "Email not entered")
            st.write(client_phone.strip() or "Phone not entered")
            st.write(client_address.strip() or "Address not entered")

        with preview_col2:
            st.markdown("**INVOICE DETAILS**")
            st.write(f"Invoice: {clean_invoice_number}")
            st.write(f"Date: {invoice_date}")
            st.write(f"Due Date: {due_date}")
            st.write(f"Project: {selected_project}")

        preview_df = pd.DataFrame([
            {
                "Description": item["description"],
                "Quantity": item["quantity"],
                "Unit Price (₹)": item["unit_price"],
                "Tax (%)": item["tax_rate"],
                "Amount (₹)": item["amount"]
            }
            for item in valid_items
        ])

        st.dataframe(preview_df, use_container_width=True, hide_index=True)

        total_col1, total_col2, total_col3 = st.columns(3)

        total_col1.metric("Subtotal", f"₹{subtotal:,.2f}")
        total_col2.metric("Tax", f"₹{tax_total:,.2f}")
        total_col3.metric("Discount", f"₹{discount:,.2f}")

        st.markdown(
            f"""
            <div style="
                background:#e8f4f3;
                padding:20px;
                border-radius:12px;
                text-align:right;
                margin-top:15px;
            ">
                <p style="color:#167d83; font-weight:700;">
                    GRAND TOTAL
                </p>
                <h1 style="color:#142238; margin:0;">
                    ₹{grand_total:,.2f}
                </h1>
            </div>
            """,
            unsafe_allow_html=True
        )

        invoice_data = {
            "invoice_number": clean_invoice_number,
            "invoice_date": invoice_date,
            "due_date": due_date,
            "project": selected_project,
            "client_name": client_name.strip(),
            "client_email": client_email.strip(),
            "client_phone": client_phone.strip(),
            "client_address": client_address.strip(),
            "items": valid_items,
            "subtotal": subtotal,
            "tax_total": tax_total,
            "discount": discount,
            "grand_total": grand_total,
            "notes": notes
        }

        try:
            pdf_bytes = generate_invoice_pdf(invoice_data)

            filename = re.sub(r"[^A-Za-z0-9._-]+", "_", clean_invoice_number) + ".pdf"

            st.download_button(
                label="⬇️ Download Invoice PDF",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )

        except Exception as e:
            st.error(f"Unable to generate the PDF: {e}")

    st.caption(
        "Note: Tax percentages are entered manually. This invoice preview "
        "does not automatically verify GST compliance. Invoices are always "
        "calculated in ₹ regardless of the display currency setting."
    )


# =========================================================
# PROJECT HISTORY
# =========================================================

elif st.session_state.page == "Project History":

    st.title("📁 Project History")
    st.caption("Search, explore and manage your construction projects.")

    projects = st.session_state.projects

    if not projects:

        st.info("No project history available yet.")

        st.button(
            "＋ Create Your First Project",
            type="primary",
            on_click=navigate_to,
            args=("New Project", True)
        )

    else:

        df = pd.DataFrame(projects)

        total_projects = len(projects)

        total_budget = sum(safe_float(p.get("Budget (₹)", 0)) for p in projects)

        status_counts = {
            status: sum(1 for p in projects if p.get("Status") == status)
            for status in PROJECT_STATUSES
        }

        col1, col2, col3, col4, col5 = st.columns(5)

        col1.metric("Total Projects", total_projects)
        col2.metric("Total Budget", money_short(total_budget))
        col3.metric("Planning", status_counts["Planning"])
        col4.metric("In Progress", status_counts["In Progress"])
        col5.metric("Completed", status_counts["Completed"])

        st.caption(
            f"On Hold: {status_counts['On Hold']}  |  "
            f"Cancelled: {status_counts['Cancelled']}"
        )

        st.divider()
        st.subheader("Find Projects")

        search = st.text_input(
            "Search by project or client name",
            placeholder="Enter a project or client name..."
        )

        filter_col1, filter_col2 = st.columns(2)

        with filter_col1:
            type_options = ["All"]

            if "Type" in df.columns:
                type_options += sorted(df["Type"].dropna().unique().tolist())

            selected_type = st.selectbox("Construction Type", type_options)

        with filter_col2:
            selected_status = st.selectbox(
                "Project Status",
                ["All"] + PROJECT_STATUSES
            )

        filtered = df.copy()

        if search:
            project_mask = filtered.get(
                "Project", pd.Series("", index=filtered.index)
            ).astype(str).str.contains(search, case=False, na=False, regex=False)

            client_mask = filtered.get(
                "Client", pd.Series("", index=filtered.index)
            ).astype(str).str.contains(search, case=False, na=False, regex=False)

            filtered = filtered[project_mask | client_mask]

        if selected_type != "All" and "Type" in filtered.columns:
            filtered = filtered[filtered["Type"] == selected_type]

        if selected_status != "All" and "Status" in filtered.columns:
            filtered = filtered[filtered["Status"] == selected_status]

        st.divider()
        st.subheader(f"Projects ({len(filtered)})")

        if filtered.empty:
            st.warning("No projects match your search and filters.")

        else:

            for _, project in filtered.iloc[::-1].iterrows():

                project_id = project.get("ID")
                current_status = project.get("Status")

                if current_status not in PROJECT_STATUSES:
                    current_status = PROJECT_STATUSES[0]

                status_key = f"status_{project_id}"

                # Keep the widget in sync with the stored project status.
                st.session_state.setdefault(status_key, current_status)

                with st.container(border=True):

                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.markdown(
                            f"### 🏗️ {project.get('Project', 'Unnamed Project')}"
                        )

                        st.write(f"**Client:** {project.get('Client', 'N/A')}")

                        st.caption(
                            f"{project.get('Type', 'N/A')} | "
                            f"{project.get('Building Type', 'N/A')}"
                        )

                    with col2:
                        st.metric(
                            "Estimated Budget",
                            money_short(project.get("Budget (₹)", 0))
                        )

                        st.selectbox(
                            "Update Status",
                            PROJECT_STATUSES,
                            key=status_key,
                            on_change=update_project_status,
                            args=(project_id,)
                        )

                    with st.expander("View Project Details"):

                        details_col1, details_col2 = st.columns(2)

                        with details_col1:
                            st.write("**Floors:**", project.get("Floors", "N/A"))

                            st.write(
                                "**Construction Area:**",
                                f"{project.get('Area', 'N/A')} "
                                f"{project.get('Unit', 'sq.ft')}"
                            )

                            st.write("**Foundation:**", project.get("Foundation", "N/A"))
                            st.write(
                                "**Wall Material:**", project.get("Wall Material", "N/A")
                            )

                        with details_col2:
                            st.write("**Roof:**", project.get("Roof", "N/A"))
                            st.write("**Flooring:**", project.get("Flooring", "N/A"))
                            st.write(
                                "**Date Created:**", project.get("Date Created", "N/A")
                            )
                            st.write("**Status:**", current_status)

                            status_updated = project.get("Status Updated")
                            if isinstance(status_updated, str) and status_updated:
                                st.write("**Status Updated:**", status_updated)

                        st.write(
                            "**Project Description:**",
                            project.get("project_description") or "Not specified"
                        )

                        st.write(
                            "**Additional Requirements:**",
                            project.get("additional_requirements") or "Not specified"
                        )

        st.divider()
        st.subheader("Project Reports")

        export_all = df.drop(columns=["ID"], errors="ignore")
        export_filtered = filtered.drop(columns=["ID"], errors="ignore")

        download_col1, download_col2 = st.columns(2)

        with download_col1:
            st.download_button(
                "⬇️ Download All Projects",
                data=export_all.to_csv(index=False).encode("utf-8"),
                file_name="sitecraft_all_projects.csv",
                mime="text/csv",
                use_container_width=True
            )

        with download_col2:
            st.download_button(
                "⬇️ Download Filtered Projects",
                data=export_filtered.to_csv(index=False).encode("utf-8"),
                file_name="sitecraft_filtered_projects.csv",
                mime="text/csv",
                use_container_width=True
            )


# =========================================================
# SETTINGS
# =========================================================

elif st.session_state.page == "Settings":

    st.title("⚙️ Settings")
    st.caption("Manage your SiteCraft profile and application preferences.")

    profile_tab, preference_tab, about_tab = st.tabs([
        "Profile",
        "Preferences",
        "About SiteCraft"
    ])

    # -----------------------------------------------------
    # PROFILE
    # -----------------------------------------------------

    with profile_tab:

        st.subheader("Profile Information")
        st.caption("Enter the details associated with your workspace.")

        with st.form("profile_settings_form"):

            profile_name = st.text_input(
                "Your Name", value=st.session_state.profile_name
            )

            profile_email = st.text_input(
                "Email Address", value=st.session_state.profile_email
            )

            company_name = st.text_input(
                "Company / Organisation", value=st.session_state.company_name
            )

            profile_phone = st.text_input(
                "Phone Number", value=st.session_state.profile_phone
            )

            profile_submit = st.form_submit_button(
                "Save Profile",
                type="primary",
                use_container_width=True
            )

        if profile_submit:

            if profile_email and not re.match(
                r"^[^@\s]+@[^@\s]+\.[^@\s]+$", profile_email.strip()
            ):
                st.error("Please enter a valid email address.")

            else:
                st.session_state.profile_name = profile_name.strip()
                st.session_state.profile_email = profile_email.strip()
                st.session_state.company_name = company_name.strip()
                st.session_state.profile_phone = profile_phone.strip()

                st.success("Profile information saved for this session.")

    # -----------------------------------------------------
    # PREFERENCES
    # -----------------------------------------------------

    with preference_tab:

        st.subheader("Application Preferences")

        currency_options = ["INR (₹)", "USD ($)", "EUR (€)", "GBP (£)"]

        selected_currency = st.selectbox(
            "Display Currency",
            currency_options,
            index=selected_index(currency_options, st.session_state.currency)
        )

        notifications = st.toggle(
            "Enable Notifications",
            value=st.session_state.notifications
        )

        if st.button("Save Preferences", type="primary"):

            st.session_state.currency = selected_currency
            st.session_state.notifications = notifications

            st.success("Preferences saved for this session.")

        st.info(
            "Currency selection currently changes the display preference only. "
            "It does not convert existing project amounts or apply live exchange rates."
        )

    # -----------------------------------------------------
    # ABOUT
    # -----------------------------------------------------

    with about_tab:

        st.subheader("About SiteCraft")

        st.markdown("""
        ### 🏗️ SiteCraft

        **Smart Construction Workspace**

        SiteCraft is a construction management application designed to
        organise project information, estimate material quantities,
        generate invoices and explore AI-assisted interior design concepts.
        """)

        st.divider()

        about_col1, about_col2 = st.columns(2)

        with about_col1:
            st.write("**Application:** SiteCraft")
            st.write("**Version:** 1.0")
            st.write("**Framework:** Python + Streamlit")

        with about_col2:
            st.write("**Data Processing:** Pandas")
            st.write("**AI Provider:** Google Gemini")
            st.write("**PDF Generation:** ReportLab")

        st.divider()

        st.markdown("**Current Modules**")

        st.write("✓ Dashboard")
        st.write("✓ New Project")
        st.write("✓ AI Interior Designer")
        st.write("✓ Material Calculator")
        st.write("✓ Invoice Generator")
        st.write("✓ Project History")
        st.write("✓ Settings")

        st.warning(
            "Project data and settings currently use Streamlit session state. "
            "They are not permanently stored. Database integration and "
            "backend connection are planned for the next development stage."
        )

    st.divider()

    st.caption("SiteCraft v1.0 | Build Smarter. Plan Better.")