import sqlite3
import pandas as pd
import pytest

from src.db import (
    get_connection,
    get_kpi_summary,
    get_conversion_by_core_features,
    get_conversion_by_trend,
    get_conversion_by_segment,
    get_user_features,
    get_engagement_ranking,
    create_views,
    query_conversion_summary_view,
    query_engagement_summary_view
)

@pytest.fixture
def mock_db(tmp_path):
    db_path = tmp_path / "mock_trialens.db"
    conn = sqlite3.connect(db_path)
    
    # create users_clean
    users_data = {
        "user_id": ["u1", "u2", "u3"],
        "signup_date": ["2023-01-01", "2023-01-02", "2023-01-03"],
        "plan_type": ["Starter", "Pro", "Enterprise"],
        "company_size": ["1-10", "11-50", "201+"],
        "trial_length_days": [14, 14, 14],
        "converted": [1, 0, 1],
        "conversion_date": ["2023-01-10", None, "2023-01-05"]
    }
    pd.DataFrame(users_data).to_sql("users_clean", conn, index=False)
    
    # create user_features
    features_data = {
        "user_id": ["u1", "u2", "u3"],
        "converted": [1, 0, 1],
        "plan_type": ["Starter", "Pro", "Enterprise"],
        "company_size": ["1-10", "11-50", "201+"],
        "days_active": [5, 2, 8],
        "distinct_features_used": [4, 1, 6],
        "core_features_used_first_7_days": [3, 1, 4],
        "total_events": [20, 5, 50],
        "time_to_first_core_feature": [1, 3, 0],
        "usage_trend": ["increasing", "decreasing", "flat"],
        "sessions_count": [10, 2, 25]
    }
    pd.DataFrame(features_data).to_sql("user_features", conn, index=False)
    
    conn.close()
    return str(db_path)

def test_get_kpi_summary(mock_db):
    kpis = get_kpi_summary(mock_db)
    assert kpis['total_users'] == 3
    # u1 conv: 10-1 = 9 days. u3 conv: 5-3 = 2 days. Avg: 5.5
    assert kpis['overall_conversion_rate'] == pytest.approx(66.7, 0.1)
    assert kpis['avg_time_to_convert'] == 5.5

def test_get_conversion_by_core_features(mock_db):
    df = get_conversion_by_core_features(mock_db)
    assert len(df) == 2
    high = df[df['feature_group'] == '3+ core features'].iloc[0]
    assert high['user_count'] == 2
    assert high['conversion_rate'] == 100.0

def test_get_conversion_by_trend(mock_db):
    df = get_conversion_by_trend(mock_db)
    assert len(df) == 3
    inc = df[df['usage_trend'] == 'increasing'].iloc[0]
    assert inc['conversion_rate'] == 100.0

def test_get_conversion_by_segment(mock_db):
    df = get_conversion_by_segment("plan_type", mock_db)
    assert len(df) == 3
    
    with pytest.raises(ValueError):
        get_conversion_by_segment("invalid_col", mock_db)

def test_get_user_features(mock_db):
    # No filters
    df1 = get_user_features(db_path=mock_db)
    assert len(df1) == 3
    
    # With filters
    df2 = get_user_features({"plan_type": "Pro"}, db_path=mock_db)
    assert len(df2) == 1
    assert df2.iloc[0]['user_id'] == "u2"
    
    # Invalid filter
    with pytest.raises(ValueError):
        get_user_features({"invalid col": "val"}, db_path=mock_db)

def test_get_engagement_ranking(mock_db):
    df = get_engagement_ranking(mock_db)
    assert len(df) == 3
    # all signed up in 2023-01
    assert df.iloc[0]['signup_month'] == '2023-01'
    # highest total_events is u3 (50)
    assert df.iloc[0]['user_id'] == 'u3'
    assert df.iloc[0]['rank_within_cohort'] == 1
    assert df.iloc[1]['user_id'] == 'u1'
    assert df.iloc[1]['rank_within_cohort'] == 2
    assert df.iloc[2]['user_id'] == 'u2'
    assert df.iloc[2]['rank_within_cohort'] == 3

def test_views_creation_and_querying(mock_db):
    # Create the views
    create_views(mock_db)
    
    # Verify views exist in sqlite_master
    conn = sqlite3.connect(mock_db)
    master_df = pd.read_sql("SELECT name FROM sqlite_master WHERE type='view'", conn)
    conn.close()
    
    views = master_df['name'].tolist()
    assert 'conversion_summary' in views
    assert 'engagement_summary' in views
    
    # Query conversion summary
    conv_df = query_conversion_summary_view(mock_db)
    assert len(conv_df) == 3
    assert 'conversion_rate' in conv_df.columns
    assert 'plan_type' in conv_df.columns
    
    # Query engagement summary
    eng_df = query_engagement_summary_view(mock_db)
    assert len(eng_df) == 2  # converted = 0 and 1
    assert 'avg_days_active' in eng_df.columns
    assert 'converted' in eng_df.columns
