
import os
from dotenv import load_dotenv
from src.analyzers.llm import ContextAwareLLMAnalyzer
from src.visualization.charts import ChartGenerator
from datetime import datetime

def create_sample_logs(filename: str):
    """Create a file with sample logs"""
    logs = [
    "[ERROR] [2024-11-21T10:01:00Z] EC2 instance 'i-0123456789abcdef0' terminated unexpectedly: InstanceLimitExceeded.",
    "[DEBUG] [2024-11-21T10:01:01Z] Validating deployment configuration for Kubernetes cluster 'prod-cluster'.",
    "[WARNING] [2024-11-21T10:01:02Z] IAM role 'ReadOnlyAccess' used in high-privilege context.",
    "[INFO]  [2024-11-21T10:01:03Z] Cloud Function 'process-data' executed successfully in 250ms.",
    "[ERROR] [2024-11-21T10:01:04Z] Failed to connect to PostgreSQL database: Connection timeout.",
    "[DEBUG] [2024-11-21T10:01:05Z] Autoscaler evaluated workload distribution for Cloud Run service 'web-service'.",
    "[WARNING] [2024-11-21T10:01:06Z] High memory usage detected in pod 'analytics-worker' (95%).",
    "[INFO]  [2024-11-21T10:01:07Z] Database backup for 'customer-db' completed successfully.",
    "[ERROR] [2024-11-21T10:01:08Z] Cloud Run service 'payment-service' failed to start: HTTP 502.",
    "[DEBUG] [2024-11-21T10:01:09Z] Fetching metrics for EC2 Auto Scaling group 'web-app-asg'.",
    "[WARNING] [2024-11-21T10:01:10Z] Kubernetes node 'kube-node-2' nearing maximum pod capacity.",
    "[INFO]  [2024-11-21T10:01:11Z] IAM policy 'FullAccess' attached to user 'admin-user'.",
    "[ERROR] [2024-11-21T10:01:12Z] Pod 'backend-1' CrashLoopBackOff detected in namespace 'default'.",
    "[DEBUG] [2024-11-21T10:01:13Z] Request latency for Cloud Function 'get-user-data' measured at 120ms.",
    "[WARNING] [2024-11-21T10:01:14Z] PostgreSQL replication lag detected on 'db-replica-1' (10 seconds).",
    "[INFO]  [2024-11-21T10:01:15Z] Deployment 'frontend-app' scaled to 10 replicas in Kubernetes.",
    "[ERROR] [2024-11-21T10:01:16Z] CloudWatch alarm triggered for EC2 instance 'i-0abcdef1234567890'.",
    "[DEBUG] [2024-11-21T10:01:17Z] Investigating Kubernetes pod eviction policies in namespace 'monitoring'.",
    "[WARNING] [2024-11-21T10:01:18Z] Excessive API calls detected to IAM service from IP 192.168.0.1.",
    "[INFO]  [2024-11-21T10:01:19Z] New revision 'rev-002' deployed for Cloud Run service 'data-service'."
]

    
    with open(filename, 'w') as f:
        for log in logs:
            f.write(log + '\n')

def read_logs(filename: str):
    """Read logs from file"""
    with open(filename, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def main():
    # Load environment variables
    load_dotenv()
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OpenAI API key not found in environment variables")

    # Create sample logs file
    log_file = 'generated_logs.txt'
    create_sample_logs(log_file)
    
    print("Starting test...")
    
    try:
        # Read logs
        logs = read_logs(log_file)
        print(f"\nRead {len(logs)} logs from file")
        
        # Initialize components
        print("\nInitializing analyzer and chart generator...")
        analyzer = ContextAwareLLMAnalyzer(api_key=api_key)
        chart_generator = ChartGenerator()
        
        # Process logs
        print("\nProcessing logs...")
        chunk_size = 3
        for i in range(0, len(logs), chunk_size):
            chunk = logs[i:i+chunk_size]
            print("\nProcessing chunk:", chunk)
            
            analysis = analyzer.analyze_chunk(chunk)
            print("\nAnalysis result:")
            print(f"Context: {analysis.get('context')}")
            print(f"Category: {analysis.get('category')}")
            print(f"Severity: {analysis.get('severity')}")
            print(f"Root cause: {analysis.get('root_cause')}")
            print(f"Remediation: {analysis.get('remediation')}")
            print("-" * 50)
        
        # Get final results
        final_results = analyzer.get_results()
        print("\nFinal Statistics:")
        print(f"Issues by Context: {final_results['results']['issues']}")
        print(f"Severity Distribution: {final_results['results']['severities']}")
        
        # Generate visualization
        print("\nGenerating visualization dashboard...")
        chart_generator.create_dashboard(
            final_results,
            'log_analysis_dashboard.html'
        )
        print("✓ Dashboard saved to log_analysis_dashboard.html")
        
    except Exception as e:
        print(f"\nError during execution: {str(e)}")
        import traceback
        print(traceback.format_exc())
    
    finally:
        # Cleanup
        if os.path.exists(log_file):
            os.remove(log_file)
            print("\nCleanup completed")

if __name__ == "__main__":
    main()