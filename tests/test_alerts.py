import pandas as pd
from src.alerts import get_at_risk_users


def test_get_at_risk_users():
    data = {
        "user_id": ["u1", "u2", "u3", "u4"],
        "converted": [False, False, True, False],
        "usage_trend": ["decreasing", "increasing", "decreasing", "decreasing"],
        "total_events": [5, 5, 2, 20],
    }
    df = pd.DataFrame(data)

    # Expected at-risk users:
    # u1: converted=False, trend=decreasing, total_events=5 (<= 10) -> YES
    # u2: converted=False, trend=increasing -> NO
    # u3: converted=True -> NO
    # u4: converted=False, trend=decreasing, total_events=20 (> 10) -> NO

    at_risk_df = get_at_risk_users(df, max_events=10)

    assert len(at_risk_df) == 1
    assert at_risk_df.iloc[0]["user_id"] == "u1"


def test_get_at_risk_users_missing_cols():
    data = {"user_id": ["u1"], "converted": [False]}
    df = pd.DataFrame(data)
    at_risk_df = get_at_risk_users(df)
    assert at_risk_df.empty
