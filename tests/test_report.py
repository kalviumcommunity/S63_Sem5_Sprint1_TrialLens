import pandas as pd
from src.report import generate_report_text


def test_generate_report_text():
    kpi_summary = {
        "total_users": 1000,
        "overall_conversion_rate": 25.5,
        "avg_time_to_convert": 4.2,
    }

    analysis_report = {
        "headline_comparison": {
            "high_core_conversion_rate": 0.5,
            "low_core_conversion_rate": 0.1,
            "p_value": 0.0001,
            "significant": True,
        },
        "funnel": pd.DataFrame(
            [
                {"stage_name": "1_signed_up", "user_count": 1000, "pct_of_total": 1.0},
                {"stage_name": "2_any_event", "user_count": 900, "pct_of_total": 0.9},
            ]
        ),
        "segments": {
            "plan_type": {
                "Starter": {"high_core_cr": 0.4, "low_core_cr": 0.05, "count": 500}
            }
        },
    }

    text = generate_report_text(analysis_report, kpi_summary)

    assert len(text) > 0
    assert "TrialLens Summary Report" in text
    assert "1,000" in text
    assert "25.5%" in text
    assert "4.2 days" in text
    assert "50.0%" in text
    assert "10.0%" in text
    assert "statistically significant" in text
    assert "1 Signed Up" in text
    assert "900 users (90.0%)" in text
    assert "Starter" in text
    assert "40.0%" in text
