from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from datetime import datetime
import json
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support, confusion_matrix,
    f1_score, cohen_kappa_score, matthews_corrcoef
)
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import LabelEncoder
import scipy.stats as stats
from dataclasses import dataclass
import warnings
from collections import Counter
import time


@dataclass
class EnhancedMetrics:
    accuracy: float
    balanced_accuracy: float
    precision: Dict[str, float]
    recall: Dict[str, float]
    f1_score: Dict[str, float]
    macro_f1: float
    micro_f1: float
    weighted_f1: float
    cohen_kappa: float
    matthews_corrcoef: float
    confidence_intervals: Dict[str, Dict[str, float]]
    p_values: Dict[str, float]
    effect_sizes: Dict[str, float]
    avg_response_time: float
    response_time_std: float
    response_time_ci: Tuple[float, float]
    error_rate: float
    hallucination_rate: float
    confidence_score_distribution: Dict[str, float]
    per_class_metrics: Dict[str, Dict[str, float]]
    confusion_matrix: np.ndarray
    cv_scores: Dict[str, List[float]]
    cv_mean: Dict[str, float]
    cv_std: Dict[str, float]


class EnhancedAnalyzerEvaluator:
    def __init__(self, random_state: int = 42):
        self.expected_categories = {
            'Database', 'Memory', 'Security', 'Network', 'CPU', 'Application', 'Infrastructure'
        }
        self.expected_severities = {
            'Critical', 'High', 'Medium', 'Low'
        }
        self.expected_contexts = {
            'kubernetes', 'database', 'infrastructure', 'application', 'security'
        }
        self.results = []
        self.ground_truth = {}
        self.random_state = random_state

    def bootstrap_confidence_interval(self, data: List[float], confidence: float = 0.95, n_bootstrap: int = 1000) -> Tuple[float, float]:
        if not data:
            return (0.0, 0.0)
        rng = np.random.default_rng(self.random_state)
        samples = [np.mean(rng.choice(data, size=len(data), replace=True)) for _ in range(n_bootstrap)]
        alpha = 1 - confidence
        return (float(np.percentile(samples, (alpha/2) * 100)), float(np.percentile(samples, (1 - alpha/2) * 100)))

    def cross_validate_analyzer(self, analyzer, test_logs: List[str], ground_truth: Dict[str, Any], cv_folds: int = 5) -> Dict[str, List[float]]:
        X = list(range(len(test_logs)))
        y_context = [ground_truth.get(log, {}).get('context', 'unknown') for log in test_logs]
        le_context = LabelEncoder()
        try:
            y_context_encoded = le_context.fit_transform(y_context)
        except ValueError:
            return {'context_accuracy': [], 'severity_accuracy': [], 'context_f1': [], 'severity_f1': [], 'response_times': []}

        cv_results = {
            'context_accuracy': [],
            'severity_accuracy': [],
            'context_f1': [],
            'severity_f1': [],
            'response_times': []
        }

        skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=self.random_state)
        for _, test_idx in skf.split(X, y_context_encoded):
            test_logs_fold = [test_logs[i] for i in test_idx]
            true_context_fold = [y_context[i] for i in test_idx]
            pred_context_fold: List[str] = []
            pred_severity_fold: List[str] = []
            fold_response_times: List[float] = []

            for log in test_logs_fold:
                start_time = time.time()
                try:
                    analysis = analyzer.analyze_chunk([log])
                    fold_response_times.append(time.time() - start_time)
                    pred_context_fold.append(analysis.get('context', 'unknown') if analysis else 'unknown')
                    pred_severity_fold.append(analysis.get('severity', 'unknown') if analysis else 'unknown')
                except Exception:
                    pred_context_fold.append('unknown')
                    pred_severity_fold.append('unknown')
                    fold_response_times.append(0.0)

            context_acc = accuracy_score(true_context_fold, pred_context_fold)
            try:
                context_f1 = f1_score(true_context_fold, pred_context_fold, average='weighted', zero_division=0)
            except Exception:
                context_f1 = 0.0
            cv_results['context_accuracy'].append(float(context_acc))
            cv_results['context_f1'].append(float(context_f1))
            cv_results['response_times'].extend([float(x) for x in fold_response_times])

        return cv_results

    def analyze_error_patterns(self, true_labels: List[str], predictions: List[str]) -> Dict[str, Any]:
        unique_labels = list(set(true_labels + predictions))
        misclass_matrix: Dict[str, Dict[str, int]] = {t: {p: 0 for p in unique_labels} for t in unique_labels}
        for t, p in zip(true_labels, predictions):
            misclass_matrix[t][p] += 1
        error_rates_by_class: Dict[str, float] = {}
        for label in unique_labels:
            true_count = true_labels.count(label)
            if true_count:
                correct = misclass_matrix[label].get(label, 0)
                error_rates_by_class[label] = 1 - (correct / true_count)
        error_pairs = [(t, p) for t, p in zip(true_labels, predictions) if t != p]
        common_errors = Counter(error_pairs).most_common(5)
        return {
            'misclassification_matrix': misclass_matrix,
            'error_rates_by_class': error_rates_by_class,
            'common_errors': common_errors
        }

    def _detect_hallucination(self, analysis: Dict[str, Any]) -> bool:
        if not analysis:
            return True
        category = analysis.get('category', 'Unknown')
        if category not in self.expected_categories and category != 'Unknown':
            return True
        severity = analysis.get('severity', 'Unknown')
        if severity not in self.expected_severities and severity != 'Unknown':
            return True
        context = analysis.get('context', '').lower()
        if context and context not in self.expected_contexts:
            return True
        confidence = analysis.get('confidence_score', 0.5)
        if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
            return True
        return False

    def comprehensive_evaluation(self, analyzer, test_logs: List[str], ground_truth: Dict[str, Any]) -> EnhancedMetrics:
        predictions: List[Dict[str, Any]] = []
        true_labels: List[Dict[str, Any]] = []
        response_times: List[float] = []
        confidence_scores: List[float] = []

        for log in test_logs:
            start_time = time.time()
            try:
                analysis = analyzer.analyze_chunk([log])
                response_times.append(time.time() - start_time)
                truth = ground_truth.get(log, {})
                predictions.append(analysis or {'context': 'unknown', 'category': 'unknown', 'severity': 'unknown', 'confidence_score': 0.0})
                true_labels.append(truth)
                confidence_scores.append((analysis or {}).get('confidence_score', 0.5))
            except Exception:
                response_times.append(0.0)
                predictions.append({'context': 'unknown', 'category': 'unknown', 'severity': 'unknown', 'confidence_score': 0.0})
                true_labels.append(ground_truth.get(log, {}))
                confidence_scores.append(0.0)

        pred_categories = [p.get('category', 'unknown') for p in predictions]
        true_categories = [t.get('category', 'unknown') for t in true_labels]
        pred_contexts = [p.get('context', 'unknown') for p in predictions]
        true_contexts = [t.get('context', 'unknown') for t in true_labels]
        pred_severities = [p.get('severity', 'unknown') for p in predictions]
        true_severities = [t.get('severity', 'unknown') for t in true_labels]

        category_accuracy = float(accuracy_score(true_categories, pred_categories))
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            category_precision, category_recall, category_f1, _ = precision_recall_fscore_support(
                true_categories, pred_categories, average=None, zero_division=0, labels=list(self.expected_categories)
            )
            macro_f1 = float(f1_score(true_categories, pred_categories, average='macro', zero_division=0))
            micro_f1 = float(f1_score(true_categories, pred_categories, average='micro', zero_division=0))
            weighted_f1 = float(f1_score(true_categories, pred_categories, average='weighted', zero_division=0))

        accuracy_scores = [1.0 if t == p else 0.0 for t, p in zip(true_categories, pred_categories)]
        accuracy_ci = self.bootstrap_confidence_interval(accuracy_scores)
        response_time_ci = self.bootstrap_confidence_interval(response_times)

        try:
            kappa_category = float(cohen_kappa_score(true_categories, pred_categories))
        except Exception:
            kappa_category = 0.0
        try:
            mcc_category = float(matthews_corrcoef(
                [1 if c in self.expected_categories else 0 for c in true_categories],
                [1 if c in self.expected_categories else 0 for c in pred_categories]
            ))
        except Exception:
            mcc_category = 0.0

        cv_results = self.cross_validate_analyzer(analyzer, test_logs, ground_truth)

        hallucinations = sum(1 for p in predictions if self._detect_hallucination(p))
        hallucination_rate = float(hallucinations / len(predictions)) if predictions else 0.0

        metrics = EnhancedMetrics(
            accuracy=category_accuracy,
            balanced_accuracy=category_accuracy,
            precision={cat: float(val) for cat, val in zip(self.expected_categories, category_precision)},
            recall={cat: float(val) for cat, val in zip(self.expected_categories, category_recall)},
            f1_score={cat: float(val) for cat, val in zip(self.expected_categories, category_f1)},
            macro_f1=macro_f1,
            micro_f1=micro_f1,
            weighted_f1=weighted_f1,
            cohen_kappa=kappa_category,
            matthews_corrcoef=mcc_category,
            confidence_intervals={'accuracy': {'lower': accuracy_ci[0], 'upper': accuracy_ci[1]}, 'response_time': {'lower': response_time_ci[0], 'upper': response_time_ci[1]}},
            p_values={},
            effect_sizes={},
            avg_response_time=float(np.mean(response_times) if response_times else 0.0),
            response_time_std=float(np.std(response_times) if response_times else 0.0),
            response_time_ci=response_time_ci,
            error_rate=float(1 - category_accuracy),
            hallucination_rate=hallucination_rate,
            confidence_score_distribution={'mean': float(np.mean(confidence_scores)), 'std': float(np.std(confidence_scores)), 'median': float(np.median(confidence_scores))},
            per_class_metrics={'context': {'accuracy': float(accuracy_score(true_contexts, pred_contexts))}, 'category': {'accuracy': category_accuracy}, 'severity': {'accuracy': float(accuracy_score(true_severities, pred_severities))}},
            confusion_matrix=confusion_matrix(true_categories, pred_categories, labels=list(self.expected_categories)),
            cv_scores=cv_results,
            cv_mean={k: float(np.mean(v)) if v else 0.0 for k, v in cv_results.items()},
            cv_std={k: float(np.std(v)) if v else 0.0 for k, v in cv_results.items()}
        )

        return metrics




