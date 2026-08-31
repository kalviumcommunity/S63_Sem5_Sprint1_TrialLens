import os
import sys
import time
import argparse

def run_step(step_num, step_name, func, *args, **kwargs):
    print(f"\n=== Step {step_num}/7: {step_name} ===")
    try:
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        print(f"[{step_name} completed in {duration:.2f}s]")
        return result
    except Exception as e:
        print(f"\nERROR in {step_name}: {e}")
        print("Pipeline aborted.")
        sys.exit(1)

def main(test_data_dir=None):
    parser = argparse.ArgumentParser(description="Run the full TrialLens data pipeline.")
    parser.add_argument("--force-regenerate", action="store_true", help="Regenerate synthetic data even if raw CSVs exist.")
    
    # Check if we are running in pytest; if so, args might be empty or different
    try:
        args, unknown = parser.parse_known_args()
    except SystemExit:
        args = parser.parse_args([])

    # Import pipeline steps here to ensure they only load if we run the script
    from src.generate_data import generate_synthetic_data
    from src.profile_data import run_profiling
    from src.ingest import run_ingestion
    from src.clean import run_cleaning
    from src.features import build_features
    from src.db import create_views
    from src.analysis import run_analysis

    start_time = time.time()
    
    data_dir = test_data_dir if test_data_dir else os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
    raw_dir = os.path.join(data_dir, 'raw')
    db_path = os.path.join(data_dir, 'trialens.db')
    
    users_csv = os.path.join(raw_dir, 'users.csv')
    features_csv = os.path.join(raw_dir, 'feature_usage.csv')

    print("========================================")
    print("      TRIAL LENS PIPELINE ORCHESTRATOR")
    print("========================================")

    # Step 1: Generate Data
    if args.force_regenerate or not (os.path.exists(users_csv) and os.path.exists(features_csv)):
        run_step(1, "Generating Synthetic Data", generate_synthetic_data, output_dir=raw_dir)
    else:
        print("\n=== Step 1/7: Generating Synthetic Data ===")
        print("Raw CSVs already exist. Skipping generation (use --force-regenerate to override).")

    # Step 2: Ingestion
    run_step(2, "Ingesting Data to SQLite", run_ingestion, users_csv=users_csv, feature_usage_csv=features_csv, db_path=db_path)

    # Step 3: Profile Data
    run_step(3, "Profiling Raw Data", run_profiling, db_path=db_path)

    # Step 4: Cleaning
    run_step(4, "Cleaning Data", run_cleaning, db_path=db_path)

    # Step 5: Feature Engineering
    run_step(5, "Building Features", build_features, db_path=db_path)

    # Step 6: Create Views
    run_step(6, "Creating SQL Views", create_views, db_path=db_path)

    # Step 7: Analysis
    analysis_report = run_step(7, "Running Analysis", run_analysis, db_path=db_path)

    total_duration = time.time() - start_time
    
    print("\n========================================")
    print("          PIPELINE COMPLETE")
    print("========================================")
    print(f"Total time taken: {total_duration:.2f}s")
    print(f"Final users analyzed: {analysis_report.get('total_users', 0)}")
    
    hc = analysis_report.get('headline_comparison', {})
    high_cr = hc.get('high_core_conversion_rate', 0)
    low_cr = hc.get('low_core_conversion_rate', 0)
    print("\n--- Headline Finding Confirmation ---")
    print(f"Conversion Rate (>= 3 Core Features): {high_cr:.1%}")
    print(f"Conversion Rate (< 3 Core Features):  {low_cr:.1%}")
    print("========================================")

if __name__ == "__main__":
    main()
