import sqlite3
import pandas as pd
import pytest
import src.profile_data


@pytest.fixture
def dummy_raw_db(tmp_path):
    db_path = tmp_path / "raw_trialens.db"
    conn = sqlite3.connect(db_path)

    users_data = {
        "user_id": ["u1", "u2", "u3", None],
        "signup_date": ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"],
        "plan_type": ["Starter", "Starter", "Pro", "Enterprise"],
        "company_size": ["1-10", "11-50", "1-10", "201+"],
        "trial_length_days": [14, 14, 14, 14],
        "converted": [1, 0, 1, 0],
        "conversion_date": ["2023-01-10", None, "2023-01-05", None],
    }
    pd.DataFrame(users_data).to_sql("users", conn, index=False)

    features_data = {
        "event_id": ["e1", "e2", "e3", "e4", "e5"],
        "user_id": ["u1", "u1", "u2", "u3", "u999"],
        "feature_name": ["dashboard", "dashboard", "export", "dashboard", "api"],
        "event_timestamp": [
            "2023-01-02",
            "2023-01-02",
            "2023-01-03",
            "2023-01-03",
            "2023-01-04",
        ],
        "session_id": ["s1", "s1", "s2", "s3", "s4"],
    }
    pd.DataFrame(features_data).to_sql("feature_usage", conn, index=False)

    conn.close()
    return str(db_path)


def test_run_profiling(dummy_raw_db, tmp_path):
    # Patch the output directory for the data dictionary so we don't litter the actual docs folder during tests
    original_generate = src.profile_data.generate_data_dictionary
    src.profile_data.generate_data_dictionary = lambda: original_generate(
        docs_dir=str(tmp_path / "docs")
    )

    try:
        report = src.profile_data.run_profiling(db_path=dummy_raw_db)
    finally:
        src.profile_data.generate_data_dictionary = original_generate

    assert "users" in report
    assert "feature_usage" in report

    users = report["users"]
    assert users["row_count"] == 4

    # user_id has 1 null out of 4 -> 25%
    assert users["columns"]["user_id"]["null_pct"] == 25.0

    # plan_type unique counts (Starter, Pro, Enterprise) -> 3
    assert users["columns"]["plan_type"]["unique_values"] == 3

    # plan_type top 5 should have 'Starter' at count 2
    assert users["columns"]["plan_type"]["top_5"]["Starter"] == 2

    # check numeric
    assert users["columns"]["trial_length_days"]["mean"] == 14.0

    features = report["feature_usage"]
    assert features["row_count"] == 5
    assert features["columns"]["feature_name"]["unique_values"] == 3
    assert features["columns"]["feature_name"]["top_5"]["dashboard"] == 3
