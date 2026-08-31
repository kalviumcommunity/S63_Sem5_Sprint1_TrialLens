from typing import Dict, Any

def generate_report_text(analysis_report: Dict[str, Any], kpi_summary: Dict[str, Any]) -> str:
    """
    Generates a markdown summary report containing:
    - KPI summary
    - Headline finding with its stat and significance
    - Funnel stages
    - Segment breakdown
    """
    lines = []
    
    # 1. KPI Summary
    lines.append("# TrialLens Summary Report\n")
    lines.append("## KPI Summary")
    lines.append(f"- **Total Trial Users**: {kpi_summary.get('total_users', 0):,}")
    lines.append(f"- **Overall Conversion Rate**: {kpi_summary.get('overall_conversion_rate', 0.0):.1f}%")
    lines.append(f"- **Avg Time to Convert**: {kpi_summary.get('avg_time_to_convert', 0.0):.1f} days\n")
    
    # 2. Headline Finding
    lines.append("## Headline Finding: Core Feature Engagement")
    hc = analysis_report.get('headline_comparison', {})
    high_cr = hc.get('high_core_conversion_rate', 0) * 100
    low_cr = hc.get('low_core_conversion_rate', 0) * 100
    pval = hc.get('p_value')
    pval_str = f"{pval:.2e}" if pval is not None else "N/A"
    sig_text = "statistically significant" if hc.get('significant') else "not statistically significant"
    
    lines.append(f"Users who engage with 3 or more core features within their first 7 days convert at "
                 f"**{high_cr:.1f}%**, compared to just **{low_cr:.1f}%** for those who don't. "
                 f"This effect is {sig_text} (p-value: {pval_str}).\n")
    
    # 3. Funnel Stages
    lines.append("## Funnel Stages")
    funnel_df = analysis_report.get('funnel')
    if funnel_df is not None and not funnel_df.empty:
        for idx, row in funnel_df.iterrows():
            stage = row['stage_name'].replace('_', ' ').title()
            count = row['user_count']
            pct = row['pct_of_total'] * 100
            lines.append(f"- **{stage}**: {count:,} users ({pct:.1f}%)")
    else:
        lines.append("*Funnel data not available.*")
    lines.append("")
    
    # 4. Segment Breakdown
    lines.append("## Segment Breakdown (High Core vs Low Core Conversion Rate)")
    segments = analysis_report.get('segments', {})
    for seg_col, segment_data in segments.items():
        lines.append(f"### By {seg_col.replace('_', ' ').title()}")
        for val, metrics in segment_data.items():
            high = metrics['high_core_cr'] * 100
            low = metrics['low_core_cr'] * 100
            n = metrics['count']
            lines.append(f"- **{val}**: >=3 Core: {high:.1f}% | <3 Core: {low:.1f}% (N={n})")
        lines.append("")
        
    return "\n".join(lines)
