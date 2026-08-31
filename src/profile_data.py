import sqlite3
import pandas as pd
import numpy as np
import os

def generate_data_dictionary(docs_dir="docs"):
    """Generates the data_dictionary.md file."""
    os.makedirs(docs_dir, exist_ok=True)
    dict_path = os.path.join(docs_dir, "data_dictionary.md")
    
    content = """# TrialLens Data Dictionary

This document defines the raw ingested data sitting in `data/trialens.db`.

## Table: `users`
| Column | Data Type | Source | Business Meaning |
|--------|-----------|--------|------------------|
| `user_id` | TEXT | `data/raw/users.csv` | Unique identifier for a trial signup. |
| `signup_date` | TEXT | `data/raw/users.csv` | The calendar date the user began their trial (ISO 8601). |
| `plan_type` | TEXT | `data/raw/users.csv` | The tier of subscription they are evaluating (Starter, Pro, Enterprise). |
| `company_size` | TEXT | `data/raw/users.csv` | Self-reported employee count of the user's company. |
| `trial_length_days` | INTEGER | `data/raw/users.csv` | The duration of the free trial in days (usually 14). |
| `converted` | BOOLEAN | `data/raw/users.csv` | Whether the user successfully paid for a subscription after the trial. |
| `conversion_date` | TEXT | `data/raw/users.csv` | The date the user converted (null if they did not convert). |

## Table: `feature_usage`
| Column | Data Type | Source | Business Meaning |
|--------|-----------|--------|------------------|
| `event_id` | TEXT | `data/raw/feature_usage.csv` | Unique identifier for the interaction event. |
| `user_id` | TEXT | `data/raw/feature_usage.csv` | Foreign key to `users.user_id`, identifying who performed the action. |
| `feature_name` | TEXT | `data/raw/feature_usage.csv` | The name of the product feature utilized. |
| `event_timestamp` | TEXT | `data/raw/feature_usage.csv` | Exact time the feature was used (ISO 8601). |
| `session_id` | TEXT | `data/raw/feature_usage.csv` | Identifier grouping consecutive events into a single usage session. |
"""
    with open(dict_path, "w") as f:
        f.write(content)

def run_profiling(db_path="data/trialens.db"):
    """
    Profiles the raw `users` and `feature_usage` tables.
    Returns a dict with profiling metrics.
    """
    print(f"Starting data profiling on {db_path}...")
    
    report = {}
    
    try:
        conn = sqlite3.connect(db_path)
        tables = ['users', 'feature_usage']
        
        for table in tables:
            try:
                df = pd.read_sql(f"SELECT * FROM {table}", conn)
            except Exception as e:
                print(f"Error reading table {table}: {e}")
                continue
                
            table_report = {
                'row_count': len(df),
                'column_count': len(df.columns),
                'columns': {}
            }
            
            print(f"\n=== Table: {table} ===")
            print(f"Rows: {table_report['row_count']}, Columns: {table_report['column_count']}")
            
            for col in df.columns:
                series = df[col]
                dtype = str(series.dtype)
                null_count = series.isna().sum()
                null_pct = (null_count / len(df)) * 100 if len(df) > 0 else 0
                unique_vals = series.nunique(dropna=False)
                
                col_info = {
                    'dtype': dtype,
                    'null_pct': null_pct,
                    'unique_values': unique_vals
                }
                
                print(f"  - Column: {col}")
                print(f"    dtype: {dtype} | nulls: {null_pct:.1f}% | unique: {unique_vals}")
                
                # Numeric stats (avoid bools pretending to be numeric if they are object)
                if pd.api.types.is_numeric_dtype(series):
                    c_min = float(series.min()) if not pd.isna(series.min()) else None
                    c_max = float(series.max()) if not pd.isna(series.max()) else None
                    c_mean = float(series.mean()) if not pd.isna(series.mean()) else None
                    col_info.update({'min': c_min, 'max': c_max, 'mean': c_mean})
                    print(f"    [Numeric] min: {c_min}, max: {c_max}, mean: {c_mean:.2f}" if c_mean is not None else "    [Numeric] All NaN")
                else:
                    # Categorical/Text: Top 5
                    top_5 = series.value_counts(dropna=False).head(5)
                    top_5_dict = top_5.to_dict()
                    col_info['top_5'] = {str(k): int(v) for k, v in top_5_dict.items()}
                    print(f"    [Categorical] Top 5:")
                    for k, v in col_info['top_5'].items():
                        print(f"      {k}: {v}")
                        
                table_report['columns'][col] = col_info
                
            report[table] = table_report
            
        conn.close()
        
    except Exception as e:
        print(f"Profiling failed: {e}")
        
    generate_data_dictionary()
    print("\nGenerated data dictionary at docs/data_dictionary.md")
    
    return report

if __name__ == "__main__":
    run_profiling()
