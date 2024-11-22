# src/evaluation/analyzer_evaluator.py
from typing import List, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime
import json
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from sklearn.exceptions import UndefinedMetricWarning  
import time
from dataclasses import dataclass
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings

@dataclass
class AnalysisMetrics:
    accuracy: float
    precision: Dict[str, float]
    recall: Dict[str, float]
    f1_score: Dict[str, float]
    avg_response_time: float
    error_rate: float
    hallucination_rate: float
    categorization_accuracy: float
    severity_accuracy: float
    confusion_matrix: np.ndarray

class AnalyzerEvaluator:
    def __init__(self):
        self.expected_categories = {
            'Database', 'Memory', 'Security', 'Network', 'CPU', 'Application'
        }
        self.expected_severities = {
            'Critical', 'High', 'Medium', 'Low'
        }
        self.expected_contexts = {
            'kubernetes', 'database', 'infrastructure', 'application', 'security'
        }
        self.results = []
        self.ground_truth = {}

    def _is_valid_root_cause(self, root_cause: str) -> bool:
        """
        Validate if root cause explanation is reasonable
        
        Args:
            root_cause: The root cause explanation to validate
            
        Returns:
            bool: True if root cause is valid, False otherwise
        """
        if not isinstance(root_cause, str):
            return False
        
        # Check minimum length (arbitrary threshold)
        if not root_cause or len(root_cause.strip()) < 10:
            return False
            
        # Check for common technical terms (can be expanded)
        technical_terms = {
            'memory', 'cpu', 'disk', 'network', 'database', 'error',
            'failed', 'timeout', 'connection', 'limit', 'exceeded',
            'crash', 'overflow', 'leak', 'full', 'unavailable'
        }
        
        has_technical_term = any(term in root_cause.lower() for term in technical_terms)
        
        # Check basic structure
        has_proper_structure = (
            len(root_cause.split()) >= 3  # At least 3 words
            and any(char.isupper() for char in root_cause)  # Contains some capitalization
            and '.' in root_cause  # Contains proper punctuation
        )
        
        return has_technical_term and has_proper_structure


    def evaluate_analysis(self, 
                        analyzer,
                        test_logs: List[str],
                        ground_truth: Dict[str, Any]) -> AnalysisMetrics:
        """
        Evaluate the analyzer's performance against ground truth
        """
        evaluation_start = time.time()
        total_response_time = 0
        correct_categories = 0
        correct_severities = 0
        hallucinations = 0
        errors = 0
        
        predictions = []
        true_labels = []
        
        # Suppress sklearn warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UndefinedMetricWarning)
            
            for i, log_chunk in enumerate(test_logs):
                try:
                    start_time = time.time()
                    analysis = analyzer.analyze_chunk([log_chunk])
                    response_time = time.time() - start_time
                    total_response_time += response_time
                    
                    truth = ground_truth.get(log_chunk, {})
                    
                    if analysis:
                        category = analysis.get('category', 'Unknown')
                        if category in self.expected_categories:
                            predictions.append(category)
                            true_labels.append(truth.get('category', 'Unknown'))
                            
                            if category == truth.get('category'):
                                correct_categories += 1
                            
                            if analysis.get('severity') == truth.get('severity'):
                                correct_severities += 1
                        
                        if self._detect_hallucination(analysis, truth):
                            hallucinations += 1
                        
                        self.results.append({
                            'log_entry': log_chunk,
                            'predicted_category': category,
                            'true_category': truth.get('category'),
                            'predicted_severity': analysis.get('severity'),
                            'true_severity': truth.get('severity'),
                            'response_time': response_time,
                            'is_correct': category == truth.get('category'),
                            'has_hallucination': self._detect_hallucination(analysis, truth)
                        })
                    
                except Exception as e:
                    errors += 1
                    print(f"Error analyzing chunk {i}: {str(e)}")
            
            # Calculate metrics only if we have predictions
            total_logs = len(test_logs)
            if predictions and true_labels:
                conf_matrix = confusion_matrix(
                    true_labels, 
                    predictions, 
                    labels=list(self.expected_categories)
                )
                
                precision, recall, f1, _ = precision_recall_fscore_support(
                    true_labels,
                    predictions,
                    labels=list(self.expected_categories),
                    zero_division=0
                )
                
                precision_dict = dict(zip(self.expected_categories, precision))
                recall_dict = dict(zip(self.expected_categories, recall))
                f1_dict = dict(zip(self.expected_categories, f1))
                
            else:
                conf_matrix = np.zeros((len(self.expected_categories), len(self.expected_categories)))
                precision_dict = {cat: 0.0 for cat in self.expected_categories}
                recall_dict = {cat: 0.0 for cat in self.expected_categories}
                f1_dict = {cat: 0.0 for cat in self.expected_categories}
            
            metrics = AnalysisMetrics(
                accuracy=accuracy_score(true_labels, predictions) if predictions else 0.0,
                precision=precision_dict,
                recall=recall_dict,
                f1_score=f1_dict,
                avg_response_time=total_response_time / total_logs if total_logs > 0 else 0.0,
                error_rate=errors / total_logs if total_logs > 0 else 0.0,
                hallucination_rate=hallucinations / total_logs if total_logs > 0 else 0.0,
                categorization_accuracy=correct_categories / total_logs if total_logs > 0 else 0.0,
                severity_accuracy=correct_severities / total_logs if total_logs > 0 else 0.0,
                confusion_matrix=conf_matrix
            )
            
            return metrics

    def _detect_hallucination(self, analysis: Dict[str, Any], truth: Dict[str, Any]) -> bool:
        """
        Detect if the analysis contains hallucinated information
        
        Args:
            analysis: Analysis results from the model
            truth: Ground truth data
            
        Returns:
            bool: True if hallucination detected, False otherwise
        """
        if not analysis:
            return True
            
        # Check category
        category = analysis.get('category', 'Unknown')
        if category not in self.expected_categories:
            return True
        
        # Check severity
        severity = analysis.get('severity', 'Unknown')
        if severity not in self.expected_severities:
            return True
        
        # Check context
        context = analysis.get('context', '').lower()
        if context and context not in self.expected_contexts:
            return True
        
        # Check root cause
        root_cause = analysis.get('root_cause', '')
        if not self._is_valid_root_cause(root_cause):
            return True
        
        # Check timestamp format
        timestamp = analysis.get('timestamp', '')
        try:
            if timestamp:
                datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return True
        
        return False
    def _calculate_metrics(self, true_labels: List[str], predictions: List[str]) -> tuple:
        """
        Calculate precision, recall, and f1 scores
        
        Args:
            true_labels: List of true category labels
            predictions: List of predicted category labels
            
        Returns:
            tuple: (precision, recall, f1) dictionaries
        """
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            try:
                precision, recall, f1, _ = precision_recall_fscore_support(
                    true_labels,
                    predictions,
                    labels=list(self.expected_categories),
                    zero_division=0
                )
                
                return (
                    dict(zip(self.expected_categories, precision)),
                    dict(zip(self.expected_categories, recall)),
                    dict(zip(self.expected_categories, f1))
                )
            except:
                return (
                    {cat: 0.0 for cat in self.expected_categories},
                    {cat: 0.0 for cat in self.expected_categories},
                    {cat: 0.0 for cat in self.expected_categories}
                )
            

    def generate_evaluation_report(self, metrics: AnalysisMetrics, output_file: str = 'evaluation_report.html'):
        # Create subplots
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                'Category-wise Metrics',
                'Response Time Distribution',
                'Confusion Matrix',
                'Error Analysis',
                'Category Distribution',
                'Severity Distribution'
            ),
            specs=[
                [{"type": "bar"}, {"type": "histogram"}],
                [{"type": "heatmap"}, {"type": "bar"}],
                [{"type": "pie"}, {"type": "pie"}]
            ]
        )

        # Category-wise metrics
        categories = list(metrics.precision.keys())
        fig.add_trace(
            go.Bar(
                x=categories,
                y=[metrics.precision[cat] for cat in categories],
                name='Precision',
                marker_color='blue'
            ),
            row=1, col=1
        )
        fig.add_trace(
            go.Bar(
                x=categories,
                y=[metrics.recall[cat] for cat in categories],
                name='Recall',
                marker_color='green'
            ),
            row=1, col=1
        )

        # Response time distribution
        response_times = [result['response_time'] for result in self.results]
        fig.add_trace(
            go.Histogram(
                x=response_times,
                name='Response Time',
                nbinsx=20,
                marker_color='purple'
            ),
            row=1, col=2
        )

        # Confusion matrix
        fig.add_trace(
            go.Heatmap(
                z=metrics.confusion_matrix,
                x=list(self.expected_categories),
                y=list(self.expected_categories),
                colorscale='Blues',
                showscale=True
            ),
            row=2, col=1
        )

        # Error analysis
        error_metrics = {
            'Accuracy': metrics.accuracy,
            'Error Rate': metrics.error_rate,
            'Hallucination Rate': metrics.hallucination_rate
        }
        fig.add_trace(
            go.Bar(
                x=list(error_metrics.keys()),
                y=list(error_metrics.values()),
                name='Error Metrics',
                marker_color='red'
            ),
            row=2, col=2
        )

        # Category distribution
        category_counts = pd.DataFrame(self.results)['predicted_category'].value_counts()
        fig.add_trace(
            go.Pie(
                labels=category_counts.index,
                values=category_counts.values,
                name="Categories"
            ),
            row=3, col=1
        )

        # Severity distribution
        severity_counts = pd.DataFrame(self.results)['predicted_severity'].value_counts()
        fig.add_trace(
            go.Pie(
                labels=severity_counts.index,
                values=severity_counts.values,
                name="Severities"
            ),
            row=3, col=2
        )

        # Update layout
        fig.update_layout(
            height=1200,
            showlegend=True,
            title_text="Log Analysis Evaluation Report"
        )

        # Save to HTML
        fig.write_html(output_file)
        print(f"Report generated successfully and saved to {output_file}")