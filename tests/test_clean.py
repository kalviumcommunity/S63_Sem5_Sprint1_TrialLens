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
        "plan_type": [" starter ", "Starter", "Pro", "Pro", "Enterprise", "Enterprise"],
        "company_size": ["  1-10  ", "1-10", "11-50", "11-50", "201+", "201+"],
        "trial_length_days": [14] * 6,
        "converted": [1, 0, 0, 0, 1, 0],
        "conversion_date": ["2023-01-10", None, None, None, None, "2023-01-10"]
    }
    
    # Add normal users and 1 outlier for IQR testing
    normal_users = [f"u{i}" for i in range(10, 25)]
    outlier_user = "u99"
    for u in normal_users + [outlier_user]:
        users_data["user_id"].append(u)
        users_data["signup_date"].append("2023-01-01")
        users_data["plan_type"].append("Starter")
        users_data["company_size"].append("1-10")
        users_data["trial_length_days"].append(14)
        users_data["converted"].append(0)
        users_data["conversion_date"].append(None)

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
        "feature_name": [" DaShBoArD ", "dashboard", "dashboard", "dashboard", "dashboard", "dashboard"],
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
    
    event_idx = 10
    # 1 event for normal users
    for u in normal_users:
        features_data["event_id"].append(f"e{event_idx}")
        features_data["user_id"].append(u)
        features_data["feature_name"].append("dashboard")
        features_data["event_timestamp"].append("2023-01-02")
        features_data["session_id"].append("s1")
        event_idx += 1
        
    # 50 events for outlier user
    for _ in range(50):
        features_data["event_id"].append(f"e{event_idx}")
        features_data["user_id"].append(outlier_user)
        features_data["feature_name"].append("dashboard")
        features_data["event_timestamp"].append("2023-01-02")
        features_data["session_id"].append("s1")
        event_idx += 1
        
    pd.DataFrame(features_data).to_sql("feature_usage", conn, index=False)
    
    conn.close()
    return str(db_path)

def test_run_cleaning(dirty_db):
    report = run_cleaning(db_path=dirty_db)
    
    # Assertions on dropping users
    assert report['users_dropped_nulls'] == 1
    assert report['users_dropped_duplicates'] == 1
    assert report['users_dropped_logical_inconsistencies'] == 2
    # Base had 2 valid + 15 normal + 1 outlier = 18 final users
    assert report['final_users_count'] == 18
    assert report['users_flagged_outliers'] == 3
    
    # Assertions on dropping features
    assert report['features_dropped_nulls'] == 1
    assert report['features_dropped_duplicates'] == 1
    assert report['features_dropped_out_of_window'] == 1
    assert report['features_dropped_orphaned'] == 1
    assert report['final_features_count'] == 67
    
    # Verify tables content
    conn = sqlite3.connect(dirty_db)
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id FROM users_clean")
    final_users = {row[0] for row in cursor.fetchall()}
    assert "u1" in final_users
    assert "u3" in final_users
    assert "u2" not in final_users
    assert "u4" not in final_users
    
    cursor.execute("SELECT event_id FROM feature_usage_clean")
    final_features = {row[0] for row in cursor.fetchall()}
    assert "e1" in final_features
    assert "e3" in final_features
    assert "e4" not in final_features
    
    # Assertions on string normalization
    cursor.execute("SELECT plan_type, company_size FROM users_clean WHERE user_id = 'u1'")
    u1_row = cursor.fetchone()
    assert u1_row[0] == "Starter"
    assert u1_row[1] == "1-10"
    
    cursor.execute("SELECT feature_name FROM feature_usage_clean WHERE event_id = 'e1'")
    e1_row = cursor.fetchone()
    assert e1_row[0] == "dashboard"
    
    # Assertions on outlier detection
    cursor.execute("SELECT is_outlier_total_event_count FROM users_clean WHERE user_id = 'u99'")
    outlier_row = cursor.fetchone()
    assert outlier_row[0] == 1  # True (SQLite boolean is 1/0)
    
    cursor.execute("SELECT is_outlier_total_event_count FROM users_clean WHERE user_id = 'u10'")
    normal_row = cursor.fetchone()
    assert normal_row[0] == 0  # False
    
    conn.close()
