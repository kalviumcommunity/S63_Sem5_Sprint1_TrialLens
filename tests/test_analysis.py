import pandas as pd
import pytest
from src.analysis import run_analysis

def test_run_analysis_significance():
    data = []
    
    # 50 converted users, high engagement
    for i in range(50):
        data.append({
            'user_id': f'c_{i}',
            'converted': True,
            'core_features_used_first_7_days': 3 + (i % 2),
            'total_events': 30 + (i % 5),
            'days_active': 10 + (i % 3),
            'distinct_features_used': 6 + (i % 2),
            'time_to_first_core_feature': 1 + (i % 2),
            'sessions_count': 15 + (i % 4),
            'usage_trend': 'increasing',
            'plan_type': 'Pro',
            'company_size': '11-50'
        })
        
    # 50 non-converted users, low engagement
    for i in range(50):
        data.append({
            'user_id': f'nc_{i}',
            'converted': False,
            'core_features_used_first_7_days': 1 + (i % 2),
            'total_events': 5 + (i % 3),
            'days_active': 2 + (i % 2),
            'distinct_features_used': 2 + (i % 2),
            'time_to_first_core_feature': 5 + (i % 2),
            'sessions_count': 3 + (i % 2),
            'usage_trend': 'decreasing',
            'plan_type': 'Starter',
            'company_size': '1-10'
        })
        
    df = pd.DataFrame(data)
    report = run_analysis(df=df)
    
    nf = report['numeric_features']
    assert nf['total_events']['significant'] is True
    assert nf['total_events']['converted_mean'] > nf['total_events']['non_converted_mean']
    assert nf['total_events']['p_value'] < 0.05
    
    hc = report['headline_comparison']
    assert hc['significant'] is True
    assert hc['high_core_conversion_rate'] > 0.9  # Should be exactly 1.0 based on dummy data
    assert hc['low_core_conversion_rate'] < 0.1   # Should be exactly 0.0 based on dummy data
    
    seg = report['segments']
    assert 'Pro' in seg['plan_type']
    assert seg['plan_type']['Pro']['high_core_cr'] > 0.9

    # Assertions on distributions
    assert 'distributions' in report
    dist = report['distributions']
    assert 'total_events' in dist
    assert 'converted' in dist['total_events']
    assert 'not_converted' in dist['total_events']
    assert 'mean' in dist['total_events']['converted']
    assert 'median' in dist['total_events']['converted']
    
    # Assertions on correlation matrix
    assert 'correlation_matrix' in report
    corr = report['correlation_matrix']
    assert isinstance(corr, pd.DataFrame)
    
    # Check it's symmetric
    assert (corr.columns == corr.index).all()
    
    # Check 1.0 on diagonal
    for col in corr.columns:
        assert abs(corr.loc[col, col] - 1.0) < 1e-6
