import os
import sqlite3
import pandas as pd
import pytest

from src.clean import run_cleaning

@pytest.fixture
def dirty_db(tmp_path):
    db_path = tmp_path / "dirty_trialens.db"
    conn = sqlite3.connect(db_path)
    
    # Create dirty users
    # u1: valid
    # u2: null user_id -> drop
    # u3: duplicate user_id -> drop second
    # u3: duplicate user_id
    # u4: converted=1 but conversion_date null -> drop
    # u5: converted=0 but conversion_date not null -> drop
    
    users_data = {
        "user_id": ["u1", None, "u3", "u3", "u4", "u5"],
        "signup_date": ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-03", "2023-01-04", "2023-01-05"],
        "plan_type": ["Starter"] * 6,
        "company_size": ["1-10"] * 6,
        "trial_length_days": [14] * 6,
        "converted": [1, 0, 0, 0, 1, 0],
        "conversion_date": ["2023-01-10", None, None, None, None, "2023-01-10"]
    }
    pd.DataFrame(users_data).to_sql("users", conn, index=False)
    
    # Create dirty feature_usage
    # e1: valid (u1)
    # e2: null user_id -> drop
    # e3: duplicate event_id -> drop second
    # e3: duplicate event_id
    # e4: out of window (u1, before signup) -> drop
    # e5: orphaned (u999) -> drop
    
    features_data = {
        "event_id": ["e1", "e2", "e3", "e3", "e4", "e5"],
        "user_id": ["u1", None, "u1", "u1", "u1", "u999"],
        "feature_name": ["dashboard"] * 6,
        "event_timestamp": [
            "2023-01-02", # e1 valid
            "2023-01-02", # e2 null user_id
            "2023-01-03", # e3 duplicate
            "2023-01-03", # e3 duplicate
            "2022-12-01", # e4 out of window (before 2023-01-01)
            "2023-01-02"  # e5 orphaned
        ],
        "session_id": ["s1"] * 6
    }
    pd.DataFrame(features_data).to_sql("feature_usage", conn, index=False)
    
    conn.close()
    return str(db_path)

def test_run_cleaning(dirty_db):
    report = run_cleaning(db_path=dirty_db)
    
    # Assertions on dropping users
    assert report['users_dropped_nulls'] == 1
    assert report['users_dropped_duplicates'] == 1
    assert report['users_dropped_logical_inconsistencies'] == 2
    assert report['final_users_count'] == 2
    
    # Assertions on dropping features
    assert report['features_dropped_nulls'] == 1
    assert report['features_dropped_duplicates'] == 1
    assert report['features_dropped_out_of_window'] == 1
    assert report['features_dropped_orphaned'] == 1
    assert report['final_features_count'] == 2
    
    # Verify tables content
    conn = sqlite3.connect(dirty_db)
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id FROM users_clean")
    final_users = {row[0] for row in cursor.fetchall()}
    assert final_users == {"u1", "u3"}
    
    cursor.execute("SELECT event_id FROM feature_usage_clean")
    final_features = {row[0] for row in cursor.fetchall()}
    assert final_features == {"e1", "e3"}
    
    conn.close()
