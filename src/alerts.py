import pandas as pd


def get_at_risk_users(df: pd.DataFrame, max_events: int = 10) -> pd.DataFrame:
    """
    Identifies at-risk users who are likely to churn.
    Since the dataset is historical, we define at-risk as users who:
    - Have not converted
    - Have a 'decreasing' usage trend
    - Have critically low overall engagement (<= max_events)
    """
    if df.empty:
        return pd.DataFrame()

    required_cols = ["converted", "usage_trend", "total_events"]
    if not all(col in df.columns for col in required_cols):
        return pd.DataFrame()

    at_risk_mask = (
        (df["converted"] == False)
        & (df["usage_trend"] == "decreasing")
        & (df["total_events"] <= max_events)
    )

    return df[at_risk_mask].copy()
