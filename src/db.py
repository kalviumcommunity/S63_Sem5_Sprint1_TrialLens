import sqlite3
import pandas as pd
from typing import Dict, Any, Optional

DEFAULT_DB_PATH = "data/trialens.db"

from contextlib import contextmanager


@contextmanager
def get_connection(db_path: str = DEFAULT_DB_PATH):
    """Returns a connection to the SQLite database via a context manager."""
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def get_kpi_summary(db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    """Returns a dict with total_users, overall_conversion_rate, avg_time_to_convert."""
    query = """
        SELECT 
            COUNT(uf.user_id) as total_users,
            AVG(CAST(uf.converted AS FLOAT)) * 100.0 as overall_conversion_rate,
            AVG(julianday(uc.conversion_date) - julianday(uc.signup_date)) as avg_time_to_convert
        FROM user_features uf
        JOIN users_clean uc ON uf.user_id = uc.user_id
    """
    with get_connection(db_path) as conn:
        df = pd.read_sql(query, conn)

    if df.empty or pd.isna(df.iloc[0]["total_users"]) or df.iloc[0]["total_users"] == 0:
        return {
            "total_users": 0,
            "overall_conversion_rate": 0.0,
            "avg_time_to_convert": 0.0,
        }

    return {
        "total_users": int(df.iloc[0]["total_users"]),
        "overall_conversion_rate": round(
            float(df.iloc[0]["overall_conversion_rate"] or 0), 1
        ),
        "avg_time_to_convert": round(float(df.iloc[0]["avg_time_to_convert"] or 0), 1),
    }


def get_conversion_by_core_features(db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """
    Returns DataFrame: group ("3+ core features" / "<3 core features"), conversion_rate, user_count.
    """
    query = """
        SELECT 
            CASE 
                WHEN core_features_used_first_7_days >= 3 THEN '3+ core features'
                ELSE '<3 core features'
            END as feature_group,
            AVG(CAST(converted AS FLOAT)) * 100.0 as conversion_rate,
            COUNT(*) as user_count
        FROM user_features
        GROUP BY feature_group
        ORDER BY feature_group
    """
    with get_connection(db_path) as conn:
        df = pd.read_sql(query, conn)
    return df


def get_conversion_by_trend(db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """Returns DataFrame: usage_trend category, conversion_rate, user_count."""
    query = """
        SELECT 
            usage_trend,
            AVG(CAST(converted AS FLOAT)) * 100.0 as conversion_rate,
            COUNT(*) as user_count
        FROM user_features
        GROUP BY usage_trend
        ORDER BY conversion_rate DESC
    """
    with get_connection(db_path) as conn:
        df = pd.read_sql(query, conn)
    return df


def get_conversion_by_segment(
    segment_col: str, db_path: str = DEFAULT_DB_PATH
) -> pd.DataFrame:
    """
    Returns conversion_rate and user_count grouped by the given segment_col ("plan_type" or "company_size").
    """
    ALLOWED_SEGMENTS = {"plan_type", "company_size"}
    if segment_col not in ALLOWED_SEGMENTS:
        raise ValueError(f"Invalid segment_col. Must be one of {ALLOWED_SEGMENTS}")

    # segment_col is validated against an allowlist, so it's safe to format directly into the query
    query = f"""
        SELECT 
            {segment_col} as segment_value,
            AVG(CAST(converted AS FLOAT)) * 100.0 as conversion_rate,
            COUNT(*) as user_count
        FROM user_features
        WHERE {segment_col} IS NOT NULL
        GROUP BY {segment_col}
        ORDER BY conversion_rate DESC
    """
    with get_connection(db_path) as conn:
        df = pd.read_sql(query, conn)
    return df


def get_user_features(
    filters: Optional[Dict[str, Any]] = None, db_path: str = DEFAULT_DB_PATH
) -> pd.DataFrame:
    """
    Returns full user_features dataframe (plus signup_date and conversion_date),
    optionally filtered via parameterized query.
    """
    query = """
        SELECT uf.*, uc.signup_date, uc.conversion_date 
        FROM user_features uf
        LEFT JOIN users_clean uc ON uf.user_id = uc.user_id
    """
    params = []

    if filters:
        conditions = []
        for col, val in filters.items():
            # Validate column name to prevent SQL injection via keys
            if not str(col).isidentifier():
                raise ValueError(f"Invalid column name: {col}")

            if isinstance(val, list) or isinstance(val, tuple):
                if not val:
                    continue  # empty list means no filter applied
                placeholders = ", ".join(["?"] * len(val))
                conditions.append(f"uf.{col} IN ({placeholders})")
                params.extend(val)
            else:
                conditions.append(f"uf.{col} = ?")
                params.append(val)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

    with get_connection(db_path) as conn:
        df = pd.read_sql(query, conn, params=params)
    return df


def get_engagement_ranking(db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """
    Ranks users by total_events within their signup cohort (month).
    Returns user_id, signup_month, total_events, and rank_within_cohort.
    """
    query = """
        SELECT 
            uf.user_id,
            strftime('%Y-%m', uc.signup_date) as signup_month,
            uf.total_events,
            RANK() OVER (PARTITION BY strftime('%Y-%m', uc.signup_date) ORDER BY uf.total_events DESC) as rank_within_cohort
        FROM user_features uf
        JOIN users_clean uc ON uf.user_id = uc.user_id
        ORDER BY signup_month, rank_within_cohort
    """
    with get_connection(db_path) as conn:
        df = pd.read_sql(query, conn)
    return df


def create_views(db_path: str = DEFAULT_DB_PATH):
    """
    Creates SQL views for common aggregations.
    """
    queries = [
        "DROP VIEW IF EXISTS conversion_summary;",
        """
        CREATE VIEW conversion_summary AS
        SELECT 
            plan_type, 
            company_size, 
            AVG(CAST(converted AS FLOAT)) * 100.0 as conversion_rate,
            COUNT(*) as user_count
        FROM user_features
        WHERE plan_type IS NOT NULL AND company_size IS NOT NULL
        GROUP BY plan_type, company_size;
        """,
        "DROP VIEW IF EXISTS engagement_summary;",
        """
        CREATE VIEW engagement_summary AS
        SELECT 
            converted,
            AVG(days_active) as avg_days_active,
            AVG(distinct_features_used) as avg_distinct_features_used,
            AVG(total_events) as avg_total_events,
            COUNT(*) as user_count
        FROM user_features
        GROUP BY converted;
        """,
    ]
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        for q in queries:
            cursor.execute(q)
        conn.commit()


def query_conversion_summary_view(db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    query = "SELECT * FROM conversion_summary"
    with get_connection(db_path) as conn:
        return pd.read_sql(query, conn)


def query_engagement_summary_view(db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    query = "SELECT * FROM engagement_summary"
    with get_connection(db_path) as conn:
        return pd.read_sql(query, conn)


def check_query_plan(query: str, db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """
    Runs EXPLAIN QUERY PLAN for a given SQL query and returns the plan.
    """
    explain_query = f"EXPLAIN QUERY PLAN {query}"
    with get_connection(db_path) as conn:
        df = pd.read_sql(explain_query, conn)
    return df


def validate_headline_finding_sql(db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    """
    Independently re-derives the headline stat (conversion rate for 3+ distinct
    core features in first 7 days vs users without) using pure SQL.
    Returns both SQL and Python numbers for cross-validation.
    """
    sql_query = """
    WITH core_events_first_7 AS (
        SELECT 
            u.user_id,
            COUNT(DISTINCT f.feature_name) as distinct_core_count
        FROM users_clean u
        LEFT JOIN feature_usage_clean f 
            ON u.user_id = f.user_id 
            AND f.feature_name IN ('dashboard', 'integrations', 'collaboration')
            AND (julianday(f.event_timestamp) - julianday(u.signup_date)) < 7
        GROUP BY u.user_id
    ),
    cohorts AS (
        SELECT 
            u.user_id,
            u.converted,
            CASE 
                WHEN c.distinct_core_count >= 3 THEN '3+ core features'
                ELSE '<3 core features'
            END as feature_group
        FROM users_clean u
        JOIN core_events_first_7 c ON u.user_id = c.user_id
    )
    SELECT 
        feature_group,
        AVG(CAST(converted AS FLOAT)) * 100.0 as conversion_rate
    FROM cohorts
    GROUP BY feature_group
    """

    with get_connection(db_path) as conn:
        sql_df = pd.read_sql(sql_query, conn)

    sql_high = sql_df[sql_df["feature_group"] == "3+ core features"][
        "conversion_rate"
    ].iloc[0]
    sql_low = sql_df[sql_df["feature_group"] == "<3 core features"][
        "conversion_rate"
    ].iloc[0]

    # Get Python-based result
    py_df = get_conversion_by_core_features(db_path)
    py_high = py_df[py_df["feature_group"] == "3+ core features"][
        "conversion_rate"
    ].iloc[0]
    py_low = py_df[py_df["feature_group"] == "<3 core features"][
        "conversion_rate"
    ].iloc[0]

    match_high = abs(sql_high - py_high) < 1e-5
    match_low = abs(sql_low - py_low) < 1e-5

    return {
        "sql_high_core_conversion": float(sql_high),
        "sql_low_core_conversion": float(sql_low),
        "py_high_core_conversion": float(py_high),
        "py_low_core_conversion": float(py_low),
        "matches": bool(match_high and match_low),
    }


if __name__ == "__main__":
    print("\n--- QUERY PLAN CHECKS ---")
    q1 = "SELECT * FROM users WHERE plan_type = 'Starter'"
    print(f"Query: {q1}")
    print(check_query_plan(q1))

    q2 = "SELECT uf.*, uc.signup_date FROM user_features uf LEFT JOIN users_clean uc ON uf.user_id = uc.user_id"
    print(f"\nQuery: {q2}")
    print(check_query_plan(q2))

    q3 = "SELECT * FROM feature_usage WHERE user_id = 'u1'"
    print(f"\nQuery: {q3}")
    print(check_query_plan(q3))

    print("\n--- SQL VALIDATION CHECK ---")
    val = validate_headline_finding_sql()
    print(f"Python High Core Conv: {val['py_high_core_conversion']:.1f}%")
    print(f"SQL High Core Conv:    {val['sql_high_core_conversion']:.1f}%")
    print(f"Python Low Core Conv:  {val['py_low_core_conversion']:.1f}%")
    print(f"SQL Low Core Conv:     {val['sql_low_core_conversion']:.1f}%")
    print(f"Matches exactly?       {'YES' if val['matches'] else 'NO'}")
