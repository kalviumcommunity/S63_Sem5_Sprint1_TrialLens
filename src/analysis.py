import sqlite3
import pandas as pd
import numpy as np
from scipy import stats


def get_distributions(df):
    """
    Computes distribution statistics for numeric features split by conversion status.
    """
    numeric_cols = [
        "days_active",
        "distinct_features_used",
        "total_events",
        "sessions_count",
    ]
    dist = {}

    if "converted" not in df.columns:
        return dist

    for col in numeric_cols:
        if col in df.columns:
            dist[col] = {}
            for status in [True, False]:
                status_str = "converted" if status else "not_converted"
                subset = df[df["converted"] == status][col].dropna()
                if len(subset) > 0:
                    dist[col][status_str] = {
                        "mean": float(subset.mean()),
                        "median": float(subset.median()),
                        "std": float(subset.std()),
                        "min": float(subset.min()),
                        "max": float(subset.max()),
                        "q1": float(subset.quantile(0.25)),
                        "q3": float(subset.quantile(0.75)),
                    }
                else:
                    dist[col][status_str] = None
    return dist


def get_correlation_matrix(df):
    """
    Computes Pearson correlation matrix across numeric features + converted status.
    Returns a pandas DataFrame usable for heatmaps.
    """
    numeric_cols = [
        "days_active",
        "distinct_features_used",
        "core_features_used_first_7_days",
        "total_events",
        "time_to_first_core_feature",
        "sessions_count",
        "converted",
    ]

    existing_cols = [c for c in numeric_cols if c in df.columns]
    corr_df = df[existing_cols].copy()
    if "converted" in corr_df.columns:
        corr_df["converted"] = corr_df["converted"].astype(int)

    return corr_df.corr(method="pearson")


def get_funnel(db_path="data/trialens.db", df=None):
    """
    Computes a strict funnel analysis of user drop-off across defined stages.
    """
    if df is None:
        try:
            conn = sqlite3.connect(db_path)
            df = pd.read_sql("SELECT * FROM user_features", conn)
            conn.close()
        except Exception as e:
            print(f"Error loading data for funnel: {e}")
            return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["converted"] = df["converted"].astype(bool)

    s1 = pd.Series(True, index=df.index)
    s2 = s1 & (df.get("total_events", 0) > 0)
    s3 = (
        s2
        & df.get(
            "time_to_first_core_feature", pd.Series(np.nan, index=df.index)
        ).notna()
    )
    s4 = s3 & (df.get("core_features_used_first_7_days", 0) >= 3)
    s5 = s4 & df["converted"]

    stages = [
        {"stage_name": "1_signed_up", "mask": s1},
        {"stage_name": "2_any_event", "mask": s2},
        {"stage_name": "3_core_feature", "mask": s3},
        {"stage_name": "4_high_core_usage", "mask": s4},
        {"stage_name": "5_converted", "mask": s5},
    ]

    results = []
    total_users = len(df)
    prev_count = total_users

    for s in stages:
        count = int(s["mask"].sum())
        pct_total = count / total_users if total_users > 0 else 0.0
        pct_prev = count / prev_count if prev_count > 0 else 0.0

        results.append(
            {
                "stage_name": s["stage_name"],
                "user_count": count,
                "pct_of_previous_stage": pct_prev,
                "pct_of_total": pct_total,
            }
        )

        prev_count = count

    return pd.DataFrame(results)


def find_anomalies(df):
    """Identify users with high engagement but no conversion."""
    if df is None or df.empty:
        return pd.DataFrame()
    return df[
        (df.get("core_features_used_first_7_days", 0) >= 3)
        & (~df.get("converted", False))
    ]


def investigate_anomalies(anomalies_df, full_df):
    """Compare anomalies against expected users across key features."""
    if anomalies_df.empty or full_df is None or full_df.empty:
        return {}

    expected_df = full_df[
        (full_df.get("core_features_used_first_7_days", 0) >= 3)
        & (full_df.get("converted", False))
    ]

    if expected_df.empty:
        return {}

    comparison = {}

    cat_cols = ["plan_type", "company_size", "usage_trend"]
    for col in cat_cols:
        if col in full_df.columns:
            anom_pct = anomalies_df[col].value_counts(normalize=True).to_dict()
            exp_pct = expected_df[col].value_counts(normalize=True).to_dict()
            comparison[col] = {"anomalies": anom_pct, "expected": exp_pct}

    num_cols = ["time_to_first_core_feature", "sessions_count"]
    for col in num_cols:
        if col in full_df.columns:
            comparison[col] = {
                "anomalies_mean": float(anomalies_df[col].mean()),
                "expected_mean": float(expected_df[col].mean()),
            }

    return comparison


def run_analysis(db_path="data/trialens.db", df=None):
    """
    Run statistical analysis on user features to find predictors of conversion.
    If df is provided, skips database loading (useful for testing).
    """
    if df is None:
        try:
            conn = sqlite3.connect(db_path)
            df = pd.read_sql("SELECT * FROM user_features", conn)
            conn.close()
        except Exception as e:
            print(f"Error loading data from {db_path}: {e}")
            return {}

    # Ensure converted is boolean
    df["converted"] = df["converted"].astype(bool)

    report = {
        "total_users": len(df),
        "overall_conversion_rate": df["converted"].mean(),
        "numeric_features": {},
        "headline_comparison": {},
        "usage_trend": {},
        "segments": {"plan_type": {}, "company_size": {}},
    }

    conv_df = df[df["converted"] == True]
    non_conv_df = df[df["converted"] == False]

    numeric_cols = [
        "days_active",
        "distinct_features_used",
        "core_features_used_first_7_days",
        "total_events",
        "time_to_first_core_feature",
        "sessions_count",
    ]

    # 1. Numeric Features Analysis
    for col in numeric_cols:
        if col not in df.columns:
            continue

        c_vals = conv_df[col].dropna()
        nc_vals = non_conv_df[col].dropna()

        if len(c_vals) > 1 and len(nc_vals) > 1:
            t_stat, p_val = stats.ttest_ind(c_vals, nc_vals, equal_var=False)
            significant = bool(p_val < 0.05) if not pd.isna(p_val) else False
        else:
            t_stat, p_val, significant = None, None, False

        report["numeric_features"][col] = {
            "converted_mean": c_vals.mean() if len(c_vals) > 0 else None,
            "converted_median": c_vals.median() if len(c_vals) > 0 else None,
            "non_converted_mean": nc_vals.mean() if len(nc_vals) > 0 else None,
            "non_converted_median": nc_vals.median() if len(nc_vals) > 0 else None,
            "p_value": p_val,
            "significant": significant,
        }

    # 2. Headline Comparison
    df["high_core"] = df["core_features_used_first_7_days"] >= 3

    contingency_table = pd.crosstab(df["high_core"], df["converted"])

    if contingency_table.shape == (2, 2):
        chi2, p_val_chi, dof, ex = stats.chi2_contingency(contingency_table)
    else:
        p_val_chi = None

    high_group = df[df["high_core"]]
    low_group = df[~df["high_core"]]

    report["headline_comparison"] = {
        "high_core_conversion_rate": (
            high_group["converted"].mean() if len(high_group) > 0 else 0
        ),
        "low_core_conversion_rate": (
            low_group["converted"].mean() if len(low_group) > 0 else 0
        ),
        "p_value": p_val_chi,
        "significant": bool(p_val_chi < 0.05) if p_val_chi is not None else False,
    }

    # 3. Usage Trend
    if "usage_trend" in df.columns:
        trend_rates = df.groupby("usage_trend")["converted"].mean().to_dict()
        report["usage_trend"] = trend_rates

    # 4. Segmentation
    for segment_col in ["plan_type", "company_size"]:
        if segment_col in df.columns:
            # Refactored from Python loop to vectorized groupby for better performance.
            # Using pandas aggregations directly avoids slicing the DataFrame repeatedly in a python loop.
            seg_counts = df.groupby(segment_col).size()
            seg_high_cr = df[df["high_core"]].groupby(segment_col)["converted"].mean()
            seg_low_cr = df[~df["high_core"]].groupby(segment_col)["converted"].mean()

            for seg_val in df[segment_col].dropna().unique():
                report["segments"][segment_col][seg_val] = {
                    "high_core_cr": float(seg_high_cr.get(seg_val, 0.0)),
                    "low_core_cr": float(seg_low_cr.get(seg_val, 0.0)),
                    "count": int(seg_counts.get(seg_val, 0)),
                }

    # 5. Distributions & Correlations & Funnel
    report["distributions"] = get_distributions(df)
    report["correlation_matrix"] = get_correlation_matrix(df)
    report["funnel"] = get_funnel(df=df)

    # 6. Anomaly Detection
    anomalies_df = find_anomalies(df)
    report["anomalies_count"] = len(anomalies_df)
    report["anomalies_investigation"] = investigate_anomalies(anomalies_df, df)

    return report


if __name__ == "__main__":
    report = run_analysis()

    print("\n" + "=" * 70)
    print("                      TRIAL LENS ANALYSIS REPORT")
    print("=" * 70)
    print(f"Total Users Analyzed: {report.get('total_users', 0)}")
    print(f"Overall Conversion Rate: {report.get('overall_conversion_rate', 0):.1%}\n")

    print("--- HEADLINE COMPARISON: 3+ Core Features in Week 1 ---")
    hc = report.get("headline_comparison", {})
    print(f"Conversion (>= 3 Core): {hc.get('high_core_conversion_rate', 0):.1%}")
    print(f"Conversion (< 3 Core):  {hc.get('low_core_conversion_rate', 0):.1%}")
    if hc.get("p_value") is not None:
        print(f"Chi-square p-value:     {hc.get('p_value'):.4e}")
        print(f"Statistically Sig.?     {'Yes' if hc.get('significant') else 'No'}\n")

    print("--- ANOMALY INVESTIGATION ---")
    anom_cnt = report.get("anomalies_count", 0)
    investigation = report.get("anomalies_investigation", {})
    print(f"{anom_cnt} users showed strong engagement but did not convert.")

    if investigation and "plan_type" in investigation:
        plan_anom = investigation["plan_type"].get("anomalies", {})
        plan_exp = investigation["plan_type"].get("expected", {})
        starter_anom = plan_anom.get("Starter", 0.0)
        starter_exp = plan_exp.get("Starter", 0.0)
        print(
            f"{starter_anom:.1%} of them were on the Starter plan vs {starter_exp:.1%} in the expected (converted) group.\n"
        )

    print("--- NUMERIC FEATURES T-TESTS (Converted vs Not) ---")
    for feat, stats_dict in report.get("numeric_features", {}).items():
        sig_str = "*** SIGNIFICANT ***" if stats_dict.get("significant") else "Not sig."
        c_mean = stats_dict.get("converted_mean")
        nc_mean = stats_dict.get("non_converted_mean")
        pval = stats_dict.get("p_value")

        c_m_str = f"{c_mean:.2f}" if c_mean is not None else "N/A"
        nc_m_str = f"{nc_mean:.2f}" if nc_mean is not None else "N/A"
        p_str = f"{pval:.4e}" if pval is not None else "N/A"

        print(
            f"{feat:32s} | Conv: {c_m_str:>6s} | Non: {nc_m_str:>6s} | p: {p_str:>9s} | {sig_str}"
        )

    print("\n--- USAGE TREND CONVERSION RATES ---")
    for trend, rate in report.get("usage_trend", {}).items():
        print(f"  {trend:15s}: {rate:.1%}")

    print("\n--- SEGMENTATION (High Core vs Low Core CR) ---")
    for seg_col, segments in report.get("segments", {}).items():
        print(f"\n[{seg_col.upper()}]")
        for val, metrics in segments.items():
            print(
                f"  {val:15s} | >=3 Core: {metrics['high_core_cr']:6.1%} | <3 Core: {metrics['low_core_cr']:6.1%} | (N={metrics['count']})"
            )
    print("=" * 70 + "\n")
