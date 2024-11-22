# test_evaluation.py
from typing import List, Dict, Any
from src.evaluation.analyzer_evaluator import AnalyzerEvaluator
from src.data.log_generator import LogGenerator
from src.analyzers.llm import ContextAwareLLMAnalyzer
import os
from dotenv import load_dotenv
from datetime import datetime
import json

def generate_enhanced_ground_truth(logs: List[str]) -> Dict[str, Any]:
    """Generate comprehensive ground truth data for test logs"""
    truth = {}
    for log in logs:
        # Determine primary context and category
        if 'database' in log.lower() or 'postgresql' in log.lower():
            context = 'database'
            category = 'Database'
            severity = 'Critical' if any(term in log.lower() for term in ['error', 'failed', 'timeout']) else 'High'
            component = 'Database Service'
        elif 'memory' in log.lower():
            context = 'infrastructure'
            category = 'Memory'
            severity = 'Critical' if 'out of memory' in log.lower() else 'High'
            component = 'Application Memory'
        elif 'security' in log.lower() or 'breach' in log.lower():
            context = 'security'
            category = 'Security'
            severity = 'Critical' if 'breach' in log.lower() else 'High'
            component = 'Security System'
        elif any(k8s_term in log.lower() for k8s_term in ['pod', 'node', 'container']):
            context = 'kubernetes'
            category = 'Application'
            severity = 'High'
            component = 'Kubernetes Cluster'
        else:
            context = 'application'
            category = 'Application'
            severity = 'Medium'
            component = 'Application Service'

        # Generate root cause based on context
        root_causes = {
            'database': 'Database connection failure due to connection pool exhaustion.',
            'memory': 'Memory usage exceeded allocated limits causing performance degradation.',
            'security': 'Unauthorized access attempt detected from external IP.',
            'kubernetes': 'Pod resource limits reached causing container termination.',
            'application': 'Application service experiencing high latency.'
        }

        truth[log] = {
            'context': context,
            'category': category,
            'severity': severity,
            'component': component,
            'root_cause': root_causes.get(context, 'Unknown issue detected.'),
            'timestamp': log.split()[0] if ' ' in log else datetime.now().isoformat()
        }
    
    return truth

def save_results(metrics, filename: str = 'evaluation_results.json'):
    """Save comprehensive evaluation results"""
    results = {
        'accuracy_metrics': {
            'overall_accuracy': metrics.accuracy,
            'categorization_accuracy': metrics.categorization_accuracy,
            'severity_accuracy': metrics.severity_accuracy
        },
        'performance_metrics': {
            'avg_response_time': metrics.avg_response_time,
            'error_rate': metrics.error_rate,
            'hallucination_rate': metrics.hallucination_rate
        },
        'detailed_metrics': {
            'precision': metrics.precision,
            'recall': metrics.recall,
            'f1_score': metrics.f1_score
        },
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'evaluation_date': datetime.now().strftime('%Y-%m-%d')
        }
    }
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)

def main():
    # Load environment variables
    load_dotenv()
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OpenAI API key not found in environment variables")
    
    print("Starting evaluation process...")
    
    try:
        # Generate test logs
        print("\nGenerating test logs...")
        generator = LogGenerator()
        test_logs = generator.generate_logs(num_entries=20)
        print(f"Generated {len(test_logs)} test logs")
        
        # Generate ground truth
        print("\nGenerating ground truth...")
        ground_truth = generate_enhanced_ground_truth(test_logs)
        
        # Initialize components
        print("\nInitializing analyzer and evaluator...")
        analyzer = ContextAwareLLMAnalyzer(api_key=api_key)
        evaluator = AnalyzerEvaluator()
        
        # Run evaluation
        print("\nRunning evaluation...")
        metrics = evaluator.evaluate_analysis(analyzer, test_logs, ground_truth)
        
        # Print detailed results
        print("\nEvaluation Results:")
        print(f"Overall Accuracy: {metrics.accuracy:.2%}")
        print(f"Average Response Time: {metrics.avg_response_time:.3f}s")
        print(f"Error Rate: {metrics.error_rate:.2%}")
        print(f"Hallucination Rate: {metrics.hallucination_rate:.2%}")
        
        print("\nCategory-wise Metrics:")
        for category in evaluator.expected_categories:
            print(f"\n{category}:")
            print(f"  Precision: {metrics.precision[category]:.2%}")
            print(f"  Recall: {metrics.recall[category]:.2%}")
            print(f"  F1 Score: {metrics.f1_score[category]:.2%}")
        
        # Save results and generate report
        print("\nSaving results and generating report...")
        save_results(metrics)
        evaluator.generate_evaluation_report(metrics, 'evaluation_report.html')
        print("✓ Evaluation report saved to 'evaluation_report.html'")
        print("✓ Results saved to 'evaluation_results.json'")
        
    except Exception as e:
        print(f"\nError during evaluation: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()