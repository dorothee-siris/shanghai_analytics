"""
University Rankings Dashboard
Main entry point - handles navigation between views
"""
import streamlit as st

st.set_page_config(
    page_title="University Rankings Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🎓 University Rankings Dashboard")
st.markdown("""
Welcome to the University Rankings Dashboard. This tool allows you to explore 
**ARWU (Academic Ranking of World Universities)** and **GRAS (Global Ranking of Academic Subjects)** data.

### Available Views

- **🏛️ Institution View**: Analyze a specific institution's performance over time
- **🌍 Country View**: Compare institutions within a country *(coming soon)*

Use the sidebar to navigate between views.
""")

st.sidebar.success("Select a view above.")

st.markdown("---")
st.markdown("### Data Sources")
col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    **ARWU** (2017-2025)
    - Overall university rankings
    - Indicators: Alumni, Award, HiCi, N&S, PUB, PCP
    """)
with col2:
    st.markdown("""
    **GRAS** (2021-2025)
    - Subject-level rankings
    - Multiple fields and subjects
    - Methodology change in 2024
    """)