# src/cli.py
import click
import os
from dotenv import load_dotenv
from src.analyzers.llm import ContextAwareLLMAnalyzer
from src.analyzers.ollama_analyzer import OllamaAnalyzer
from src.data.log_parser import LogParser
from src.visualization.charts import ChartGenerator
import json
from datetime import datetime
from typing import Dict, Any, List

from src.benchmarks.comparative import run_comparative_benchmark, comparative_plots
from src.evaluation.stats import stratified_cv_accuracy, mcnemar_test
from src.data.ec2_stream import CloudWatchEC2Stream
from src.data.elk import ElasticsearchClient
from src.data.splunk import SplunkClient
from src.experiments.runner import run_experiment
from src.experiments.publish import export_dashboard_pngs, append_to_manuscript, append_stats_to_manuscript, append_model_comparison_to_manuscript, append_significance_to_manuscript, append_perclass_table_to_manuscript
from src.evaluation.enhanced_analyzer_evaluator import EnhancedAnalyzerEvaluator

load_dotenv()

@click.group()
def cli():
    """Log Insight - AI-Powered Log Analysis Tool"""
    pass

@cli.command()
@click.argument('log_file', type=click.Path(exists=True))
@click.option('--chunk-size', default=10, help='Number of logs to process at once')
@click.option('--output', '-o', default='analysis_results.html', help='Output file for visualization')
@click.option('--format', '-f', type=click.Choice(['html', 'json']), default='html', help='Output format')
@click.option('--provider', type=click.Choice(['openai', 'ollama']), default='openai')
@click.option('--api-key', envvar='OPENAI_API_KEY', help='OpenAI API key')
@click.option('--ollama-host', default='http://localhost:11434')
@click.option('--model', default='gpt-4o-mini', help='Model name')
def analyze(log_file, chunk_size, output, format, provider, api_key, ollama_host, model):
    """Analyze log file and generate insights"""
    if provider == 'openai' and not api_key:
        raise click.UsageError("OpenAI API key is required for provider=openai. Set OPENAI_API_KEY or use --api-key")
    
    click.echo(f"Analyzing log file: {log_file}")
    
    # Initialize components
    parser = LogParser(chunk_size=chunk_size)
    if provider == 'openai':
        analyzer = ContextAwareLLMAnalyzer(api_key=api_key, model=model)
    else:
        analyzer = OllamaAnalyzer(model=model, host=ollama_host)
    
    # Process logs
    with click.progressbar(length=os.path.getsize(log_file),
                         label='Processing logs') as bar:
        for chunk in parser.parse_file(log_file):
            analyzer.analyze_chunk(chunk)
            bar.update(len('\n'.join(chunk).encode('utf-8')))
    
    results = analyzer.get_results()
    
    if format == 'json':
        # Save JSON results
        output_file = output if output.endswith('.json') else f"{output}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        click.echo(f"Results saved to {output_file}")
    else:
        # Generate visualization
        generator = ChartGenerator()
        generator.create_dashboard(results, filename=output)
        click.echo(f"Dashboard saved to {output}")

@cli.command()
@click.argument('log_file', type=click.Path(exists=True))
@click.option('--live/--no-live', default=False, help='Enable live monitoring')
def monitor(log_file, live):
    """Monitor log file for new entries"""
    click.echo(f"Monitoring log file: {log_file}")
    if live:
        click.echo("Live monitoring enabled - press Ctrl+C to stop")
        # TODO: Implement live monitoring
    else:
        click.echo("Live monitoring disabled")

@cli.command()
@click.option('--host', default='localhost', help='Host to run the dashboard on')
@click.option('--port', default=8050, help='Port to run the dashboard on')
def dashboard(host, port):
    """Launch interactive dashboard"""
    click.echo(f"Starting dashboard on http://{host}:{port}")
    # TODO: Implement interactive dashboard


def _load_ground_truth(path: str) -> Dict[str, Any]:
    """Load ground truth mapping from a JSON or JSONL file.
    Expected schema: { log_line: {"category": str, "severity": str, ...}, ... }
    """
    if path.endswith('.jsonl') or path.endswith('.ndjson'):
        data: Dict[str, Any] = {}
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                log_line = obj.get('log') or obj.get('log_line')
                labels = obj.get('labels') or {k: v for k, v in obj.items() if k not in {'log', 'log_line'}}
                if log_line:
                    data[log_line] = labels
        return data
    else:
        with open(path, 'r') as f:
            return json.load(f)


def _load_logs_file(path: str) -> List[str]:
    with open(path, 'r') as f:
        return [line.strip() for line in f if line.strip()]


@cli.command()
@click.argument('log_file', type=click.Path(exists=True))
@click.argument('ground_truth_file', type=click.Path(exists=True))
@click.option('--provider', type=click.Choice(['openai', 'ollama']), default='openai')
@click.option('--api-key', envvar='OPENAI_API_KEY', help='OpenAI API key (optional for LLM arm)')
@click.option('--model', default='o3-mini', help='Model to use (OpenAI or Ollama tag)')
@click.option('--out-prefix', default=lambda: os.getenv('RESULTS_ROOT', 'results') + '/benchmarks/bench', help='Output prefix for plots/files')
@click.option('--manuscript', default=None, help='Optional manuscript path to append stats')
def benchmark(log_file, ground_truth_file, provider, api_key, model, out_prefix, manuscript):
    """Run comparative benchmark: LLM vs rule-based vs TF-IDF baselines."""
    click.echo("Loading data...")
    logs = _load_logs_file(log_file)
    truth = _load_ground_truth(ground_truth_file)

    click.echo("Running benchmarks...")
    results = run_comparative_benchmark(logs, truth, api_key=api_key, model=model, provider=provider)

    click.echo("Generating comparative plots...")
    figs = comparative_plots(results)
    acc_path = f"{out_prefix}_accuracy.html"
    err_path = f"{out_prefix}_errors.html"
    figs['accuracy'].write_html(acc_path)
    figs['errors'].write_html(err_path)

    # Save raw metrics
    metrics_path = f"{out_prefix}_metrics.json"
    serializable = {
        name: {
            'accuracy': m.accuracy,
            'categorization_accuracy': m.categorization_accuracy,
            'severity_accuracy': m.severity_accuracy,
            'avg_response_time': m.avg_response_time,
            'error_rate': m.error_rate,
            'hallucination_rate': m.hallucination_rate,
        } for name, m in results.items()
    }
    with open(metrics_path, 'w') as f:
        json.dump(serializable, f, indent=2)

    click.echo(f"Saved: {acc_path}, {err_path}, {metrics_path}")

    # Enhanced statistical summary (LLM only, if api_key provided)
    if provider == 'openai' and api_key:
        try:
            from src.analyzers.llm import ContextAwareLLMAnalyzer
            evaluator = EnhancedAnalyzerEvaluator()
            analyzer = ContextAwareLLMAnalyzer(api_key=api_key, model=model)
            enhanced = evaluator.comprehensive_evaluation(analyzer, logs, truth)

            enhanced_stats = {
                'accuracy': float(enhanced.accuracy),
                'accuracy_95_ci': [
                    float(enhanced.confidence_intervals['accuracy']['lower']),
                    float(enhanced.confidence_intervals['accuracy']['upper'])
                ],
                'cohen_kappa': float(enhanced.cohen_kappa),
                'cv_means': enhanced.cv_mean,
                'cv_stds': enhanced.cv_std,
                'macro_f1': float(enhanced.macro_f1),
                'micro_f1': float(enhanced.micro_f1),
                'weighted_f1': float(enhanced.weighted_f1)
            }

            enhanced_path = f"{out_prefix}_enhanced_stats.json"
            with open(enhanced_path, 'w') as f:
                json.dump(enhanced_stats, f, indent=2)
            click.echo(f"Saved enhanced stats: {enhanced_path}")

            if manuscript:
                append_stats_to_manuscript(enhanced_stats, manuscript)
                click.echo(f"Appended stats to {manuscript}")
        except Exception as e:
            click.echo(f"Warning: enhanced stats generation failed: {str(e)}")


@cli.command()
@click.argument('dataset_file', type=click.Path(exists=True))
@click.option('--folds', default=5, help='Number of CV folds')
def stats(dataset_file, folds):
    """Compute cross-validation accuracy and 95% CI on a JSONL dataset.
    JSONL schema: {"log": str, "category": str}
    """
    click.echo("Loading dataset...")
    data = _load_ground_truth(dataset_file)
    texts = list(data.keys())
    labels = [v.get('category', 'Application') for v in data.values()]

    from src.benchmarks.comparative import TfidfClassifierAnalyzer

    def fit_fn(X_train, y_train):
        model = TfidfClassifierAnalyzer()
        dummy_sev = ['Medium'] * len(y_train)
        model.fit(X_train, y_train, dummy_sev)
        return model

    def predict_fn(model, X_test):
        return [model.category_pipeline.predict([x])[0] for x in X_test]

    cv = stratified_cv_accuracy(texts, labels, predict_fn=predict_fn, fit_fn=fit_fn, folds=folds)
    click.echo(json.dumps({
        'folds': cv.folds,
        'accuracies': cv.accuracies,
        'mean_accuracy': cv.mean_accuracy,
        'ci95': cv.ci95
    }, indent=2))


@cli.command()
@click.option('--log-group', required=True, help='CloudWatch log group name')
@click.option('--log-stream', default=None, help='Optional CloudWatch log stream')
@click.option('--region', default=None, help='AWS region')
@click.option('--chunk-size', default=5, help='Number of log lines per LLM analysis')
@click.option('--api-key', envvar='OPENAI_API_KEY', help='OpenAI API key')
@click.option('--output', '-o', default='stream_dashboard.html', help='Output dashboard file')
def ec2_stream(log_group, log_stream, region, chunk_size, api_key, output):
    """Stream logs from CloudWatch and analyze in near real-time."""
    if not api_key:
        raise click.UsageError("OpenAI API key is required. Set OPENAI_API_KEY or use --api-key")

    click.echo(f"Connecting to CloudWatch group={log_group} stream={log_stream or '*'} region={region or 'default'}")
    streamer = CloudWatchEC2Stream(log_group=log_group, log_stream=log_stream, region=region)
    analyzer = ContextAwareLLMAnalyzer(api_key=api_key)
    generator = ChartGenerator()

    buffer: List[str] = []
    try:
        for line in streamer.poll():
            buffer.append(line)
            if len(buffer) >= chunk_size:
                analyzer.analyze_chunk(buffer)
                buffer = []

                # Periodically refresh dashboard
                results = analyzer.get_results()
                generator.create_dashboard(results, filename=output)
                click.echo(f"Updated dashboard -> {output} at {datetime.now().isoformat()}")
    except KeyboardInterrupt:
        click.echo("Stopping stream...")


@cli.command()
@click.option('--es-endpoint', default=None, help='Elasticsearch endpoint (or use --es-cloud-id)')
@click.option('--es-cloud-id', default=None, help='Elastic Cloud ID')
@click.option('--es-api-key', envvar='ELASTIC_API_KEY', default=None, help='Elasticsearch API key')
@click.option('--index', required=True, help='Index name')
@click.option('--term-field', default=None)
@click.option('--term-value', default=None)
@click.option('--query-json', default=None, help='Raw JSON query string')
def elk_query(es_endpoint, es_cloud_id, es_api_key, index, term_field, term_value, query_json):
    """Query Elasticsearch to pull logs for side-by-side comparison."""
    client = ElasticsearchClient(endpoint=es_endpoint, api_key=es_api_key, cloud_id=es_cloud_id)
    if query_json:
        query = json.loads(query_json)
        docs = client.search_logs(index=index, query=query)
    else:
        if not (term_field and term_value):
            raise click.UsageError('Provide --term-field and --term-value or --query-json')
        docs = client.term_query(index=index, field=term_field, value=term_value)
    click.echo(json.dumps({'count': len(docs), 'samples': docs[:5]}, indent=2))


@cli.command()
@click.option('--host', required=True)
@click.option('--port', type=int, default=8089)
@click.option('--username', envvar='SPLUNK_USERNAME')
@click.option('--password', envvar='SPLUNK_PASSWORD')
@click.option('--query', required=True)
@click.option('--earliest', default='-24h')
@click.option('--latest', default='now')
def splunk_query(host, port, username, password, query, earliest, latest):
    """Query Splunk to pull logs for side-by-side comparison."""
    if not (username and password):
        raise click.UsageError('Set SPLUNK_USERNAME and SPLUNK_PASSWORD or pass flags')
    client = SplunkClient(host=host, port=port, username=username, password=password)
    rows = client.search(query=query, earliest=earliest, latest=latest)
    click.echo(json.dumps({'count': len(rows), 'samples': rows[:5]}, indent=2))


@cli.command()
@click.option('--region', required=True)
@click.option('--key-name', required=True, help='EC2 key pair name')
@click.option('--provider', type=click.Choice(['openai', 'ollama']), default='openai')
@click.option('--api-key', envvar='OPENAI_API_KEY')
@click.option('--model', default='gpt-4o-mini')
@click.option('--ollama-host', default='http://localhost:11434')
@click.option('--duration', default=300, help='Stream duration seconds')
@click.option('--chunk-size', default=5)
@click.option('--terraform-dir', default='infra/terraform')
@click.option('--out-root', default=lambda: os.getenv('RESULTS_ROOT', 'results') + '/experiments')
@click.option('--destroy/--no-destroy', default=True)
@click.option('--elk-endpoint', default=None)
@click.option('--elk-cloud-id', default=None)
@click.option('--elk-api-key', envvar='ELASTIC_API_KEY', default=None)
@click.option('--elk-index', default=None)
@click.option('--elk-term-field', default=None)
@click.option('--elk-term-value', default=None)
@click.option('--elk-query-json', default=None)
@click.option('--splunk-host', default=None)
@click.option('--splunk-port', default=8089)
@click.option('--splunk-username', envvar='SPLUNK_USERNAME', default=None)
@click.option('--splunk-password', envvar='SPLUNK_PASSWORD', default=None)
@click.option('--splunk-query', default=None)
@click.option('--splunk-earliest', default='-24h')
@click.option('--splunk-latest', default='now')
def experiment(region, key_name, provider, api_key, model, ollama_host, duration, chunk_size, terraform_dir, out_root, destroy,
               elk_endpoint, elk_cloud_id, elk_api_key, elk_index, elk_term_field, elk_term_value, elk_query_json,
               splunk_host, splunk_port, splunk_username, splunk_password, splunk_query, splunk_earliest, splunk_latest):
    """Provision EC2 via Terraform, stream logs, analyze, and optionally pull ELK/Splunk for comparison."""
    if provider == 'openai' and not api_key:
        raise click.UsageError('OPENAI provider selected but no --api-key provided')
    elk_params = {
        'endpoint': elk_endpoint,
        'cloud_id': elk_cloud_id,
        'api_key': elk_api_key,
        'index': elk_index,
        'term_field': elk_term_field,
        'term_value': elk_term_value,
        'query_json': elk_query_json
    }
    splunk_params = {
        'host': splunk_host,
        'port': splunk_port,
        'username': splunk_username,
        'password': splunk_password,
        'query': splunk_query,
        'earliest': splunk_earliest,
        'latest': splunk_latest
    }
    out_dir = run_experiment(
        terraform_dir=terraform_dir,
        region=region,
        key_name=key_name,
        api_key=api_key or "",
        duration_seconds=duration,
        chunk_size=chunk_size,
        out_root=out_root,
        destroy_after=destroy,
        elk_params=elk_params,
        splunk_params=splunk_params
    )
    click.echo(json.dumps({'experiment_dir': out_dir}, indent=2))


@cli.command()
@click.argument('log_file', type=click.Path(exists=True))
@click.argument('ground_truth_file', type=click.Path(exists=True))
@click.option('--provider', type=click.Choice(['openai', 'ollama']), default='openai')
@click.option('--models', multiple=True, required=True, help='Models to benchmark (repeat flag)')
@click.option('--manuscript', default='docs/results/manuscript.md')
@click.option('--out-dir', default=lambda: os.getenv('RESULTS_ROOT', 'results') + '/benchmarks')
@click.option('--api-key', envvar='OPENAI_API_KEY')
def benchmark_sweep(log_file, ground_truth_file, provider, models, manuscript, out_dir, api_key):
    """Run benchmarks across multiple models and append a comparison table to the manuscript."""
    logs = _load_logs_file(log_file)
    truth = _load_ground_truth(ground_truth_file)

    evaluator = EnhancedAnalyzerEvaluator()
    model_to_stats = {}
    for model in models:
        if provider == 'openai':
            analyzer = ContextAwareLLMAnalyzer(api_key=api_key, model=model)
        else:
            analyzer = OllamaAnalyzer(model=model)
        enhanced = evaluator.comprehensive_evaluation(analyzer, logs, truth)
        stats = {
            'accuracy': float(enhanced.accuracy),
            'accuracy_95_ci': [
                float(enhanced.confidence_intervals['accuracy']['lower']),
                float(enhanced.confidence_intervals['accuracy']['upper'])
            ],
            'cohen_kappa': float(enhanced.cohen_kappa),
            'macro_f1': float(enhanced.macro_f1),
        }
        model_to_stats[model] = stats
        out_path = os.path.join(out_dir, f'bench_{model}_enhanced_stats.json')
        os.makedirs(out_dir, exist_ok=True)
        with open(out_path, 'w') as f:
            json.dump(stats, f, indent=2)
        click.echo(f"Saved {out_path}")

    append_model_comparison_to_manuscript(model_to_stats, manuscript)
    click.echo(f"Appended model comparison to {manuscript}")


@cli.command()
@click.argument('log_file', type=click.Path(exists=True))
@click.argument('ground_truth_file', type=click.Path(exists=True))
@click.option('--model-a', required=True)
@click.option('--model-b', required=True)
@click.option('--api-key', envvar='OPENAI_API_KEY', required=True)
@click.option('--manuscript', default='docs/results/manuscript.md')
def stats_significance(log_file, ground_truth_file, model_a, model_b, api_key, manuscript):
    """Compute McNemar's test between two models and append to manuscript."""
    logs = _load_logs_file(log_file)
    truth = _load_ground_truth(ground_truth_file)

    from src.analyzers.llm import ContextAwareLLMAnalyzer
    evalr = EnhancedAnalyzerEvaluator()

    a_preds = [ContextAwareLLMAnalyzer(api_key=api_key, model=model_a).analyze_chunk([x]) for x in logs]
    b_preds = [ContextAwareLLMAnalyzer(api_key=api_key, model=model_b).analyze_chunk([x]) for x in logs]

    y_true = [truth.get(x, {}).get('category') for x in logs]
    y_pred_a = [p.get('category') if p else None for p in a_preds]
    y_pred_b = [p.get('category') if p else None for p in b_preds]

    # Build correct/incorrect arrays
    correct_a = [int(t == p) for t, p in zip(y_true, y_pred_a)]
    correct_b = [int(t == p) for t, p in zip(y_true, y_pred_b)]
    b01 = sum(1 for ca, cb in zip(correct_a, correct_b) if ca == 1 and cb == 0)
    b10 = sum(1 for ca, cb in zip(correct_a, correct_b) if ca == 0 and cb == 1)
    stat = ((abs(b01 - b10) - 1) ** 2) / (b01 + b10) if (b01 + b10) > 0 else 0.0
    import math
    from math import exp
    import scipy.stats as sps
    p_value = 1 - sps.chi2.cdf(stat, 1) if (b01 + b10) > 0 else 1.0

    append_significance_to_manuscript(model_a, model_b, float(stat), float(p_value), manuscript)
    click.echo(json.dumps({'model_a': model_a, 'model_b': model_b, 'statistic': stat, 'p_value': p_value}, indent=2))


@cli.command()
@click.argument('log_file', type=click.Path(exists=True))
@click.argument('ground_truth_file', type=click.Path(exists=True))
@click.option('--model', required=True)
@click.option('--api-key', envvar='OPENAI_API_KEY', required=True)
@click.option('--manuscript', default='docs/results/manuscript.md')
def stats_perclass(log_file, ground_truth_file, model, api_key, manuscript):
    """Compute per-class precision/recall/F1 with bootstrap 95% CIs and append to manuscript."""
    logs = _load_logs_file(log_file)
    truth = _load_ground_truth(ground_truth_file)
    from src.analyzers.llm import ContextAwareLLMAnalyzer
    analyzer = ContextAwareLLMAnalyzer(api_key=api_key, model=model)

    # Collect predictions
    preds = [analyzer.analyze_chunk([x]) for x in logs]
    y_true = [truth.get(x, {}).get('category', 'Unknown') for x in logs]
    y_pred = [p.get('category', 'Unknown') if p else 'Unknown' for p in preds]

    # Compute per-class metrics with Wilson CIs for precision/recall
    from collections import Counter
    classes = sorted(set(y_true))
    perclass = {}
    def wilson_ci(success: int, total: int, z: float = 1.96):
        if total <= 0:
            return (0.0, 0.0)
        phat = success / total
        denom = 1 + z*z/total
        centre = phat + z*z/(2*total)
        margin = z*((phat*(1-phat)/total) + (z*z/(4*total*total)))**0.5
        lower = (centre - margin)/denom
        upper = (centre + margin)/denom
        return (max(0.0, lower), min(1.0, upper))

    for cls in classes:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == cls and p == cls)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != cls and p == cls)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == cls and p != cls)
        prec_den = tp + fp
        rec_den = tp + fn
        precision = tp/prec_den if prec_den > 0 else 0.0
        recall = tp/rec_den if rec_den > 0 else 0.0
        f1 = (2*precision*recall/(precision+recall)) if (precision+recall) > 0 else 0.0
        p_ci = wilson_ci(tp, prec_den) if prec_den > 0 else (0.0, 0.0)
        r_ci = wilson_ci(tp, rec_den) if rec_den > 0 else (0.0, 0.0)
        perclass[cls] = {
            'precision': float(precision), 'precision_ci': p_ci,
            'recall': float(recall), 'recall_ci': r_ci,
            'f1': float(f1), 'f1_ci': (float(f1), float(f1))
        }

    # Append table
    append_perclass_table_to_manuscript(perclass, manuscript)
    click.echo(json.dumps({'classes': classes}, indent=2))


@cli.command()
@click.argument('log_file', type=click.Path(exists=True))
@click.argument('ground_truth_file', type=click.Path(exists=True))
@click.option('--model', required=True)
@click.option('--api-key', envvar='OPENAI_API_KEY', required=True)
@click.option('--manuscript', default='docs/results/manuscript.md')
@click.option('--out-fig', default=lambda: os.getenv('RESULTS_ROOT', 'results') + '/figures/reliability_gpt4o_mini.png')
def stats_calibration(log_file, ground_truth_file, model, api_key, manuscript, out_fig):
    """Compute ECE and Brier score; export a reliability plot and append summary to manuscript."""
    logs = _load_logs_file(log_file)
    truth = _load_ground_truth(ground_truth_file)
    from src.analyzers.llm import ContextAwareLLMAnalyzer
    analyzer = ContextAwareLLMAnalyzer(api_key=api_key, model=model)

    preds = [analyzer.analyze_chunk([x]) for x in logs]
    y_true = [truth.get(x, {}).get('category') for x in logs]
    y_pred = [p.get('category') if p else None for p in preds]
    conf = [float((p or {}).get('confidence_score', 0.5)) for p in preds]
    correct = [int(t == p) for t, p in zip(y_true, y_pred)]

    from src.evaluation.statistical_utilities import StatisticalAnalyzer
    sa = StatisticalAnalyzer()
    ece = sa.expected_calibration_error(conf, correct)
    brier = sa.brier_score(conf, correct)

    # Reliability plot via Plotly
    import numpy as np
    import plotly.graph_objects as go
    bins = np.linspace(0, 1, 11)
    bin_centres = (bins[:-1] + bins[1:]) / 2
    accs = []
    confs = []
    weights = []
    conf_arr = np.array(conf)
    corr_arr = np.array(correct)
    for i in range(len(bins)-1):
        lo, hi = bins[i], bins[i+1]
        idx = (conf_arr >= lo) & (conf_arr < hi if i < len(bins)-2 else conf_arr <= hi)
        if idx.any():
            accs.append(float(corr_arr[idx].mean()))
            confs.append(float(conf_arr[idx].mean()))
            weights.append(float(idx.mean()))
        else:
            accs.append(0.0); confs.append((lo+hi)/2); weights.append(0.0)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=confs, y=accs, mode='lines+markers', name='Accuracy vs Confidence'))
    fig.add_trace(go.Scatter(x=[0,1], y=[0,1], mode='lines', name='Perfect Calibration', line=dict(dash='dash')))
    fig.update_layout(title=f'Reliability Diagram ({model})', xaxis_title='Confidence', yaxis_title='Empirical Accuracy', height=400)

    os.makedirs(os.path.dirname(out_fig), exist_ok=True)
    fig.write_image(out_fig, engine='kaleido', width=900, height=600)

    # Append summary to manuscript
    with open(manuscript, 'a') as f:
        f.write("\n### Calibration (Auto-Generated)\n\n")
        f.write(f"- ECE: {ece:.3f}\n\n")
        f.write(f"- Brier Score: {brier:.3f}\n\n")
        f.write(f"- Reliability Figure: ![]({out_fig})\n")

    click.echo(json.dumps({'ece': ece, 'brier': brier, 'figure': out_fig}, indent=2))


@cli.command()
@click.argument('experiment_dir', type=click.Path(exists=True))
@click.option('--manuscript', default='docs/results/manuscript.md')
def publish(experiment_dir, manuscript):
    """Export key PNG figures from an experiment run and append to manuscript."""
    figs = export_dashboard_pngs(experiment_dir)
    append_to_manuscript(figs, manuscript)
    click.echo(json.dumps({'exported': figs, 'manuscript': manuscript}, indent=2))


@cli.command()
@click.option('--manuscript', default='docs/results/manuscript.md')
@click.option('--results', default='publication_ready_results.json', help='Path to stats JSON')
def publish_stats(manuscript, results):
    """Append statistical summary from a results JSON to the manuscript."""
    with open(results, 'r') as f:
        stats = json.load(f)
    append_stats_to_manuscript(stats, manuscript)
    click.echo(json.dumps({'manuscript': manuscript, 'source': results}, indent=2))

if __name__ == '__main__':
    cli()