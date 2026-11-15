import base64
import re
import time

import pandas as pd
import streamlit as st
from google import genai


# ---------------- PAGE CONFIGURATION ----------------

st.set_page_config(
    page_title="SiteCraft | Smart Construction",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = [
    "Dashboard",
    "New Project",
    "AI Estimation",
    "Invoice Generator",
    "Project History",
    "Settings",
]

# ---------------- SESSION STATE ----------------

if "projects" not in st.session_state:
    st.session_state.projects = []

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

if "main_menu" not in st.session_state:
    st.session_state.main_menu = st.session_state.page


# ---------------- NAVIGATION ----------------

def navigate_to(page):
    st.session_state.page = page


def sync_navigation():
    st.session_state.page = st.session_state.main_menu


# ---------------- CUSTOM CSS ----------------

CUSTOM_CSS = """
<style>

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

/* MAIN CONTENT TEXT */

[data-testid="stMain"] h1,
[data-testid="stMain"] h2,
[data-testid="stMain"] h3,
[data-testid="stMain"] p,
[data-testid="stMain"] label,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] {
    color: #172a43;
}

/* INPUT BOXES */

[data-testid="stMain"] input,
[data-testid="stMain"] textarea,
[data-testid="stMain"] [data-baseweb="select"] > div {
    background-color: #ffffff !important;
    color: #172a43 !important;
    border-color: #dce4ed !important;
}

/* INPUT PLACEHOLDER */

[data-testid="stMain"] input::placeholder,
[data-testid="stMain"] textarea::placeholder {
    color: #8492a6 !important;
}

/* FORM CONTAINER */

[data-testid="stForm"] {
    background: #ffffff;
    padding: 22px;
    border: 1px solid #e5eaf0;
    border-radius: 16px;
}

/* SECTION HEADINGS */

[data-testid="stMain"] h1,
[data-testid="stMain"] h2,
[data-testid="stMain"] h3 {
    font-weight: 800;
}

/* HERO SECTION */

.hero {
    background: linear-gradient(120deg, #142238, #24516a);
    padding: 38px;
    border-radius: 20px;
    color: white;
    margin-bottom: 28px;
    min-height: 195px;
}

.hero h1 {
    color: white !important;
    font-family: 'Manrope', sans-serif;
    font-size: 38px;
    font-weight: 800;
}

.hero p {
    color: #d5e2ee !important;
    font-size: 16px;
}

/* METRIC CARDS */

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

/* ALERT / INFO MESSAGES */

[data-testid="stAlert"] {
    background-color: #ffffff !important;
    color: #172a43 !important;
    border: 1px solid #dce4ed !important;
    border-radius: 12px !important;
}

[data-testid="stAlert"] p,
[data-testid="stAlert"] [data-testid="stMarkdownContainer"] {
    color: #172a43 !important;
}

/* BUTTONS */

div.stButton > button {
    background-color: #167d83 !important;
    color: #ffffff !important;
    border: 1px solid #167d83 !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    min-height: 44px;
}

div.stButton > button p,
div.stButton > button span {
    color: #ffffff !important;
}

div.stButton > button:hover {
    background-color: #11676c !important;
    border-color: #11676c !important;
}

/* DATAFRAME */

[data-testid="stDataFrame"] {
    background-color: #ffffff !important;
    border-radius: 12px;
}

</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------------- HELPERS ----------------

def get_gemini_client():
    return genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"],
        http_options={"timeout": 300000},
    )


def to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


def show_projects_table():
    df = pd.DataFrame(st.session_state.projects)
    st.dataframe(df, use_container_width=True, hide_index=True)


WALL_ANALYSIS_PROMPT = """
Analyse this wall photograph for interior design.

Suggest exactly THREE different,
practical interior wall design ideas.

Consider the existing wall,
its appearance, lighting and
visible surroundings.

Return exactly three numbered
suggestions.

Each suggestion should include:
- Design style
- Suggested materials
- Colour combination
- Decorative elements

Keep each suggestion concise.
Do not provide prices.
"""


def build_design_prompt(selected_design: str) -> str:
    return f"""
Redesign the wall in the provided
photograph.

Customer's chosen design:
{selected_design}

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


def parse_suggestions(text: str):
    """Extract up to three suggestions from Gemini's numbered response."""
    suggestions = re.split(r"(?m)^\s*\d+[).:-]\s*", text)
    suggestions = [item.strip() for item in suggestions if item.strip()]

    # Fallback if Gemini did not number its suggestions
    if len(suggestions) < 3:
        suggestions = [
            line.strip() for line in text.splitlines() if line.strip()
        ]

    return suggestions[:3]


def analyse_wall(client, image_bytes: bytes, mime_type: str):
    """Call Gemini to analyse the wall, retrying on 503 errors."""
    for attempt in range(3):
        try:
            return client.interactions.create(
                model="gemini-3.5-flash",
                input=[
                    {"type": "text", "text": WALL_ANALYSIS_PROMPT},
                    {
                        "type": "image",
                        "data": to_base64(image_bytes),
                        "mime_type": mime_type,
                    },
                ],
            )
        except Exception as e:
            if "503" in str(e) and attempt < 2:
                time.sleep(3 * (attempt + 1))
            else:
                raise
    return None


# ---------------- SIDEBAR ----------------

with st.sidebar:

    st.markdown("# 🏗️ SiteCraft")
    st.caption("SMART CONSTRUCTION WORKSPACE")

    st.divider()

    st.markdown("##### MAIN MENU")

    st.radio(
        "Navigation",
        PAGES,
        key="main_menu",
        label_visibility="collapsed",
        on_change=sync_navigation,
    )

    st.divider()

    st.caption("BUILD SMARTER. PLAN BETTER.")
    st.caption("SiteCraft v1.0")


# ---------------- PAGE FUNCTIONS ----------------

def render_dashboard():

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
    total_value = sum(project["Budget (₹)"] for project in projects)
    completed_projects = sum(
        1 for project in projects if project.get("Status") == "Completed"
    )

    col1, col2, col3, col4 = st.columns(4)

    metrics = [
        (col1, "TOTAL PROJECTS", str(total_projects)),
        (col2, "ESTIMATED VALUE", f"₹{total_value:,.0f}"),
        (col3, "COMPLETED PROJECTS", str(completed_projects)),
        (col4, "AI STATUS", "Ready"),
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

    # Recent projects
    with left:

        st.subheader("📋 Recent Projects")

        if projects:
            show_projects_table()
        else:
            st.markdown("""
            <div style="
                background-color: #ffffff;
                border: 1px solid #dce4ed;
                border-radius: 12px;
                padding: 20px;
                color: #172a43;
                font-size: 15px;
                font-weight: 500;
            ">
                No projects yet. Create your first project to get started!
            </div>
            """, unsafe_allow_html=True)

    # Quick actions
    with right:

        st.subheader("⚡ Quick Actions")

        if st.button(
            "＋ Create New Project",
            use_container_width=True,
            type="primary",
        ):
            navigate_to("New Project")
            st.rerun()

        if st.button("✦ AI Estimation", use_container_width=True):
            navigate_to("AI Estimation")
            st.rerun()

        if st.button("▤ Generate Invoice", use_container_width=True):
            navigate_to("Invoice Generator")
            st.rerun()

        st.write("")

        st.caption("Your construction workspace, all in one place.")


def render_new_project():

    st.title("🏗️ Create New Project")
    st.caption("Set up your construction project details.")

    st.divider()

    st.subheader("Project Information")

    with st.form("project_form"):

        col1, col2 = st.columns(2)

        with col1:
            project_name = st.text_input(
                "Project Name *",
                placeholder="Example: Dream Villa",
            )

            client_name = st.text_input(
                "Client Name",
                placeholder="Enter client name",
            )

        with col2:
            project_type = st.selectbox(
                "Project Type",
                ["Residential", "Commercial", "Renovation", "Interior Design"],
            )

            area = st.number_input(
                "Built-up Area (sq.ft)",
                min_value=0.0,
                value=1200.0,
            )

        st.divider()

        st.subheader("Budget Details")

        budget = st.number_input(
            "Estimated Budget (₹)",
            min_value=0.0,
            value=1000000.0,
            step=50000.0,
        )

        st.caption("Fields marked * are required.")

        submit = st.form_submit_button(
            "＋ Create Project",
            type="primary",
            use_container_width=True,
        )

        if submit:

            if not project_name.strip():
                st.error("Please enter a project name.")

            elif any(
                p["Project"].strip().lower() == project_name.strip().lower()
                for p in st.session_state.projects
            ):
                st.error("A project with this name already exists.")

            else:
                st.session_state.projects.append({
                    "Project": project_name.strip(),
                    "Client": client_name.strip(),
                    "Type": project_type,
                    "Area (sq.ft)": area,
                    "Budget (₹)": budget,
                    "Status": "Planning",
                })

                st.success(f"Project '{project_name}' created successfully!")


def run_wall_analysis(uploaded_file):
    """Step 1 action: analyse the uploaded wall and store suggestions."""
    try:
        client = get_gemini_client()
        image_bytes = uploaded_file.getvalue()

        with st.spinner("Gemini is analysing your wall..."):
            analysis = analyse_wall(client, image_bytes, uploaded_file.type)

        if analysis is None:
            raise RuntimeError("Gemini did not return an analysis.")

        suggestions = parse_suggestions(analysis.output_text or "")

        if len(suggestions) < 3:
            st.error(
                "Gemini did not return three suggestions. "
                "Please try analysing the photo again."
            )
        else:
            st.session_state["sitecraft_wall_image"] = image_bytes
            st.session_state["sitecraft_wall_mime"] = uploaded_file.type
            st.session_state["sitecraft_suggestions"] = suggestions
            st.session_state["sitecraft_generated_image"] = None

            st.success("Your wall analysis is complete!")

    except Exception as e:
        st.error(f"Unable to analyse the image: {e}")


def run_design_generation(selected_design: str):
    """Step 4 action: generate the redesigned wall image."""
    try:
        client = get_gemini_client()

        with st.spinner("Gemini is creating your interior design..."):
            image_generation = client.interactions.create(
                model="gemini-3.5-flash-image",
                input=[
                    {"type": "text", "text": build_design_prompt(selected_design)},
                    {
                        "type": "image",
                        "data": to_base64(st.session_state["sitecraft_wall_image"]),
                        "mime_type": st.session_state["sitecraft_wall_mime"],
                    },
                ],
            )

        generated_image = image_generation.output_image

        if generated_image:
            st.session_state["sitecraft_generated_image"] = base64.b64decode(
                generated_image.data
            )
            st.session_state["sitecraft_selected_design"] = selected_design
        else:
            st.error("Gemini did not return an image. Please try again.")

    except Exception as e:
        st.error(f"Image generation failed: {e}")


def render_ai_estimation():

    st.title("✦ AI Interior Designer")

    st.caption(
        "Upload your wall photo, explore AI design ideas "
        "and generate your customised interior design."
    )

    st.divider()

    # STEP 1: UPLOAD WALL PHOTO

    st.subheader("1. Upload Your Wall Photo")

    uploaded_file = st.file_uploader(
        "Choose a photo of your wall",
        type=["jpg", "jpeg", "png", "webp"],
        help="Upload a clear photo of the wall you want to decorate.",
    )

    if not uploaded_file:
        return

    st.image(
        uploaded_file,
        caption="Your original wall",
        use_container_width=True,
    )

    if st.button("Analyse My Wall & Suggest Designs", type="primary"):
        run_wall_analysis(uploaded_file)

    # STEP 2: SHOW DESIGN SUGGESTIONS

    if not st.session_state.get("sitecraft_suggestions"):
        return

    st.divider()

    st.subheader("2. Explore AI Design Suggestions")

    suggestions = st.session_state["sitecraft_suggestions"]

    for index, suggestion in enumerate(suggestions, start=1):
        with st.container(border=True):
            st.markdown(f"**Design Option {index}**")
            st.write(suggestion)

    # STEP 3: CUSTOMER CHOICE

    st.divider()

    st.subheader("3. Choose Your Design")

    design_choice = st.radio(
        "How would you like to continue?",
        ["Choose an AI suggestion", "Create my own design idea"],
    )

    if design_choice == "Choose an AI suggestion":
        selected_design = st.selectbox(
            "Select your favourite design",
            suggestions,
        )
    else:
        selected_design = st.text_area(
            "Describe your dream wall design",
            placeholder=(
                "Example: I want a modern wooden panel wall "
                "with warm LED lighting and a marble finish."
            ),
        )

    # STEP 4: GENERATE CUSTOM DESIGN IMAGE

    if st.button("Generate My Interior Design", type="primary"):
        if not selected_design.strip():
            st.error("Please select or describe a design first.")
        else:
            run_design_generation(selected_design)

    # STEP 5: DISPLAY GENERATED DESIGN

    if st.session_state.get("sitecraft_generated_image"):

        st.divider()

        st.subheader("4. Your Custom Interior Design")

        st.image(
            st.session_state["sitecraft_generated_image"],
            caption="AI-generated interior design concept",
            use_container_width=True,
        )

        st.success("Your interior design preview is ready!")

        st.info(
            "Next: We will connect this design to the "
            "AI construction cost estimation feature."
        )


def render_invoice_generator():

    st.title("▤ Invoice Generator")

    st.caption("Create professional construction invoices.")

    st.info("Invoice generation interface is ready for development.")


def render_project_history():

    st.title("📁 Project History")

    st.caption("View your previously created projects.")

    if st.session_state.projects:
        show_projects_table()
    else:
        st.info("No project history available yet.")


def render_settings():

    st.title("⚙️ Settings")

    st.subheader("Application Information")

    st.write("Application: SiteCraft")
    st.write("Framework: Python + Streamlit")
    st.write("AI Provider: Google Gemini")
    st.write("Version: 1.0")

    st.info("Backend configuration will be integrated during the next stage.")


# ---------------- ROUTER ----------------

PAGE_RENDERERS = {
    "Dashboard": render_dashboard,
    "New Project": render_new_project,
    "AI Estimation": render_ai_estimation,
    "Invoice Generator": render_invoice_generator,
    "Project History": render_project_history,
    "Settings": render_settings,
}

PAGE_RENDERERS[st.session_state.page]()