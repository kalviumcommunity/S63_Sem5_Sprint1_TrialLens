# Product Requirements Document (PRD): TrialLens

## 1. Product Overview
**TrialLens** is an analytical dashboard designed to uncover the hidden behavioral patterns that predict SaaS free-trial conversion. By connecting raw free-trial user activity and feature usage logs with subscription conversion data, TrialLens provides Product Managers (PMs) with actionable insights based on evidence rather than intuition.

## 2. Problem Statement
A SaaS company has amassed months of free trial user activity, feature usage logs, and subscription conversion data. Despite this wealth of data, product managers still rely on intuition and lagging indicators because there is no streamlined workflow connecting user behavior patterns to successful upgrades. 
TrialLens closes this gap: it transforms raw trial and usage data into a queryable, visual tool that surfaces the specific behaviors driving conversion.

## 3. Target Audience
- **Product Managers (PMs):** To design better onboarding flows and identify activation milestones.
- **Growth Marketers:** To target users who are slipping away or who exhibit high-intent behaviors.
- **Data Analysts:** To quickly explore trial usage data without writing repetitive SQL queries.

## 4. Goals and Success Metrics
### Goals
1. Identify the core features that correlate most strongly with trial-to-paid conversion.
2. Provide a reliable, automated ETL pipeline from raw CSV logs to a structured SQLite database.
3. Present findings in a user-friendly, interactive dashboard.

### Success Metrics
- **Pipeline Reliability:** 100% of raw data accurately cleaned and ingested.
- **Actionability:** PMs can clearly identify a statistically significant "Activation Metric" (e.g., users using 3+ core features in their first 7 days convert at a higher rate).
- **Adoption:** Frequent usage of the dashboard for exploring segmented conversion rates (by company size, plan type, etc.).

## 5. Key Features & Requirements
### 5.1 Data Ingestion & Processing Pipeline (ETL)
- **Ingest:** Load raw trial activity and feature usage CSVs.
- **Clean:** Handle missing values, duplicate entries, and inconsistent timestamps. Produce auditable logs of fixes.
- **Feature Engineering:** Calculate user-level signals such as `days_active`, `distinct_features_used`, `core_features_used_first_7_days`, `time_to_first_core_feature`, and `usage_trend`.

### 5.2 Analytical Engine
- **Statistical Significance:** Compare converted vs. non-converted users to find key predictors (e.g., Welch's t-test for numeric features, Chi-Square for categorical variables).
- **Funnel Analysis:** Track user drop-off across defined activation stages.
- **Anomaly Detection:** Identify users with high engagement but no conversion to spot friction points.

### 5.3 Interactive Dashboard (Streamlit)
- **KPI Metrics:** Total Trial Users, Conversion Rate, Average Time to Convert.
- **Alerts:** Automated warnings for users at risk of churning due to declining engagement.
- **Visualizations:** 
  - Conversion Rate by Week 1 Core Feature Usage (Headline insight).
  - Conversion Rate by Trial Usage Trend.
  - Conversion Rate by Segment (Plan Type, Company Size).
- **Data Exploration:** Filterable table to explore individual user metrics.
- **Export & Sharing:** Download summary reports (Markdown) and filtered data (CSV), or send reports via Email (SMTP integration).
- **Data Upload Preview:** Capability to upload and preview custom CSV data.

## 6. Architecture & Tech Stack
- **Scripting & Analysis:** Python (Pandas, NumPy, SciPy)
- **Database:** SQLite (SQL Views, CTEs, Window Functions)
- **Dashboard UI:** Streamlit, Plotly Express
- **Automation & CI/CD:** GitHub Actions, Pytest, Flake8, Black
- **Orchestration:** End-to-end Python pipeline (`run_pipeline.py`)

## 7. Out of Scope for MVP
- Live integration with production databases (PostgreSQL/Snowflake). MVP uses SQLite and CSV drops.
- Machine Learning models for churn prediction (relying on statistical analysis for MVP).
- Multi-tenant authentication and user roles in the dashboard.
