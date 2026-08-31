import pandas as pd
import pytest
from src.features import compute_daily_activity, compute_rolling_engagement

def test_compute_rolling_engagement():
    # User 1: Increasing activity
    # Day 0: 1, Day 1: 2, Day 2: 3, Day 3: 4
    u1_events = [
        {'user_id': 'u1', 'days_since_signup': 0, 'trial_length_days': 3},
        {'user_id': 'u1', 'days_since_signup': 1, 'trial_length_days': 3},
        {'user_id': 'u1', 'days_since_signup': 1, 'trial_length_days': 3},
        {'user_id': 'u1', 'days_since_signup': 2, 'trial_length_days': 3},
        {'user_id': 'u1', 'days_since_signup': 2, 'trial_length_days': 3},
        {'user_id': 'u1', 'days_since_signup': 2, 'trial_length_days': 3},
        {'user_id': 'u1', 'days_since_signup': 3, 'trial_length_days': 3},
        {'user_id': 'u1', 'days_since_signup': 3, 'trial_length_days': 3},
        {'user_id': 'u1', 'days_since_signup': 3, 'trial_length_days': 3},
        {'user_id': 'u1', 'days_since_signup': 3, 'trial_length_days': 3},
    ]
    
    # User 2: Decreasing activity
    # Day 0: 4, Day 1: 3, Day 2: 2, Day 3: 1
    u2_events = []
    for _ in range(4): u2_events.append({'user_id': 'u2', 'days_since_signup': 0, 'trial_length_days': 3})
    for _ in range(3): u2_events.append({'user_id': 'u2', 'days_since_signup': 1, 'trial_length_days': 3})
    for _ in range(2): u2_events.append({'user_id': 'u2', 'days_since_signup': 2, 'trial_length_days': 3})
    for _ in range(1): u2_events.append({'user_id': 'u2', 'days_since_signup': 3, 'trial_length_days': 3})
    
    df = pd.DataFrame(u1_events + u2_events)
    
    # Compute slopes
    slopes = compute_rolling_engagement(df, window=2)
    
    # Assertions
    assert slopes['u1'] > 0, f"Expected positive slope for u1, got {slopes['u1']}"
    assert slopes['u2'] < 0, f"Expected negative slope for u2, got {slopes['u2']}"
