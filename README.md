# TrialLens

[![CI Pipeline](https://github.com/kalviumcommunity/S63_Sem5_Sprint1_TrialLens/actions/workflows/ci.yml/badge.svg)](https://github.com/kalviumcommunity/S63_Sem5_Sprint1_TrialLens/actions/workflows/ci.yml)

**Project Status: Complete — all 50 concepts implemented.**

Connecting free-trial user behavior to subscription conversion — so product decisions run on evidence instead of intuition.

## Problem Statement

A SaaS company has six months of free trial user activity, feature usage logs, and subscription conversion data — yet product managers still rely on intuition because no workflow connects user behavior patterns to successful upgrades. TrialLens closes that gap: it turns raw trial and usage data into a queryable, visual tool that surfaces which behaviors actually predict conversion.

## Live Demo

[Live Demo Placeholder](https://streamlit.io/placeholder) *(to be updated upon deployment)*

## Key Finding

Our analysis reveals a statistically significant link between core feature engagement during the first 7 days and trial conversion:

- **Conversion Rate (>= 3 Core Features):** 44.3%
- **Conversion Rate (< 3 Core Features):** 11.1%
- **Statistical Significance (p-value):** 3.128e-26

## Architecture

The pipeline follows a robust Extract, Transform, Load (ETL) and analysis workflow, entirely orchestrated by a single command (`python -m src.run_pipeline`):

```text
Raw CSVs 
   ↓ (ingest)
SQLite (users, feature_usage) 
   ↓ (clean.py)
Cleaned tables (users_clean, feature_usage_clean)
   ↓ (features.py)
user_features 
   ↓ (db.py, analysis.py)
SQL views + Statistical analysis 
   ↓ 
Streamlit dashboard (app/streamlit_app.py)
```

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
│   ├── raw/                      # Original CSVs
│   └── trialens.db               # SQLite database
├── src/
│   ├── __init__.py               # Package marker
│   ├── ingest.py                 # Loads raw data into SQLite
│   ├── profile_data.py           # Generates initial data profiles
│   ├── clean.py                  # Cleaning + validation
│   ├── features.py               # Feature engineering
│   ├── analysis.py               # EDA + statistical analysis
│   ├── db.py                     # SQL query helpers + views
│   ├── alerts.py                 # Threshold monitoring for at-risk users
│   ├── notify.py                 # Email sharing functionality
│   ├── report.py                 # Dynamic markdown report generation
│   ├── generate_data.py          # Synthetic data generation
│   └── run_pipeline.py           # E2E orchestrator
├── app/
│   └── streamlit_app.py          # Streamlit dashboard
├── docs/
│   └── data_dictionary.md        # Data Dictionary
├── tests/
│   ├── test_ingest.py            # Unit testing ingestion
│   ├── test_profile_data.py      # Unit testing profiling
│   ├── test_clean.py             # Unit testing cleaning
│   ├── test_features.py          # Unit testing feature logic
│   ├── test_db.py                # Unit testing SQL
│   ├── test_analysis.py          # Unit testing stats
│   ├── test_alerts.py            # Unit testing alerts
│   ├── test_notify.py            # Unit testing email stub
│   ├── test_report.py            # Unit testing reporting
│   └── test_run_pipeline.py      # Integration testing
├── .github/workflows/
│   └── ci.yml                    # CI/CD pipeline automation
├── requirements.txt              # Dependencies
└── README.md                     # This document
```

## How to Run Locally

```bash
git clone https://github.com/kalviumcommunity/S63_Sem5_Sprint1_TrialLens.git
cd S63_Sem5_Sprint1_TrialLens
python -m venv venv
source venv/bin/activate  # Or on Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m src.run_pipeline
python -m streamlit run app/streamlit_app.py
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

## Concepts Covered

**Environment & Git**
- [x] Setting up a Python virtual environment
- [x] Defining dependencies in `requirements.txt`
- [x] Structuring a modular Python project
- [x] Ignoring files with `.gitignore`
- [x] Utilizing environment variables (`.env`)
- [x] Managing Git feature branches

**Data Ingestion**
- [x] Reading raw CSVs with Pandas
- [x] Database connection management (context managers)
- [x] Schema definition and DDL statements
- [x] Bulk loading data into SQLite
- [x] Designing idempotent data operations
- [x] Basic referential integrity checks

**Data Cleaning**
- [x] Null value imputation and dropping
- [x] Deduplication of records
- [x] Outlier detection via IQR
- [x] String normalization
- [x] Temporal validation (window checks)
- [x] Ensuring logical consistency

**Analysis & EDA**
- [x] Automated statistical profiling
- [x] Generating a markdown Data Dictionary
- [x] Feature extraction from raw event logs
- [x] Group-by aggregations and counting
- [x] Calculating conversion rates
- [x] Identifying correlations between behaviors
- [x] Significance testing (Welch's t-test)

**SQL**
- [x] Complex JOIN operations
- [x] Window functions (`RANK() OVER`)
- [x] Common Table Expressions (CTEs)
- [x] SQL View creation and dropping
- [x] Query Plan execution evaluation (`EXPLAIN`)
- [x] Comparing Python output vs SQL engine output

**Visualisation**
- [x] Bar charts for segment breakdowns
- [x] Histograms for distribution analysis
- [x] Funnel visualization for user journeys
- [x] Time series scatter plotting
- [x] Box plots for feature spread
- [x] Dynamic dashboard KPIs

**Streamlit & App**
- [x] Layout configuration and containers
- [x] Interactive filtering (Sidebar widgets)
- [x] State persistence (`st.session_state`)
- [x] File upload and previews (`st.file_uploader`)
- [x] Direct downloadable exports (`st.download_button`)
- [x] Data storytelling and contextual alerts
- [x] Conditional rendering (Email stubs)

**Delivery & Ops**
- [x] Centralizing execution (`run_pipeline.py`)
- [x] Integration testing across a pipeline
- [x] Pytest suite covering all modules
- [x] Automated Linting (`flake8`) & Formatting (`black`)
- [x] CI/CD workflows via GitHub Actions
- [x] Headless application smoke testing
