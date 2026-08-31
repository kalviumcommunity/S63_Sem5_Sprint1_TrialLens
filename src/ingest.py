import os
import sqlite3
import pandas as pd

def run_ingestion(db_path="data/trialens.db", users_csv="data/raw/users.csv", feature_usage_csv="data/raw/feature_usage.csv"):
    """
    Load synthetic trial data from CSVs into a SQLite database.
    This operation is idempotent (it drops and recreates the tables).
    """
    print(f"Starting data ingestion to {db_path}...")
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Connect to SQLite
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Drop existing tables if they exist to ensure idempotency
    cursor.execute("DROP TABLE IF EXISTS feature_usage")
    cursor.execute("DROP TABLE IF EXISTS users")
    
    # 2. Create tables with explicit schema
    create_users_query = """
    CREATE TABLE users (
        user_id TEXT PRIMARY KEY,
        signup_date TEXT NOT NULL,
        plan_type TEXT,
        company_size TEXT,
        trial_length_days INTEGER,
        converted BOOLEAN,
        conversion_date TEXT
    )
    """
    cursor.execute(create_users_query)
    
    create_feature_usage_query = """
    CREATE TABLE feature_usage (
        event_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        feature_name TEXT,
        event_timestamp TEXT NOT NULL,
        session_id TEXT,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """
    cursor.execute(create_feature_usage_query)
    
    # 3. Create indexes
    cursor.execute("CREATE INDEX idx_feature_usage_user_id ON feature_usage(user_id)")
    cursor.execute("CREATE INDEX idx_feature_usage_event_timestamp ON feature_usage(event_timestamp)")
    
    conn.commit()
    
    # 4. Load CSVs with pandas and insert into tables
    if not os.path.exists(users_csv) or not os.path.exists(feature_usage_csv):
        print(f"Error: CSV files not found. Ensure {users_csv} and {feature_usage_csv} exist.")
        conn.close()
        return
        
    print(f"Loading {users_csv}...")
    df_users = pd.read_csv(users_csv)
    df_users.to_sql("users", conn, if_exists="append", index=False)
    
    print(f"Loading {feature_usage_csv}...")
    df_features = pd.read_csv(feature_usage_csv)
    df_features.to_sql("feature_usage", conn, if_exists="append", index=False)
    
    # 5. Run verification checks
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM feature_usage")
    features_count = cursor.fetchone()[0]
    
    # Check for orphaned rows (user_id in feature_usage that doesn't exist in users)
    cursor.execute("""
        SELECT COUNT(*) 
        FROM feature_usage 
        WHERE user_id NOT IN (SELECT user_id FROM users)
    """)
    orphaned_count = cursor.fetchone()[0]
    
    print("\n--- Ingestion Summary ---")
    print(f"Rows loaded into 'users': {users_count}")
    print(f"Rows loaded into 'feature_usage': {features_count}")
    print(f"Orphaned feature_usage rows (referential integrity check): {orphaned_count}")
    
    if orphaned_count > 0:
        print("WARNING: Found orphaned rows in feature_usage! Referential integrity violated.")
    else:
        print("Referential integrity intact.")
        
    conn.close()
    print("Ingestion complete.")

if __name__ == "__main__":
    run_ingestion()
