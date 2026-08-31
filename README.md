# TrialLens

[![CI Pipeline](https://github.com/kalviumcommunity/S63_Sem5_Sprint1_TrialLens/actions/workflows/ci.yml/badge.svg)](https://github.com/kalviumcommunity/S63_Sem5_Sprint1_TrialLens/actions/workflows/ci.yml)
Connecting free-trial user behavior to subscription conversion — so product decisions run on evidence instead of intuition.

## Problem Statement

A SaaS company has six months of free trial user activity, feature usage logs, and subscription conversion data — yet product managers still rely on intuition because no workflow connects user behavior patterns to successful upgrades. TrialLens closes that gap: it turns raw trial and usage data into a queryable, visual tool that surfaces which behaviors actually predict conversion.

## Approach

1. **Ingest** — load raw trial activity, feature usage logs, and conversion records into a SQLite database.
2. **Clean** — handle missing values, duplicates, and inconsistent timestamps; log every fix so the data is auditable.
3. **Engineer features** — turn raw event logs into per-user signals (days active, features touched, time-to-first-value, usage trend).
4. **Analyze** — compare converted vs. non-converted users across those signals to find the clearest predictors of conversion.
5. **Visualize** — surface the findings in an interactive Streamlit dashboard a PM can actually use, with filters and drill-downs.
6. **Automate** — GitHub Actions runs tests and data validation on every push, so the pipeline stays trustworthy as it grows.

## Tech Stack

| Layer | Tool |
|---|---|
| Scripting & analysis | Python |
| Data manipulation | Pandas, NumPy |
| Database / querying | SQL / SQLite |
| Dashboard | Streamlit |
| Pipeline automation & validation | GitHub Actions |

## Project Structure

```
trialens/
├── data/
│   ├── raw/              # original files, untouched
│   ├── processed/        # cleaned CSVs
│   └── trialens.db       # SQLite database
├── src/
│   ├── ingest.py         # loads raw data into SQLite
│   ├── clean.py          # cleaning + validation
│   ├── features.py       # feature engineering
│   ├── analysis.py       # EDA + statistical analysis
│   └── db.py             # SQL query helpers used by the app
├── notebooks/
│   └── eda.ipynb         # exploratory work
├── app/
│   └── streamlit_app.py  # the dashboard
├── tests/
│   └── test_cleaning.py  # sanity checks run in CI
├── .github/workflows/
│   └── ci.yml             # lint + test + data validation
├── requirements.txt
└── README.md
```

## Email Sharing Configuration

The dashboard includes a feature to share reports via email. To fully enable this feature (so it actually sends emails instead of just displaying a preview), create a `.env` file in the project root with your SMTP credentials:

```env
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_secure_password
```

If these are not configured, the app will fail gracefully and display the report payload directly in the dashboard instead of crashing.
