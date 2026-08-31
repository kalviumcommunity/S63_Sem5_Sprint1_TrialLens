import sqlite3
import pandas as pd
import numpy as np
from scipy import stats

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
    df['converted'] = df['converted'].astype(bool)
    
    report = {
        'total_users': len(df),
        'overall_conversion_rate': df['converted'].mean(),
        'numeric_features': {},
        'headline_comparison': {},
        'usage_trend': {},
        'segments': {
            'plan_type': {},
            'company_size': {}
        }
    }
    
    conv_df = df[df['converted'] == True]
    non_conv_df = df[df['converted'] == False]
    
    numeric_cols = [
        'days_active', 'distinct_features_used', 
        'core_features_used_first_7_days', 'total_events', 
        'time_to_first_core_feature', 'sessions_count'
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
            
        report['numeric_features'][col] = {
            'converted_mean': c_vals.mean() if len(c_vals) > 0 else None,
            'converted_median': c_vals.median() if len(c_vals) > 0 else None,
            'non_converted_mean': nc_vals.mean() if len(nc_vals) > 0 else None,
            'non_converted_median': nc_vals.median() if len(nc_vals) > 0 else None,
            'p_value': p_val,
            'significant': significant
        }
        
    # 2. Headline Comparison
    df['high_core'] = df['core_features_used_first_7_days'] >= 3
    
    contingency_table = pd.crosstab(df['high_core'], df['converted'])
    
    if contingency_table.shape == (2, 2):
        chi2, p_val_chi, dof, ex = stats.chi2_contingency(contingency_table)
    else:
        p_val_chi = None
        
    high_group = df[df['high_core']]
    low_group = df[~df['high_core']]
    
    report['headline_comparison'] = {
        'high_core_conversion_rate': high_group['converted'].mean() if len(high_group) > 0 else 0,
        'low_core_conversion_rate': low_group['converted'].mean() if len(low_group) > 0 else 0,
        'p_value': p_val_chi,
        'significant': bool(p_val_chi < 0.05) if p_val_chi is not None else False
    }
    
    # 3. Usage Trend
    if 'usage_trend' in df.columns:
        trend_rates = df.groupby('usage_trend')['converted'].mean().to_dict()
        report['usage_trend'] = trend_rates
        
    # 4. Segmentation
    for segment_col in ['plan_type', 'company_size']:
        if segment_col in df.columns:
            for seg_val in df[segment_col].unique():
                if pd.isna(seg_val):
                    continue
                seg_df = df[df[segment_col] == seg_val]
                seg_high = seg_df[seg_df['high_core']]['converted'].mean() if len(seg_df[seg_df['high_core']]) > 0 else 0
                seg_low = seg_df[~seg_df['high_core']]['converted'].mean() if len(seg_df[~seg_df['high_core']]) > 0 else 0
                
                report['segments'][segment_col][seg_val] = {
                    'high_core_cr': seg_high,
                    'low_core_cr': seg_low,
                    'count': len(seg_df)
                }
                
    return report

if __name__ == "__main__":
    report = run_analysis()
    
    print("\n" + "="*70)
    print("                      TRIAL LENS ANALYSIS REPORT")
    print("="*70)
    print(f"Total Users Analyzed: {report.get('total_users', 0)}")
    print(f"Overall Conversion Rate: {report.get('overall_conversion_rate', 0):.1%}\n")
    
    print("--- HEADLINE COMPARISON: 3+ Core Features in Week 1 ---")
    hc = report.get('headline_comparison', {})
    print(f"Conversion (>= 3 Core): {hc.get('high_core_conversion_rate', 0):.1%}")
    print(f"Conversion (< 3 Core):  {hc.get('low_core_conversion_rate', 0):.1%}")
    if hc.get('p_value') is not None:
        print(f"Chi-square p-value:     {hc.get('p_value'):.4e}")
        print(f"Statistically Sig.?     {'Yes' if hc.get('significant') else 'No'}\n")
        
    print("--- NUMERIC FEATURES T-TESTS (Converted vs Not) ---")
    for feat, stats_dict in report.get('numeric_features', {}).items():
        sig_str = "*** SIGNIFICANT ***" if stats_dict.get('significant') else "Not sig."
        c_mean = stats_dict.get('converted_mean')
        nc_mean = stats_dict.get('non_converted_mean')
        pval = stats_dict.get('p_value')
        
        c_m_str = f"{c_mean:.2f}" if c_mean is not None else "N/A"
        nc_m_str = f"{nc_mean:.2f}" if nc_mean is not None else "N/A"
        p_str = f"{pval:.4e}" if pval is not None else "N/A"
        
        print(f"{feat:32s} | Conv: {c_m_str:>6s} | Non: {nc_m_str:>6s} | p: {p_str:>9s} | {sig_str}")
        
    print("\n--- USAGE TREND CONVERSION RATES ---")
    for trend, rate in report.get('usage_trend', {}).items():
        print(f"  {trend:15s}: {rate:.1%}")
        
    print("\n--- SEGMENTATION (High Core vs Low Core CR) ---")
    for seg_col, segments in report.get('segments', {}).items():
        print(f"\n[{seg_col.upper()}]")
        for val, metrics in segments.items():
            print(f"  {val:15s} | >=3 Core: {metrics['high_core_cr']:6.1%} | <3 Core: {metrics['low_core_cr']:6.1%} | (N={metrics['count']})")
    print("="*70 + "\n")
