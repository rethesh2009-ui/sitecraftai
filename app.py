
import streamlit as st
import pandas as pd

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
    st.session_state.main_menu = page
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
            st.info(
                "No projects yet. Create your first project to get started!"
            )

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



# ---------------- AI ESTIMATION ----------------

elif st.session_state.page == "AI Estimation":

    st.title("✦ AI Construction Estimation")

    st.caption(
        "Generate preliminary construction estimates "
        "using Google's Gemini AI."
    )

    st.info(
        "The AI estimation interface is ready for backend integration."
    )

    description = st.text_area(
        "Describe your construction project",
        placeholder="Example: Build a 2BHK residential house..."
    )

    if st.button("Generate AI Estimate", type="primary"):

        if description.strip():
            st.warning(
                "AI integration will be connected with Vishnu's backend."
            )
        else:
            st.error("Please enter your project details.")


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
