import os
import sys
import streamlit as st

# Ensure the root directory is in the Python path so we can import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db import get_kpi_summary

# 1. Set page config
st.set_page_config(
    page_title="TrialLens",
    layout="wide",
    page_icon="🔍"
)

# 6. Sidebar with project name and About blurb
with st.sidebar:
    st.title("TrialLens")
    st.markdown("""
    **About**
    
    TrialLens is an analytical dashboard designed to uncover the hidden behavioral patterns 
    that predict SaaS free-trial conversion.
    """)

# 2. Header section
st.title("TrialLens")
st.markdown("### Connecting free-trial behavior to subscription conversion.")

# Determine the absolute path to the database to avoid CWD issues
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'trialens.db'))

# 5. Load data with try/except
try:
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    # 3. Call get_kpi_summary and display as 3 metrics
    kpis = get_kpi_summary(db_path=DB_PATH)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Trial Users", f"{kpis['total_users']:,}")
        
    with col2:
        st.metric("Conversion Rate", f"{kpis['overall_conversion_rate']}%")
        
    with col3:
        st.metric("Avg Time to Convert (days)", f"{kpis['avg_time_to_convert']}")
        
    # 4. Divider and placeholder
    st.divider()
    
    st.subheader("Key Insight")
    st.info("Charts coming next.")
    
    # --- CHARTS AND FILTERS SECTION (To be added later) ---
    
except Exception as e:
    st.error("⚠️ Database Not Found or Data Error")
    st.error(
        "Could not load data from `data/trialens.db`. Please ensure you have run the "
        "pipeline scripts (`src/ingest.py`, `src/clean.py`, `src/features.py`) to generate "
        "the database before launching the app."
    )
    st.exception(e)
