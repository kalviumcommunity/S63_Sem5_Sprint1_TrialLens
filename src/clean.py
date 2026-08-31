import pandas as pd
import sqlite3
import pprint

def run_cleaning(db_path="data/trialens.db"):
    print(f"Starting data cleaning on {db_path}...")
    
    conn = sqlite3.connect(db_path)
    
    try:
        df_users = pd.read_sql("SELECT * FROM users", conn)
        df_features = pd.read_sql("SELECT * FROM feature_usage", conn)
    except Exception as e:
        print(f"Error loading data: {e}")
        return {}
        
    report = {}
    
    # 1. Nulls in required fields
    initial_users = len(df_users)
    df_users = df_users.dropna(subset=['user_id', 'signup_date'])
    dropped_users_nulls = initial_users - len(df_users)
    report['users_dropped_nulls'] = dropped_users_nulls
    print(f"Checked users for null user_id/signup_date: Dropped {dropped_users_nulls} rows.")

    initial_features = len(df_features)
    df_features = df_features.dropna(subset=['user_id', 'event_timestamp'])
    dropped_features_nulls = initial_features - len(df_features)
    report['features_dropped_nulls'] = dropped_features_nulls
    print(f"Checked feature_usage for null user_id/event_timestamp: Dropped {dropped_features_nulls} rows.")
    
    # 2. Duplicate event_id
    initial_features = len(df_features)
    df_features = df_features.drop_duplicates(subset=['event_id'], keep='first')
    dropped_feature_dupes = initial_features - len(df_features)
    report['features_dropped_duplicates'] = dropped_feature_dupes
    print(f"Checked feature_usage for duplicate event_id: Dropped {dropped_feature_dupes} rows.")
    
    # 3. Duplicate user_id
    initial_users = len(df_users)
    df_users = df_users.drop_duplicates(subset=['user_id'], keep='first')
    dropped_user_dupes = initial_users - len(df_users)
    report['users_dropped_duplicates'] = dropped_user_dupes
    print(f"Checked users for duplicate user_id: Dropped {dropped_user_dupes} rows.")
    
    # 4. Logical inconsistencies
    initial_users = len(df_users)
    
    # Ensure converted is boolean (SQLite stores as 1/0)
    df_users['converted'] = df_users['converted'].astype(bool)
    
    invalid_conv_1 = df_users['converted'] & df_users['conversion_date'].isna()
    invalid_conv_2 = (~df_users['converted']) & df_users['conversion_date'].notna()
    invalid_users_mask = invalid_conv_1 | invalid_conv_2
    
    df_users = df_users[~invalid_users_mask]
    dropped_invalid_users = initial_users - len(df_users)
    report['users_dropped_logical_inconsistencies'] = dropped_invalid_users
    print(f"Checked users for logical inconsistencies (converted vs conversion_date): Dropped {dropped_invalid_users} rows.")
    
    # 5. Out of window feature_usage
    initial_features = len(df_features)
    df_users['signup_date_dt'] = pd.to_datetime(df_users['signup_date'], errors='coerce')
    df_features['event_timestamp_dt'] = pd.to_datetime(df_features['event_timestamp'], errors='coerce')
    
    # Left merge to preserve features for the orphaned check later
    merged = df_features.merge(df_users[['user_id', 'signup_date_dt', 'trial_length_days']], on='user_id', how='left')
    
    trial_lengths = pd.to_numeric(merged['trial_length_days'], errors='coerce').fillna(14)
    trial_end = merged['signup_date_dt'] + pd.to_timedelta(trial_lengths, unit='D')
    
    out_of_window = (merged['signup_date_dt'].notna()) & (
        (merged['event_timestamp_dt'] < merged['signup_date_dt']) | 
        (merged['event_timestamp_dt'] > trial_end)
    )
    
    df_features = df_features[~out_of_window.values]
    dropped_out_of_window = initial_features - len(df_features)
    report['features_dropped_out_of_window'] = dropped_out_of_window
    print(f"Checked feature_usage for out-of-window events: Dropped {dropped_out_of_window} rows.")
    
    # 6. Orphaned feature_usage rows
    initial_features = len(df_features)
    valid_users = set(df_users['user_id'])
    df_features = df_features[df_features['user_id'].isin(valid_users)]
    dropped_orphans = initial_features - len(df_features)
    report['features_dropped_orphaned'] = dropped_orphans
    print(f"Checked feature_usage for orphaned rows: Dropped {dropped_orphans} rows.")
    
    # Clean up temp columns
    df_users = df_users.drop(columns=['signup_date_dt'])
    df_features = df_features.drop(columns=['event_timestamp_dt'])
    
    # Write to SQLite
    df_users.to_sql('users_clean', conn, if_exists='replace', index=False)
    df_features.to_sql('feature_usage_clean', conn, if_exists='replace', index=False)
    
    conn.close()
    
    report['final_users_count'] = len(df_users)
    report['final_features_count'] = len(df_features)
    print(f"Data cleaning complete. Final users: {len(df_users)}, Final feature_usage: {len(df_features)}.")
    
    return report

if __name__ == "__main__":
    report = run_cleaning()
    print("\n=== CLEANING REPORT ===")
    pprint.pprint(report)
