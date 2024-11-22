# src/cli.py
import click
import os
from dotenv import load_dotenv
from src.analyzers.llm import LLMAnalyzer
from src.data.log_parser import LogParser
from src.visualization.charts import ChartGenerator
import json
from datetime import datetime

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
@click.option('--api-key', envvar='OPENAI_API_KEY', help='OpenAI API key')
def analyze(log_file, chunk_size, output, format, api_key):
    """Analyze log file and generate insights"""
    if not api_key:
        raise click.UsageError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or use --api-key")
    
    click.echo(f"Analyzing log file: {log_file}")
    
    # Initialize components
    parser = LogParser(chunk_size=chunk_size)
    analyzer = LLMAnalyzer(api_key=api_key)
    
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
        fig = generator.create_dashboard(results)
        fig.write_html(output)
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

if __name__ == '__main__':
    cli()