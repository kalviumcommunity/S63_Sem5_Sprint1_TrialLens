import os
import sqlite3
import pandas as pd
import pytest

from src.ingest import run_ingestion

@pytest.fixture
def mock_data(tmp_path):
    """Create tiny mock CSVs for testing ingestion."""
    users_csv = tmp_path / "test_users.csv"
    features_csv = tmp_path / "test_features.csv"
    db_path = tmp_path / "test_trialens.db"
    
    users_data = {
        "user_id": ["u1", "u2"],
        "signup_date": ["2023-01-01", "2023-01-02"],
        "plan_type": ["Starter", "Pro"],
        "company_size": ["1-10", "11-50"],
        "trial_length_days": [14, 14],
        "converted": [True, False],
        "conversion_date": ["2023-01-10", None]
    }
    pd.DataFrame(users_data).to_csv(users_csv, index=False)
    
    features_data = {
        "event_id": ["e1", "e2", "e3"],
        "user_id": ["u1", "u1", "u2"],
        "feature_name": ["dashboard", "export", "search"],
        "event_timestamp": ["2023-01-02T10:00:00", "2023-01-03T11:00:00", "2023-01-03T09:00:00"],
        "session_id": ["s1", "s2", "s3"]
    }
    pd.DataFrame(features_data).to_csv(features_csv, index=False)
    
    return {
        "db_path": str(db_path),
        "users_csv": str(users_csv),
        "features_csv": str(features_csv),
        "expected_users_count": 2,
        "expected_features_count": 3
    }

def test_run_ingestion(mock_data):
    """Test the ingestion script creates tables and loads data correctly."""
    
    # Run ingestion against temp paths
    run_ingestion(
        db_path=mock_data["db_path"],
        users_csv=mock_data["users_csv"],
        feature_usage_csv=mock_data["features_csv"]
    )
    
    # Assert DB was created
    assert os.path.exists(mock_data["db_path"])
    
    # Connect and verify
    conn = sqlite3.connect(mock_data["db_path"])
    cursor = conn.cursor()
    
    # 1. Assert tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "users" in tables
    assert "feature_usage" in tables
    
    # 2. Assert expected columns in 'users'
    cursor.execute("PRAGMA table_info(users)")
    user_cols = {row[1] for row in cursor.fetchall()}
    expected_user_cols = {"user_id", "signup_date", "plan_type", "company_size", "trial_length_days", "converted", "conversion_date"}
    assert user_cols == expected_user_cols
    
    # 3. Assert expected columns in 'feature_usage'
    cursor.execute("PRAGMA table_info(feature_usage)")
    feature_cols = {row[1] for row in cursor.fetchall()}
    expected_feature_cols = {"event_id", "user_id", "feature_name", "event_timestamp", "session_id"}
    assert feature_cols == expected_feature_cols
    
    # 4. Assert row counts match
    cursor.execute("SELECT COUNT(*) FROM users")
    assert cursor.fetchone()[0] == mock_data["expected_users_count"]
    
    cursor.execute("SELECT COUNT(*) FROM feature_usage")
    assert cursor.fetchone()[0] == mock_data["expected_features_count"]
    
    # 5. Assert no orphaned feature_usage rows
    cursor.execute("""
        SELECT COUNT(*) FROM feature_usage 
        WHERE user_id NOT IN (SELECT user_id FROM users)
    """)
    assert cursor.fetchone()[0] == 0
    
    conn.close()
