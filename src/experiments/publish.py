from typing import Dict, Any
import os
import json


def export_dashboard_pngs(experiment_dir: str) -> Dict[str, str]:
    """Open the dashboard HTML and analyzer results to recreate and export key charts to PNG."""
    from src.visualization.charts import ChartGenerator
    import plotly.io as pio

    results_path = os.path.join(experiment_dir, 'analyzer_results.json')
    with open(results_path, 'r') as f:
        results = json.load(f)

    gen = ChartGenerator()
    # Recreate figures via helper methods
    figs = {}
    # Build composite figures from generator internals by recreating dashboard and extracting subplots is non-trivial
    # Instead, build two high-signal charts separately using the same data
    from plotly.subplots import make_subplots
    import plotly.graph_objects as go

    # 1) Issues by Context
    issues = results['results']['issues']
    fig_ctx = go.Figure(go.Pie(labels=list(issues.keys()), values=list(issues.values()), name='Contexts'))
    ctx_path = os.path.join(experiment_dir, 'fig_issues_by_context.png')
    pio.write_image(fig_ctx, ctx_path, format='png', width=900, height=700, engine='kaleido')
    figs['issues_by_context'] = ctx_path

    # 2) Severity Distribution
    severities = results['results']['severities']
    fig_sev = go.Figure(go.Bar(x=list(severities.keys()), y=list(severities.values()), name='Severity'))
    sev_path = os.path.join(experiment_dir, 'fig_severity_distribution.png')
    pio.write_image(fig_sev, sev_path, format='png', width=900, height=700, engine='kaleido')
    figs['severity_distribution'] = sev_path

    return figs


def append_to_manuscript(fig_paths: Dict[str, str], manuscript_path: str) -> None:
    section = [
        "\n### Experiment Figures (Auto-Generated)\n",
        "The following figures were generated from the latest experiment run:\n\n"
    ]
    if 'issues_by_context' in fig_paths:
        section.append(f"- Issues by Context: ![]({fig_paths['issues_by_context']})\n")
    if 'severity_distribution' in fig_paths:
        section.append(f"- Severity Distribution: ![]({fig_paths['severity_distribution']})\n")

    with open(manuscript_path, 'a') as f:
        f.write("".join(section))


def append_stats_to_manuscript(stats: Dict[str, Any], manuscript_path: str) -> None:
    """Append a concise statistical summary to the manuscript."""
    lines = [
        "\n### Statistical Summary (Auto-Generated)\n"
    ]
    acc = stats.get('accuracy')
    ci = stats.get('accuracy_95_ci') or stats.get('accuracy_ci')
    kappa = stats.get('cohen_kappa')
    cv_mean = stats.get('cv_means') or stats.get('cv_mean') or {}
    cv_std = stats.get('cv_stds') or stats.get('cv_std') or {}

    if acc is not None and ci:
        lines.append(f"- Accuracy: {acc*100:.1f}% (95% CI: {ci[0]*100:.1f}%–{ci[1]*100:.1f}%)\n")
    if kappa is not None:
        lines.append(f"- Cohen's κ: {kappa:.2f}\n")
    if 'context_f1' in cv_mean:
        lines.append(f"- Cross-validated Context F1: {cv_mean['context_f1']:.2f} ± {cv_std.get('context_f1', 0.0):.2f}\n")

    with open(manuscript_path, 'a') as f:
        f.write("".join(lines))


def append_model_comparison_to_manuscript(model_to_stats: Dict[str, Dict[str, Any]], manuscript_path: str) -> None:
    """Append a markdown table comparing models on key metrics."""
    header = [
        "\n### Model Comparison (Auto-Generated)\n\n",
        "| Model | Accuracy | 95% CI | Macro F1 | Cohen's κ |\n",
        "|---|---:|:---:|---:|---:|\n"
    ]
    rows = []
    for model, s in model_to_stats.items():
        acc = s.get('accuracy')
        ci = s.get('accuracy_95_ci') or [None, None]
        macro_f1 = s.get('macro_f1')
        kappa = s.get('cohen_kappa')
        rows.append(f"| {model} | {acc:.3f} | [{ci[0]:.3f}, {ci[1]:.3f}] | {macro_f1:.3f} | {kappa:.2f} |\n")

    with open(manuscript_path, 'a') as f:
        f.write("".join(header + rows))


def append_significance_to_manuscript(model_a: str, model_b: str, stat: float, p_value: float, manuscript_path: str) -> None:
    section = (
        "\n### Statistical Significance (Auto-Generated)\n\n"
        f"McNemar's test comparing {model_a} vs {model_b}: χ² = {stat:.3f}, p = {p_value:.4f}. "
        + ("Difference is statistically significant (p < 0.05)." if p_value < 0.05 else "No statistically significant difference (p ≥ 0.05).")
        + "\n"
    )
    with open(manuscript_path, 'a') as f:
        f.write(section)


def append_perclass_table_to_manuscript(perclass: Dict[str, Dict[str, float]], manuscript_path: str) -> None:
    header = [
        "\n### Per-Class Performance with 95% CIs (Auto-Generated)\n\n",
        "| Class | Precision | 95% CI | Recall | 95% CI | F1 | 95% CI |\n",
        "|---|---:|:---:|---:|:---:|---:|:---:|\n"
    ]
    rows = []
    for cls, m in perclass.items():
        pr = m.get('precision', 0.0); prl, pru = m.get('precision_ci', (0.0, 0.0))
        rc = m.get('recall', 0.0); rcl, rcu = m.get('recall_ci', (0.0, 0.0))
        f1 = m.get('f1', 0.0); f1l, f1u = m.get('f1_ci', (0.0, 0.0))
        rows.append(f"| {cls} | {pr:.3f} | [{prl:.3f}, {pru:.3f}] | {rc:.3f} | [{rcl:.3f}, {rcu:.3f}] | {f1:.3f} | [{f1l:.3f}, {f1u:.3f}] |\n")
    with open(manuscript_path, 'a') as f:
        f.write("".join(header + rows))


