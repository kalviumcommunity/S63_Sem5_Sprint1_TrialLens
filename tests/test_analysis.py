import pandas as pd
from src.analysis import run_analysis


def test_run_analysis_significance():
    data = []

    # 50 converted users, high engagement
    for i in range(50):
        data.append(
            {
                "user_id": f"c_{i}",
                "converted": True,
                "core_features_used_first_7_days": 3 + (i % 2),
                "total_events": 30 + (i % 5),
                "days_active": 10 + (i % 3),
                "distinct_features_used": 6 + (i % 2),
                "time_to_first_core_feature": 1 + (i % 2),
                "sessions_count": 15 + (i % 4),
                "usage_trend": "increasing",
                "plan_type": "Pro",
                "company_size": "11-50",
            }
        )

    # 50 non-converted users, low engagement
    for i in range(50):
        data.append(
            {
                "user_id": f"nc_{i}",
                "converted": False,
                "core_features_used_first_7_days": 1 + (i % 2),
                "total_events": 5 + (i % 3),
                "days_active": 2 + (i % 2),
                "distinct_features_used": 2 + (i % 2),
                "time_to_first_core_feature": 5 + (i % 2),
                "sessions_count": 3 + (i % 2),
                "usage_trend": "decreasing",
                "plan_type": "Starter",
                "company_size": "1-10",
            }
        )

    df = pd.DataFrame(data)
    report = run_analysis(df=df)

    nf = report["numeric_features"]
    assert nf["total_events"]["significant"] is True
    assert (
        nf["total_events"]["converted_mean"] > nf["total_events"]["non_converted_mean"]
    )
    assert nf["total_events"]["p_value"] < 0.05

    hc = report["headline_comparison"]
    assert hc["significant"] is True
    assert (
        hc["high_core_conversion_rate"] > 0.9
    )  # Should be exactly 1.0 based on dummy data
    assert (
        hc["low_core_conversion_rate"] < 0.1
    )  # Should be exactly 0.0 based on dummy data

    seg = report["segments"]
    assert "Pro" in seg["plan_type"]
    assert seg["plan_type"]["Pro"]["high_core_cr"] > 0.9

    # Assertions on distributions
    assert "distributions" in report
    dist = report["distributions"]
    assert "total_events" in dist
    assert "converted" in dist["total_events"]
    assert "not_converted" in dist["total_events"]
    assert "mean" in dist["total_events"]["converted"]
    assert "median" in dist["total_events"]["converted"]

    # Assertions on correlation matrix
    assert "correlation_matrix" in report
    corr = report["correlation_matrix"]
    assert isinstance(corr, pd.DataFrame)

    # Check it's symmetric
    assert (corr.columns == corr.index).all()

    # Check 1.0 on diagonal
    for col in corr.columns:
        assert abs(corr.loc[col, col] - 1.0) < 1e-6


def test_get_funnel():
    import numpy as np
    from src.analysis import get_funnel

    # Construct a dataset for funnel testing
    # We want:
    # 5 total users
    # 4 with > 0 events
    # 3 with time_to_first_core_feature != NaN
    # 2 with 3+ core features
    # 1 who converted

    data = [
        # u1: fully converted (makes it to stage 5)
        {
            "user_id": "u1",
            "total_events": 10,
            "time_to_first_core_feature": 1.0,
            "core_features_used_first_7_days": 3,
            "converted": True,
        },
        # u2: makes it to stage 4 but doesn't convert
        {
            "user_id": "u2",
            "total_events": 10,
            "time_to_first_core_feature": 1.0,
            "core_features_used_first_7_days": 3,
            "converted": False,
        },
        # u3: makes it to stage 3 but only 2 core features
        {
            "user_id": "u3",
            "total_events": 10,
            "time_to_first_core_feature": 1.0,
            "core_features_used_first_7_days": 2,
            "converted": False,
        },
        # u4: makes it to stage 2 but no core feature (NaN)
        {
            "user_id": "u4",
            "total_events": 10,
            "time_to_first_core_feature": np.nan,
            "core_features_used_first_7_days": 0,
            "converted": False,
        },
        # u5: signed up only (0 events)
        {
            "user_id": "u5",
            "total_events": 0,
            "time_to_first_core_feature": np.nan,
            "core_features_used_first_7_days": 0,
            "converted": False,
        },
    ]

    df = pd.DataFrame(data)
    funnel = get_funnel(df=df)

    counts = funnel["user_count"].tolist()
    assert counts == [5, 4, 3, 2, 1]

    # Check pct of previous stage for stage 4 -> stage 5 (1 / 2 = 0.5)
    assert funnel.loc[4, "pct_of_previous_stage"] == 0.5


def test_find_anomalies():
    from src.analysis import find_anomalies

    data = [
        # u1: expected (converted + high usage)
        {"user_id": "u1", "core_features_used_first_7_days": 4, "converted": True},
        # u2: anomaly (not converted + high usage)
        {"user_id": "u2", "core_features_used_first_7_days": 3, "converted": False},
        # u3: anomaly (not converted + high usage)
        {"user_id": "u3", "core_features_used_first_7_days": 5, "converted": False},
        # u4: expected bad (not converted + low usage)
        {"user_id": "u4", "core_features_used_first_7_days": 1, "converted": False},
        # u5: expected good (converted + low usage)
        {"user_id": "u5", "core_features_used_first_7_days": 2, "converted": True},
    ]

    import pandas as pd

    df = pd.DataFrame(data)

    anomalies = find_anomalies(df)

    # Should only find u2 and u3
    assert len(anomalies) == 2
    anomaly_users = anomalies["user_id"].tolist()
    assert "u2" in anomaly_users
    assert "u3" in anomaly_users
    assert "u1" not in anomaly_users
