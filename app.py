
import streamlit as st
import pandas as pd
import base64
import re
from google import genai

# ---------------- PAGE CONFIGURATION ----------------

st.set_page_config(
    page_title="SiteCraft | Smart Construction",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- SESSION STATE ----------------

if "projects" not in st.session_state:
    st.session_state.projects = []

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

if "main_menu" not in st.session_state:
    st.session_state.main_menu = st.session_state.page


# ---------------- NAVIGATION FUNCTIONS ----------------

def navigate_to(page):
    st.session_state.page = page


def sync_navigation():
    st.session_state.page = st.session_state.main_menu


# ---------------- CUSTOM CSS ----------------

st.markdown("""
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


/* RESTORE HERO SECTION */

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

/* RESTORE METRIC CARDS */

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

/* RESTORE EMPTY PROJECT MESSAGE */

[data-testid="stAlert"] {
    background: #ffffff !important;
    color: #172a43 !important;
    border: 1px solid #e5eaf0;
    border-radius: 12px;
}


/* =================================
   QUICK ACTION BUTTONS
================================= */

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

/* =================================
   RECENT PROJECTS MESSAGE
================================= */

[data-testid="stAlert"] {
    background-color: #ffffff !important;
    border: 1px solid #dce4ed !important;
    border-radius: 12px !important;
}

[data-testid="stAlert"] p {
    color: #172a43 !important;
}

[data-testid="stAlert"] [data-testid="stMarkdownContainer"] {
    color: #172a43 !important;
}

/* =================================
   RECENT PROJECTS DATA
================================= */

[data-testid="stDataFrame"] {
    background-color: #ffffff !important;
    border-radius: 12px;
}




</style>
""", unsafe_allow_html=True)


# ---------------- SIDEBAR ----------------

with st.sidebar:

    st.markdown("# 🏗️ SiteCraft")
    st.caption("SMART CONSTRUCTION WORKSPACE")

    st.divider()

    st.markdown("##### MAIN MENU")

    pages = [
        "Dashboard",
        "New Project",
        "AI Estimation",
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


# ---------------- DASHBOARD ----------------

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

    total_projects = len(st.session_state.projects)

    total_value = sum(
        project["Budget (₹)"]
        for project in st.session_state.projects
    )

    completed_projects = sum(
        1 for project in st.session_state.projects
        if project.get("Status") == "Completed"
    )

    # Dashboard metrics

    col1, col2, col3, col4 = st.columns(4)

    metrics = [
        (col1, "TOTAL PROJECTS", str(total_projects)),
        (col2, "ESTIMATED VALUE", f"₹{total_value:,.0f}"),
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

    # Recent projects

    with left:

        st.subheader("📋 Recent Projects")

        if st.session_state.projects:

            df = pd.DataFrame(
                st.session_state.projects
            )

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

        
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
            type="primary"
        ):
            navigate_to("New Project")
            st.rerun()

        if st.button(
            "✦ AI Estimation",
            use_container_width=True
        ):
            navigate_to("AI Estimation")
            st.rerun()

        if st.button(
            "▤ Generate Invoice",
            use_container_width=True
        ):
            navigate_to("Invoice Generator")
            st.rerun()

        st.write("")

        st.caption("Your construction workspace, all in one place.")



# ---------------- NEW PROJECT ----------------

elif st.session_state.page == "New Project":

    st.title("🏗️ Create New Project")
    st.caption("Set up your construction project details.")

    st.divider()

    st.subheader("Project Information")

    with st.form("project_form"):

        col1, col2 = st.columns(2)

        with col1:
            project_name = st.text_input(
                "Project Name *",
                placeholder="Example: Dream Villa"
            )

            client_name = st.text_input(
                "Client Name",
                placeholder="Enter client name"
            )

        with col2:
            project_type = st.selectbox(
                "Project Type",
                [
                    "Residential",
                    "Commercial",
                    "Renovation",
                    "Interior Design"
                ]
            )

            area = st.number_input(
                "Built-up Area (sq.ft)",
                min_value=0.0,
                value=1200.0
            )

        st.divider()

        st.subheader("Budget Details")

        budget = st.number_input(
            "Estimated Budget (₹)",
            min_value=0.0,
            value=1000000.0,
            step=50000.0
        )

        st.caption("Fields marked * are required.")

        submit = st.form_submit_button(
            "＋ Create Project",
            type="primary",
            use_container_width=True
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

                project = {
                    "Project": project_name.strip(),
                    "Client": client_name.strip(),
                    "Type": project_type,
                    "Area (sq.ft)": area,
                    "Budget (₹)": budget,
                    "Status": "Planning"
                }

                st.session_state.projects.append(project)

                st.success(
                    f"Project '{project_name}' created successfully!"
                )




# ---------------- AI ESTIMATION / INTERIOR DESIGN ----------------

elif st.session_state.page == "AI Estimation":

    

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
        help="Upload a clear photo of the wall you want to decorate."
    )

    if uploaded_file:
        st.image(
            uploaded_file,
            caption="Your original wall",
            use_container_width=True
        )

        if st.button("Analyse My Wall & Suggest Designs", type="primary"):

            try:
                client = genai.Client(
                    api_key=st.secrets["GEMINI_API_KEY"],
                    http_options={"timeout": 120000}
                )

                image_bytes = uploaded_file.getvalue()

                with st.spinner("Gemini is analysing your wall..."):

                    analysis = client.interactions.create(
                        model="gemini-3.8-flash",
                        input=[
                            {
                                "type": "text",
                                "text": """
                                Analyse this wall photograph for interior design.

                                Suggest exactly THREE different, practical
                                interior wall design ideas.

                                Consider the existing wall, its appearance,
                                lighting and visible surroundings.

                                Return exactly three numbered suggestions.
                                Each suggestion should include:
                                - Design style
                                - Suggested materials
                                - Colour combination
                                - Decorative elements

                                Keep each suggestion concise.
                                Do not provide prices.
                                """
                            },
                            {
                                "type": "image",
                                "data": base64.b64encode(
                                    image_bytes
                                ).decode("utf-8"),
                                "mime_type": uploaded_file.type
                            }
                        ]
                    )

                suggestions_text = analysis.output_text or ""

                suggestions = []

                for line in suggestions_text.splitlines():
                    line = re.sub(
                        r"^\s*(?:\d+[).:-]?|[-*•])\s*",
                        "",
                        line
                    ).strip()

                    if line:
                        suggestions.append(line)

                suggestions = suggestions[:3]

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

    # STEP 2: SHOW DESIGN SUGGESTIONS

    if st.session_state.get("sitecraft_suggestions"):

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
            [
                "Choose an AI suggestion",
                "Create my own design idea"
            ]
        )

        selected_design = ""

        if design_choice == "Choose an AI suggestion":

            selected_design = st.selectbox(
                "Select your favourite design",
                suggestions
            )

        else:

            selected_design = st.text_area(
                "Describe your dream wall design",
                placeholder=(
                    "Example: I want a modern wooden panel wall "
                    "with warm LED lighting and a marble finish."
                )
            )

        # STEP 4: GENERATE CUSTOM DESIGN IMAGE

        if st.button("Generate My Interior Design", type="primary"):

            if not selected_design.strip():

                st.error("Please select or describe a design first.")

            else:

                try:
                    client = genai.Client(
                        api_key=st.secrets["GEMINI_API_KEY"],
                        http_options={"timeout": 120000}
                    )

                    with st.spinner(
                        "Gemini is creating your interior design..."
                    ):

                        image_generation = client.interactions.create(
                            model="gemini-3.1-flash-image",
                            input=[
                                {
                                    "type": "text",
                                    "text": f"""
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
                                },
                                {
                                    "type": "image",
                                    "data": base64.b64encode(
                                        st.session_state[
                                            "sitecraft_wall_image"
                                        ]
                                    ).decode("utf-8"),
                                    "mime_type": st.session_state[
                                        "sitecraft_wall_mime"
                                    ]
                                }
                            ]
                        )

                    generated_image = image_generation.output_image

                    if generated_image:

                        generated_bytes = base64.b64decode(
                            generated_image.data
                        )

                        st.session_state[
                            "sitecraft_generated_image"
                        ] = generated_bytes

                        st.session_state[
                            "sitecraft_selected_design"
                        ] = selected_design

                    else:
                        st.error(
                            "Gemini did not return an image. "
                            "Please try again."
                        )

                except Exception as e:
                    st.error(f"Image generation failed: {e}")

        # STEP 5: DISPLAY GENERATED DESIGN

        if st.session_state.get("sitecraft_generated_image"):

            st.divider()
            st.subheader("4. Your Custom Interior Design")

            st.image(
                st.session_state["sitecraft_generated_image"],
                caption="AI-generated interior design concept",
                use_container_width=True
            )

            st.success("Your interior design preview is ready!")

            st.info(
                "Next: We will connect this design to the "
                "AI construction cost estimation feature."
            )



# ---------------- INVOICE GENERATOR ----------------

elif st.session_state.page == "Invoice Generator":

    st.title("▤ Invoice Generator")

    st.caption(
        "Create professional construction invoices."
    )

    st.info(
        "Invoice generation interface is ready for development."
    )


# ---------------- PROJECT HISTORY ----------------

elif st.session_state.page == "Project History":

    st.title("📁 Project History")

    st.caption("View your previously created projects.")

    if st.session_state.projects:

        df = pd.DataFrame(
            st.session_state.projects
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No project history available yet.")


# ---------------- SETTINGS ----------------

elif st.session_state.page == "Settings":

    st.title("⚙️ Settings")

    st.subheader("Application Information")

    st.write("Application: SiteCraft")
    st.write("Framework: Python + Streamlit")
    st.write("AI Provider: Google Gemini")
    st.write("Version: 1.0")

    st.info(
        "Backend configuration will be integrated during the next stage."
    )
