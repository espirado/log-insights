# test_integration.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta
from src.data.log_parser import LogParser
from src.analyzers.llm import LLMAnalyzer
from src.visualization.charts import ChartGenerator

def generate_sample_logs(filename: str, num_entries: int = 10):
    """Generate sample logs for testing"""
    templates = [
        ("ERROR", "Database connection timeout after {} retries"),
        ("WARNING", "Memory usage at {}%"),
        ("ERROR", "Failed to process request. Response time: {}ms"),
        ("CRITICAL", "Security breach attempt from IP: {}")
    ]
    
    with open(filename, 'w') as f:
        start_time = datetime.now()
        for i in range(num_entries):
            timestamp = start_time + timedelta(minutes=i)
            level, template = templates[i % len(templates)]
            value = str(i*10) if 'Memory' in template else str(i+1)
            log_entry = f"{timestamp} {level} {template.format(value)}\n"
            f.write(log_entry)

def main():
    try:
        # Load environment variables
        load_dotenv()
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in .env file")

        print("Starting test...")
        
        # Generate test logs
        print("\nGenerating test logs...")
        generate_sample_logs('test_logs.txt')
        print("✓ Test logs generated")

        # Initialize components
        print("\nInitializing components...")
        parser = LogParser(chunk_size=3)
        analyzer = LLMAnalyzer(api_key=api_key)
        print("✓ Components initialized")

        # Process logs
        print("\nProcessing logs...")
        for log_chunk in parser.parse_file('test_logs.txt'):
            print("\nProcessing chunk:", log_chunk)
            analysis = analyzer.analyze_chunk(log_chunk)
            if analysis:
                print("\nAnalysis result:")
                print(f"Category: {analysis.get('category')}")
                print(f"Severity: {analysis.get('severity')}")
                print(f"Root cause: {analysis.get('root_cause')}")
                print(f"Remediation: {analysis.get('remediation')}")
                print("-" * 50)

        # Get final results
        final_results = analyzer.get_results()
        print("\nFinal Statistics:")
        print(f"Issues found: {final_results['results']['issues']}")
        print(f"Severity distribution: {final_results['results']['severities']}")

        # Generate visualization
        print("\nGenerating visualization dashboard...")
        chart_gen = ChartGenerator()
        chart_gen.create_dashboard(final_results, 'log_analysis_dashboard-2.html')
        print("✓ Dashboard saved to log_analysis_dashboard.html")
        
    except Exception as e:
        print(f"Error during execution: {str(e)}")
        import traceback
        print(traceback.format_exc())
    
    finally:
        # Cleanup
        if os.path.exists('test_logs.txt'):
            os.remove('test_logs.txt')
            print("\nCleanup completed")

if __name__ == "__main__":
    main()