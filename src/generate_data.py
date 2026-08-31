import os
import uuid
import numpy as np
import pandas as pd
from faker import Faker
from datetime import timedelta

def generate_synthetic_data():
    print("Initializing synthetic data generation...")
    # Set seeds for reproducibility
    np.random.seed(42)
    Faker.seed(42)
    fake = Faker()

    NUM_USERS = 800
    TRIAL_LENGTH_DAYS = 14
    CORE_FEATURES = ["dashboard", "integrations", "collaboration"]
    OTHER_FEATURES = ["export", "api_access", "reporting", "search", "notifications"]
    ALL_FEATURES = CORE_FEATURES + OTHER_FEATURES

    users = []
    feature_usage = []

    print("Generating users and event schedules...")
    for _ in range(NUM_USERS):
        user_id = str(uuid.uuid4())
        # Generate a random signup date in the last 6 months, minus 14 days so trial is finished
        signup_date = fake.date_time_between(start_date="-6m", end_date="-15d")
        plan_type = np.random.choice(["Starter", "Pro", "Enterprise"], p=[0.5, 0.3, 0.2])
        company_size = np.random.choice(["1-10", "11-50", "51-200", "201+"])
        
        # Decide if this user hits the 3+ core features in first 7 days threshold
        is_high_engagement = np.random.rand() < 0.35  # ~35% of users are "high engagement"
        
        # Conversion probability (noisy signal)
        prob_convert = 0.45 if is_high_engagement else 0.12
        converted = np.random.rand() < prob_convert
        
        conversion_date = None
        if converted:
            # Convert somewhere within the trial length, usually towards the end
            conv_day = np.random.randint(1, TRIAL_LENGTH_DAYS + 1)
            conversion_date = signup_date + timedelta(days=conv_day, hours=np.random.randint(0, 24))
            
        users.append({
            "user_id": user_id,
            "signup_date": signup_date,
            "plan_type": plan_type,
            "company_size": company_size,
            "trial_length_days": TRIAL_LENGTH_DAYS,
            "converted": converted,
            "conversion_date": conversion_date
        })
        
        # Event Generation
        # Converted users tend to have more events.
        target_events = int(np.random.normal(30 if converted else 15, 8))
        target_events = max(5, target_events)
        
        # Distribute events over days (0 to 13)
        num_days = TRIAL_LENGTH_DAYS
        if converted:
            # Sustained/increasing usage
            day_weights = np.linspace(1, 2.5, num_days)
        else:
            # Drop off usage
            day_weights = np.exp(-np.arange(num_days) / 2.5)
            
        day_weights /= day_weights.sum()
        events_per_day = np.random.multinomial(target_events, day_weights)
        
        # Ensure high engagement users have at least 3 events in the first 7 days
        events_in_first_7 = sum(events_per_day[:7])
        if is_high_engagement and events_in_first_7 < 3:
            # Add the missing events to a random day in the first 7 days
            events_per_day[np.random.randint(0, 7)] += (3 - events_in_first_7)
            
        user_events = []
        for day, num_events in enumerate(events_per_day):
            if num_events == 0:
                continue
                
            session_id = str(uuid.uuid4())
            day_start = signup_date + timedelta(days=day)
            session_start = day_start + timedelta(hours=np.random.randint(8, 20))
            
            for e in range(num_events):
                event_timestamp = session_start + timedelta(minutes=e * np.random.randint(2, 15))
                user_events.append({
                    "event_id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "feature_name": None,  # Will assign below based on rules
                    "event_timestamp": event_timestamp,
                    "session_id": session_id
                })
                
        # Now assign features according to the required signal
        first_7_events = [e for e in user_events if (e['event_timestamp'] - signup_date).days < 7]
        other_events = [e for e in user_events if (e['event_timestamp'] - signup_date).days >= 7]
        
        if is_high_engagement:
            # Ensure they hit exactly 3 distinct core features
            core_indices = np.random.choice(len(first_7_events), 3, replace=False)
            for i, idx in enumerate(core_indices):
                first_7_events[idx]['feature_name'] = CORE_FEATURES[i]
                
            for idx, event in enumerate(first_7_events):
                if event['feature_name'] is None:
                    event['feature_name'] = np.random.choice(ALL_FEATURES)
        else:
            # Ensure they DO NOT get 3 distinct core features in first 7 days
            core_used = set()
            for event in first_7_events:
                if len(core_used) == 2:
                    allowed = OTHER_FEATURES + list(core_used)
                    feat = np.random.choice(allowed)
                else:
                    feat = np.random.choice(ALL_FEATURES)
                    if feat in CORE_FEATURES:
                        core_used.add(feat)
                event['feature_name'] = feat
                
        # Assign features randomly for events after first 7 days
        for event in other_events:
            event['feature_name'] = np.random.choice(ALL_FEATURES)
            
        feature_usage.extend(user_events)

    print("Creating DataFrames...")
    df_users = pd.DataFrame(users)
    df_features = pd.DataFrame(feature_usage)

    print("Saving Data to CSVs...")
    os.makedirs('data/raw', exist_ok=True)
    df_users.to_csv('data/raw/users.csv', index=False)
    df_features.to_csv('data/raw/feature_usage.csv', index=False)

    print("\n--- Data Generation Summary ---")
    total_users = len(df_users)
    overall_conversion = df_users['converted'].mean()
    avg_events = len(df_features) / total_users

    # Evaluate the 3+ core feature signal
    df_merged = pd.merge(df_features, df_users[['user_id', 'signup_date', 'converted']], on='user_id')
    df_merged['days_since_signup'] = (df_merged['event_timestamp'] - df_merged['signup_date']).dt.days
    
    first_7 = df_merged[df_merged['days_since_signup'] < 7]
    core_only = first_7[first_7['feature_name'].isin(CORE_FEATURES)]
    
    user_core_counts = core_only.groupby('user_id')['feature_name'].nunique().reset_index(name='distinct_core_first_7')
    df_eval = pd.merge(df_users, user_core_counts, on='user_id', how='left')
    df_eval['distinct_core_first_7'] = df_eval['distinct_core_first_7'].fillna(0)
    df_eval['high_engagement'] = df_eval['distinct_core_first_7'] >= 3

    conv_high = df_eval[df_eval['high_engagement']]['converted'].mean()
    conv_low = df_eval[~df_eval['high_engagement']]['converted'].mean()

    print(f"Total Users: {total_users}")
    print(f"Overall Conversion Rate: {overall_conversion:.1%}")
    print(f"Average Events per User: {avg_events:.1f}")
    print(f"Conversion Rate (High Engagement - 3+ core features in first 7 days): {conv_high:.1%}")
    print(f"Conversion Rate (Low Engagement - <3 core features in first 7 days): {conv_low:.1%}")

if __name__ == "__main__":
    generate_synthetic_data()
