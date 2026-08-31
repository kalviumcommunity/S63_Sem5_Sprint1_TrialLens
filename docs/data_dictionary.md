# TrialLens Data Dictionary

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
