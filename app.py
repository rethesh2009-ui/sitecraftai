
import streamlit as st
import pandas as pd
from google import genai

# ---------------- PAGE CONFIGURATION ----------------

st.set_page_config(
    page_title="SiteCraft | Smart Construction",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- CUSTOM CSS ----------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;600;700;800&display=swap');

.stApp {
    background: #f4f6fa;
    font-family: 'DM Sans', sans-serif;
}

[data-testid="stSidebar"] {
    background: #142238;
}

[data-testid="stSidebar"] * {
    color: white;
}

.block-container {
    padding-top: 2rem;
    max-width: 1450px;
}

.hero {
    background: linear-gradient(120deg, #142238, #24516a);
    padding: 35px;
    border-radius: 18px;
    color: white;
    margin-bottom: 25px;
}

.hero h1 {
    color: white;
    font-family: 'Manrope', sans-serif;
    font-size: 36px;
}

.hero p {
    color: #d5e2ee;
    font-size: 16px;
}

.metric {
    background: white;
    padding: 22px;
    border-radius: 15px;
    border: 1px solid #e5eaf0;
}

.metric-label {
    color: #78869a;
    font-size: 13px;
}

.metric-value {
    color: #172a43;
    font-size: 27px;
    font-weight: 800;
}

div.stButton > button {
    border-radius: 9px;
    font-weight: 600;
    min-height: 42px;
}

</style>
""", unsafe_allow_html=True)


# ---------------- SESSION STATE ----------------

if "projects" not in st.session_state:
    st.session_state.projects = []

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"


# ---------------- SIDEBAR ----------------

with st.sidebar:

    st.markdown("# 🏗️ SiteCraft")
    st.caption("SMART CONSTRUCTION WORKSPACE")

    st.divider()

    pages = [
        "Dashboard",
        "New Project",
        "AI Estimation",
        "Invoice Generator",
        "Project History",
        "Settings"
    ]

    selected_page = st.radio(
        "MAIN MENU",
        pages
    )

    st.session_state.page = selected_page

    st.divider()

    st.caption("BUILD SMARTER. PLAN BETTER.")
    st.caption("SiteCraft v1.0")

    st.divider()


with st.sidebar:
    if st.button("Test Gemini Connection", use_container_width=True):
        try:
            st.info("Connecting to Gemini...")

            client = genai.Client(
                api_key=st.secrets["GEMINI_API_KEY"],
                http_options={"timeout": 120000}
            )

            result = client.interactions.create(
                model="gemini-3.8-flash",
                input="Reply with exactly: SiteCraft connected!"
            )

            st.success("Gemini connected successfully!")
            st.write(result.output_text)

        except Exception as e:
            st.error(f"Connection failed: {e}")


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

    # Dashboard metrics

    col1, col2, col3, col4 = st.columns(4)

    total_projects = len(st.session_state.projects)

    total_value = sum(
        p["budget"] for p in st.session_state.projects
    )

    metrics = [
        (col1, "TOTAL PROJECTS", total_projects),
        (col2, "ESTIMATED VALUE", f"₹{total_value:,.0f}"),
        (col3, "COMPLETED PROJECTS", 0),
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

    left, right = st.columns([1.6, 1])

    with left:

        st.subheader("Recent Projects")

        if st.session_state.projects:

            df = pd.DataFrame(st.session_state.projects)

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

        else:
            st.info("No projects yet. Create your first project!")

    with right:

        st.subheader("Quick Actions")

        if st.button("＋ Create New Project", use_container_width=True):
            st.session_state.page = "New Project"
            st.rerun()

        if st.button("✦ AI Estimation", use_container_width=True):
            st.session_state.page = "AI Estimation"
            st.rerun()

        if st.button("▤ Generate Invoice", use_container_width=True):
            st.session_state.page = "Invoice Generator"
            st.rerun()


# ---------------- NEW PROJECT ----------------

elif st.session_state.page == "New Project":

    st.title("Create New Project")
    st.caption("Enter your construction project details.")

    with st.form("project_form"):

        project_name = st.text_input("Project Name")

        client_name = st.text_input("Client Name")

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

        budget = st.number_input(
            "Estimated Budget (₹)",
            min_value=0.0,
            value=1000000.0
        )

        submit = st.form_submit_button(
            "Create Project",
            type="primary"
        )

        if submit:

            if not project_name.strip():
                st.error("Please enter a project name.")

            else:

                project = {
                    "Project": project_name,
                    "Client": client_name,
                    "Type": project_type,
                    "Area (sq.ft)": area,
                    "Budget (₹)": budget
                }

                st.session_state.projects.append(project)

                st.success("Project created successfully!")


# ---------------- AI ESTIMATION ----------------

elif st.session_state.page == "AI Estimation":

    st.title("AI Construction Estimation")

    st.write(
        "Generate preliminary construction estimates "
        "using Google's Gemini AI."
    )

    st.info("Gemini integration will be added in the next development stage.")

    description = st.text_area(
        "Describe your construction project",
        placeholder="Example: Build a 2BHK residential house..."
    )

    if st.button("Generate AI Estimate", type="primary"):

        if description.strip():
            st.warning("Gemini API integration is coming next.")
        else:
            st.error("Enter project details first.")


# ---------------- INVOICE GENERATOR ----------------

elif st.session_state.page == "Invoice Generator":

    st.title("Invoice Generator")

    st.write(
        "Generate professional construction invoices."
    )

    st.info("Invoice generation module will be connected next.")


# ---------------- PROJECT HISTORY ----------------

elif st.session_state.page == "Project History":

    st.title("Project History")

    if st.session_state.projects:

        st.dataframe(
            pd.DataFrame(st.session_state.projects),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No project history available.")


# ---------------- SETTINGS ----------------

elif st.session_state.page == "Settings":

    st.title("Settings")

    st.subheader("Application Information")

    st.write("Application: SiteCraft")
    st.write("Framework: Python + Streamlit")
    st.write("AI Provider: Google Gemini")
    st.write("Version: 1.0")

    st.info("Gemini API configuration will be added next.")



if st.button("Test Gemini Connection", use_container_width=True):
    st.info("Connecting to Gemini...")

    try:
        client = genai.Client(
            api_key=st.secrets["GEMINI_API_KEY"]
        )

        response = client.interactions.create(
            model="gemini-3.8-flash",
            input="Reply with exactly: SiteCraft connected!"
        )

        st.success("Gemini connected successfully!")
        st.write(response.output_text)

    except Exception as e:
        st.error(f"Connection failed: {e}")

