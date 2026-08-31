import sqlite3
import pandas as pd
import numpy as np

def compute_daily_activity(feature_usage_df, user_id):
    """
    Returns a per-day event count series for a specific user across their trial window.
    """
    user_events = feature_usage_df[feature_usage_df['user_id'] == user_id]
    if user_events.empty:
        return pd.Series(dtype=float)
        
    daily = user_events.groupby('days_since_signup').size()
    
    trial_length = user_events['trial_length_days'].iloc[0] if 'trial_length_days' in user_events.columns else 14
    max_day = int(max(trial_length, daily.index.max() if not daily.empty else 0))
    full_index = pd.RangeIndex(0, max_day + 1)
    
    return daily.reindex(full_index, fill_value=0)

def compute_rolling_engagement(df, window=3):
    """
    Computes a rolling average of daily event counts per user and derives a linear trend slope.
    """
    slopes = {}
    users = df['user_id'].unique()
    
    for uid in users:
        daily = compute_daily_activity(df, uid)
        if len(daily) < window:
            slopes[uid] = 0.0
            continue
            
        rolling_avg = daily.rolling(window=window, min_periods=1).mean()
        
        x = np.arange(len(rolling_avg))
        y = rolling_avg.values
        
        if len(x) > 1:
            slope, _ = np.polyfit(x, y, 1)
            slopes[uid] = float(slope)
        else:
            slopes[uid] = 0.0
            
    return pd.Series(slopes, name='rolling_trend_slope')


def build_features(db_path="data/trialens.db"):
    print(f"Building features from {db_path}...")
    conn = sqlite3.connect(db_path)
    
    # 1. Load cleaned data
    users = pd.read_sql("SELECT * FROM users_clean", conn)
    features = pd.read_sql("SELECT * FROM feature_usage_clean", conn)
    
    # Pre-process dates
    users['signup_date_dt'] = pd.to_datetime(users['signup_date'])
    features['event_timestamp_dt'] = pd.to_datetime(features['event_timestamp'])
    
    # Merge to compute relative times
    df = features.merge(users[['user_id', 'signup_date_dt', 'trial_length_days']], on='user_id', how='left')
    
    df['days_since_signup'] = (df['event_timestamp_dt'] - df['signup_date_dt']).dt.days
    df['calendar_day'] = df['event_timestamp_dt'].dt.date
    
    CORE_FEATURES = ["dashboard", "integrations", "collaboration"]
    df['is_core'] = df['feature_name'].isin(CORE_FEATURES)
    df['is_first_7_days'] = df['days_since_signup'] < 7
    
    # Compute per-user aggregations
    g = df.groupby('user_id')
    
    # days_active
    days_active = g['calendar_day'].nunique().rename('days_active')
    
    # distinct_features_used
    distinct_features_used = g['feature_name'].nunique().rename('distinct_features_used')
    
    # core_features_used_first_7_days
    core_first_7 = df[df['is_core'] & df['is_first_7_days']].groupby('user_id')['feature_name'].nunique().rename('core_features_used_first_7_days')
    
    # total_events
    total_events = g.size().rename('total_events')
    
    # time_to_first_core_feature
    core_only = df[df['is_core']]
    first_core_days = core_only.groupby('user_id')['days_since_signup'].min().rename('time_to_first_core_feature')
    
    # usage_trend
    # first half vs second half
    df['half_cutoff'] = df['trial_length_days'] / 2.0
    df['is_first_half'] = df['days_since_signup'] < df['half_cutoff']
    
    first_half_events = df[df['is_first_half']].groupby('user_id').size()
    second_half_events = df[~df['is_first_half']].groupby('user_id').size()
    
    # align them for trend computation to include users with zero events
    trend_df = pd.DataFrame(index=users['user_id'].unique())
    trend_df['first_half'] = first_half_events
    trend_df['second_half'] = second_half_events
    trend_df = trend_df.fillna(0)
    
    conditions = [
        trend_df['second_half'] > trend_df['first_half'],
        trend_df['second_half'] < trend_df['first_half']
    ]
    choices = ["increasing", "decreasing"]
    usage_trend = pd.Series(np.select(conditions, choices, default="flat"), index=trend_df.index, name='usage_trend')
    
    # sessions_count
    sessions_count = g['session_id'].nunique().rename('sessions_count')
    
    # rolling_trend_slope
    rolling_trend_slope = compute_rolling_engagement(df, window=3)
    
    # Combine features
    user_features = pd.DataFrame(index=users['user_id'].unique())
    
    for s in [days_active, distinct_features_used, core_first_7, total_events, first_core_days, usage_trend, rolling_trend_slope, sessions_count]:
        user_features = user_features.join(s, how='left')
        
    # Fill NAs for counts (users with zero events or zero specific events)
    count_cols = ['days_active', 'distinct_features_used', 'core_features_used_first_7_days', 'total_events', 'sessions_count']
    user_features[count_cols] = user_features[count_cols].fillna(0).astype(int)
    user_features['usage_trend'] = user_features['usage_trend'].fillna('flat')
    user_features['rolling_trend_slope'] = user_features['rolling_trend_slope'].fillna(0.0)
    
    # Join with users_clean
    user_features = user_features.reset_index().rename(columns={'index': 'user_id'})
    
    final_df = users[['user_id', 'converted', 'plan_type', 'company_size']].merge(user_features, on='user_id', how='left')
    
    # Write to SQLite
    final_df.to_sql('user_features', conn, if_exists='replace', index=False)
    
    conn.close()
    print("Features engineered and saved to 'user_features' table.")
    
    return final_df

if __name__ == "__main__":
    df = build_features()
    
    # Ensure converted is boolean (could be 1/0 from SQLite)
    df['converted'] = df['converted'].astype(bool)
    
    total_users = len(df)
    avg_distinct_features = df['distinct_features_used'].mean()
    
    # Conversion rates split by core_features_used_first_7_days >= 3
    df['high_core_usage'] = df['core_features_used_first_7_days'] >= 3
    
    # Handle cases where denominator might be 0, though unlikely with 800 users
    high_core_users = df[df['high_core_usage']]
    low_core_users = df[~df['high_core_usage']]
    
    conv_high = high_core_users['converted'].mean() if len(high_core_users) > 0 else 0
    conv_low = low_core_users['converted'].mean() if len(low_core_users) > 0 else 0
    
    print("\n=== FEATURE ENGINEERING SUMMARY ===")
    print(f"Total Users: {total_users}")
    print(f"Average Distinct Features Used: {avg_distinct_features:.2f}")
    print(f"Conversion Rate (Core Features >= 3 in first 7 days): {conv_high:.1%}")
    print(f"Conversion Rate (Core Features < 3 in first 7 days): {conv_low:.1%}")
