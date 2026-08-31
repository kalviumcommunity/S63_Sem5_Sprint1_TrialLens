import os
import sys
import streamlit as st

# Ensure the root directory is in the Python path so we can import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import plotly.express as px
import pandas as pd
from src.db import (
    get_kpi_summary,
    get_conversion_by_core_features,
    get_conversion_by_trend,
    get_conversion_by_segment,
    get_user_features
)
from src.analysis import run_analysis

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
        with st.spinner("Setting up data pipeline for the first time... This takes about 10 seconds."):
            from src.generate_data import generate_all_data
            from src.ingest import run_ingestion
            from src.clean import run_cleaning
            from src.features import build_features
            
            raw_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'raw'))
            if not os.path.exists(os.path.join(raw_dir, 'users.csv')):
                generate_all_data(output_dir=raw_dir)
            
            run_ingestion(raw_dir=raw_dir, db_path=DB_PATH)
            run_cleaning(db_path=DB_PATH)
            build_features(db_path=DB_PATH)
            
            st.success("Data pipeline initialized successfully!")

    # Fetch base data to populate filter options dynamically
    base_df = get_user_features(db_path=DB_PATH)
    all_plans = base_df['plan_type'].dropna().unique().tolist()
    all_sizes = base_df['company_size'].dropna().unique().tolist()

    # --- SIDEBAR FILTERS ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filter Users")
    
    selected_plans = st.sidebar.multiselect("Plan Type", options=all_plans)
    selected_sizes = st.sidebar.multiselect("Company Size", options=all_sizes)
    selected_conv = st.sidebar.radio("Conversion Status", options=["All", "Converted", "Not Converted"])
    
    # Build filter dict
    filters = {}
    if selected_plans:
        filters['plan_type'] = selected_plans
    if selected_sizes:
        filters['company_size'] = selected_sizes
    if selected_conv != "All":
        filters['converted'] = True if selected_conv == "Converted" else False
        
    # Get filtered dataframe
    filtered_df = get_user_features(filters=filters, db_path=DB_PATH)

    # --- RECOMPUTE KPIs ---
    if not filtered_df.empty:
        total_users = len(filtered_df)
        conv_rate = filtered_df['converted'].mean() * 100.0
        
        # Avg time to convert
        conv_only = filtered_df[filtered_df['converted'] == True].copy()
        if not conv_only.empty and 'signup_date' in conv_only.columns and 'conversion_date' in conv_only.columns:
            conv_only['signup_date_dt'] = pd.to_datetime(conv_only['signup_date'])
            conv_only['conversion_date_dt'] = pd.to_datetime(conv_only['conversion_date'])
            avg_time = (conv_only['conversion_date_dt'] - conv_only['signup_date_dt']).dt.days.mean()
        else:
            avg_time = 0.0
    else:
        total_users = 0
        conv_rate = 0.0
        avg_time = 0.0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Trial Users", f"{total_users:,}")
        
    with col2:
        st.metric("Conversion Rate", f"{conv_rate:.1f}%")
        
    with col3:
        st.metric("Avg Time to Convert (days)", f"{avg_time:.1f}")
        
    # 4. Divider and placeholder
    st.divider()
    
    # 1a. Headline Chart
    st.subheader("Key Insight: Core Feature Engagement")
    
    # Get headline data and analysis report
    core_features_df = get_conversion_by_core_features(db_path=DB_PATH)
    analysis_report = run_analysis(db_path=DB_PATH)
    hc_stats = analysis_report.get('headline_comparison', {})
    
    fig_headline = px.bar(
        core_features_df, 
        x="feature_group", 
        y="conversion_rate", 
        title="Conversion Rate by Week 1 Core Feature Usage",
        labels={"feature_group": "User Group", "conversion_rate": "Conversion Rate (%)"},
        text_auto=".1f",
        color="feature_group",
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig_headline.update_layout(showlegend=False)
    st.plotly_chart(fig_headline, use_container_width=True)
    
    # Dynamic caption based on analysis results
    high_cr = hc_stats.get('high_core_conversion_rate', 0) * 100
    low_cr = hc_stats.get('low_core_conversion_rate', 0) * 100
    pval = hc_stats.get('p_value')
    pval_str = f"{pval:.2e}" if pval is not None else "N/A"
    sig_text = "statistically significant" if hc_stats.get('significant') else "not statistically significant"
    st.caption(
        f"**Finding:** Users who engage with 3 or more core features within their first 7 days convert at "
        f"**{high_cr:.1f}%**, compared to just **{low_cr:.1f}%** for those who don't. "
        f"This effect is {sig_text} (p-value: {pval_str})."
    )
    
    st.divider()
    
    # 2. Side-by-side charts
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.subheader("Usage Trend")
        trend_df = get_conversion_by_trend(db_path=DB_PATH)
        fig_trend = px.bar(
            trend_df,
            x="usage_trend",
            y="conversion_rate",
            title="Conversion Rate by Trial Usage Trend",
            labels={"usage_trend": "Usage Trend (2nd Half vs 1st Half)", "conversion_rate": "Conversion Rate (%)"},
            text_auto=".1f",
            color="usage_trend",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_trend.update_layout(showlegend=False)
        st.plotly_chart(fig_trend, use_container_width=True)
        
    with chart_col2:
        st.subheader("Segment Breakdown")
        segment_choice = st.selectbox(
            "Select Segment to Analyze",
            options=["plan_type", "company_size"],
            format_func=lambda x: x.replace("_", " ").title()
        )
        
        segment_df = get_conversion_by_segment(segment_choice, db_path=DB_PATH)
        
        # Handle empty gracefully
        if segment_df.empty:
            st.warning("No data available for this segment.")
        else:
            fig_segment = px.bar(
                segment_df,
                x="segment_value",
                y="conversion_rate",
                title=f"Conversion Rate by {segment_choice.replace('_', ' ').title()}",
                labels={"segment_value": "Segment", "conversion_rate": "Conversion Rate (%)"},
                text_auto=".1f",
                color="segment_value",
                color_discrete_sequence=px.colors.qualitative.Safe
            )
            fig_segment.update_layout(showlegend=False)
            st.plotly_chart(fig_segment, use_container_width=True)
            
    # Note: Charts currently run off global data via optimized DB queries. 
    # A future improvement could be to pass the `filters` dict to the DB 
    # query functions so the charts respect the sidebar selections too.
    
    st.divider()
    
    # --- EXPLORE USERS SECTION ---
    st.subheader("Explore Users")
    
    if filtered_df.empty:
        st.warning("No users match the selected filters. Please adjust your criteria.")
    else:
        st.write(f"Showing {len(filtered_df):,} of {len(base_df):,} users")
        
        # Select key columns for display
        display_cols = [
            'user_id', 'plan_type', 'company_size', 'days_active', 
            'distinct_features_used', 'core_features_used_first_7_days', 
            'usage_trend', 'converted'
        ]
        
        # Reorder and subset if they exist
        existing_cols = [c for c in display_cols if c in filtered_df.columns]
        display_df = filtered_df[existing_cols].copy()
        
        st.dataframe(display_df, use_container_width=True)
    
except Exception as e:
    st.error("⚠️ Database Not Found or Data Error")
    st.error(
        "Could not load data from `data/trialens.db`. Please ensure you have run the "
        "pipeline scripts (`src/ingest.py`, `src/clean.py`, `src/features.py`) to generate "
        "the database before launching the app."
    )
    st.exception(e)
