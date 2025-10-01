from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import time

from src.analyzers.llm import ContextAwareLLMAnalyzer
from src.analyzers.ollama_analyzer import OllamaAnalyzer
from src.data.log_parser import LogParser


@dataclass
class BenchmarkResult:
    name: str
    metrics: Dict[str, Any]


class RuleBasedAnalyzer:
    """A very simple keyword rule-based baseline."""

    def __init__(self):
        self.parser = LogParser()
        self.category_rules = {
            'Database': ['postgres', 'mysql', 'database', 'query', 'replication'],
            'Network': ['latency', 'timeout', 'connection', 'dns', 'http 5'],
            'CPU': ['cpu', 'throttle', 'throttling', 'overload'],
            'Memory': ['memory', 'oom', 'out of memory', 'leak'],
            'Security': ['iam', 'policy', 'permission', 'access', 'breach', 'unauthorized'],
            'Application': ['exception', 'stack trace', 'service', 'endpoint', 'crash'],
        }
        self.severity_rules = {
            'Critical': ['crash', 'panic', 'unavailable', 'crashloopbackoff', 'terminated'],
            'High': ['failed', 'timeout', 'error', 'alarm'],
            'Medium': ['warning', 'degraded'],
            'Low': ['info', 'debug']
        }

    def analyze_chunk(self, logs: List[str]) -> Dict[str, Any]:
        text = " \n".join(logs).lower()
        category = 'Application'
        for cat, keys in self.category_rules.items():
            if any(k in text for k in keys):
                category = cat
                break

        severity = 'Medium'
        for sev, keys in self.severity_rules.items():
            if any(k in text for k in keys):
                severity = sev
                break

        ts = None
        for line in logs:
            parsed = self.parser.parse_line(line)
            if parsed.get('timestamp'):
                ts = parsed['timestamp']
                break

        return {
            'context': category if category in ['Database', 'Application'] else 'infrastructure',
            'category': category,
            'severity': severity,
            'component': 'baseline-rule',
            'root_cause': logs[0][:200],
            'remediation': 'N/A (rule-based baseline)',
            'timestamp': ts or time.strftime('%Y-%m-%dT%H:%M:%S')
        }


class TfidfClassifierAnalyzer:
    """A supervised baseline using TF-IDF + linear models for category and severity."""

    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.pipeline import Pipeline
        from sklearn.svm import LinearSVC
        from sklearn.linear_model import LogisticRegression

        self.parser = LogParser()
        self.category_pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=5000)),
            ('clf', LinearSVC())
        ])
        self.severity_pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=5000)),
            ('clf', LogisticRegression(max_iter=1000))
        ])
        self.fitted = False

    def fit(self, texts: List[str], categories: List[str], severities: List[str]):
        self.category_pipeline.fit(texts, categories)
        self.severity_pipeline.fit(texts, severities)
        self.fitted = True

    def analyze_chunk(self, logs: List[str]) -> Dict[str, Any]:
        if not self.fitted:
            raise RuntimeError("TfidfClassifierAnalyzer must be fit before use.")
        text = " \n".join(logs)
        category = self.category_pipeline.predict([text])[0]
        severity = self.severity_pipeline.predict([text])[0]

        ts = None
        for line in logs:
            parsed = self.parser.parse_line(line)
            if parsed.get('timestamp'):
                ts = parsed['timestamp']
                break

        return {
            'context': category.lower(),
            'category': category,
            'severity': severity,
            'component': 'baseline-tfidf',
            'root_cause': logs[0][:200],
            'remediation': 'N/A (supervised baseline)',
            'timestamp': ts or time.strftime('%Y-%m-%dT%H:%M:%S')
        }


def _to_dataset(ground_truth: Dict[str, Dict[str, Any]]) -> Tuple[List[str], List[str], List[str]]:
    texts: List[str] = []
    cats: List[str] = []
    sevs: List[str] = []
    for log, truth in ground_truth.items():
        texts.append(log)
        cats.append(truth.get('category', 'Application'))
        sevs.append(truth.get('severity', 'Medium'))
    return texts, cats, sevs


def run_comparative_benchmark(
    test_logs: List[str],
    ground_truth: Dict[str, Dict[str, Any]],
    api_key: Optional[str] = None,
    model: str = "o3-mini",
    provider: str = "openai"
) -> Dict[str, Any]:
    """
    Compare ContextAwareLLMAnalyzer with rule-based and TF-IDF baselines using
    the existing AnalyzerEvaluator.
    """
    from src.evaluation.analyzer_evaluator import AnalyzerEvaluator

    evaluator = AnalyzerEvaluator()
    results: Dict[str, Any] = {}

    # LLM analyzer
    if provider == 'openai' and api_key:
        llm = ContextAwareLLMAnalyzer(api_key=api_key, model=model)
        llm_metrics = evaluator.evaluate_analysis(llm, test_logs, ground_truth)
        results['llm'] = llm_metrics
    elif provider == 'ollama':
        oll = OllamaAnalyzer(model=model)
        oll_metrics = evaluator.evaluate_analysis(oll, test_logs, ground_truth)
        results['ollama'] = oll_metrics

    # Rule-based baseline
    rule = RuleBasedAnalyzer()
    rule_metrics = evaluator.evaluate_analysis(rule, test_logs, ground_truth)
    results['rule_based'] = rule_metrics

    # TF-IDF baseline (fit on available ground truth)
    tfidf = TfidfClassifierAnalyzer()
    texts, cats, sevs = _to_dataset(ground_truth)
    if texts:
        tfidf.fit(texts, cats, sevs)
        tfidf_metrics = evaluator.evaluate_analysis(tfidf, test_logs, ground_truth)
        results['tfidf'] = tfidf_metrics

    return results


def comparative_plots(results: Dict[str, Any]) -> Dict[str, Any]:
    """Return Plotly figures comparing accuracy, error, and response times."""
    import plotly.graph_objects as go

    names = []
    accuracies = []
    cat_acc = []
    sev_acc = []
    err_rates = []
    hall_rates = []

    for name, metrics in results.items():
        names.append(name)
        accuracies.append(metrics.accuracy)
        cat_acc.append(metrics.categorization_accuracy)
        sev_acc.append(metrics.severity_accuracy)
        err_rates.append(metrics.error_rate)
        hall_rates.append(metrics.hallucination_rate)

    fig_acc = go.Figure()
    fig_acc.add_bar(x=names, y=accuracies, name='Overall Accuracy')
    fig_acc.add_bar(x=names, y=cat_acc, name='Category Accuracy')
    fig_acc.add_bar(x=names, y=sev_acc, name='Severity Accuracy')
    fig_acc.update_layout(barmode='group', title='Benchmark Accuracy Comparison')

    fig_err = go.Figure()
    fig_err.add_bar(x=names, y=err_rates, name='Error Rate')
    fig_err.add_bar(x=names, y=hall_rates, name='Hallucination Rate')
    fig_err.update_layout(barmode='group', title='Benchmark Error Metrics')

    return {
        'accuracy': fig_acc,
        'errors': fig_err
    }






