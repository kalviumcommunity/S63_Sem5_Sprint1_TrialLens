import sqlite3
import pandas as pd
from typing import Dict, Any, Optional

DEFAULT_DB_PATH = "data/trialens.db"

def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Returns a connection to the SQLite database."""
    return sqlite3.connect(db_path)

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
    
    if df.empty or pd.isna(df.iloc[0]['total_users']) or df.iloc[0]['total_users'] == 0:
        return {'total_users': 0, 'overall_conversion_rate': 0.0, 'avg_time_to_convert': 0.0}
        
    return {
        'total_users': int(df.iloc[0]['total_users']),
        'overall_conversion_rate': round(float(df.iloc[0]['overall_conversion_rate'] or 0), 1),
        'avg_time_to_convert': round(float(df.iloc[0]['avg_time_to_convert'] or 0), 1)
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

def get_conversion_by_segment(segment_col: str, db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
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

def get_user_features(filters: Optional[Dict[str, Any]] = None, db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
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
