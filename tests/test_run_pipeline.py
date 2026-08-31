import os
import tempfile
import sqlite3
import pandas as pd
import sys
from src.run_pipeline import main


def test_run_pipeline(monkeypatch):
    # Mock sys.argv to simulate running with --force-regenerate
    monkeypatch.setattr(sys, "argv", ["run_pipeline.py", "--force-regenerate"])

    with tempfile.TemporaryDirectory() as temp_dir:
        main(test_data_dir=temp_dir)

        # Verify raw files are created
        raw_dir = os.path.join(temp_dir, "raw")
        assert os.path.exists(os.path.join(raw_dir, "users.csv"))
        assert os.path.exists(os.path.join(raw_dir, "feature_usage.csv"))

        # Verify db is created and has the final tables/views
        db_path = os.path.join(temp_dir, "trialens.db")
        assert os.path.exists(db_path)

        conn = sqlite3.connect(db_path)

        # Verify tables/views exist
        tables = pd.read_sql(
            "SELECT name FROM sqlite_master WHERE type='table' OR type='view'", conn
        )
        table_names = tables["name"].tolist()

        assert "users_clean" in table_names
        assert "feature_usage" in table_names
        assert "user_features" in table_names
        assert "conversion_summary" in table_names
        assert "engagement_summary" in table_names

        conn.close()
