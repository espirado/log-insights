# src/analyzers/stream_analyzer.py
from typing import Generator, Dict, Any
import time
from dotenv import load_dotenv
from collections import defaultdict
import os
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .llm import ContextAwareLLMAnalyzer

class LogStreamAnalyzer(FileSystemEventHandler):
    def __init__(self, log_path: str, buffer_size: int = 5):
        load_dotenv()
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key not found in environment variables")
            
        self.analyzer = ContextAwareLLMAnalyzer(api_key=api_key)
        self.log_path = log_path
        self.last_position = 0
        self.buffer = []
        self.buffer_size = buffer_size
        self.metrics = defaultdict(int)

    async def start_monitoring(self):
        observer = Observer()
        observer.schedule(self, self.log_path, recursive=False)
        observer.start()
        print(f"Started monitoring {self.log_path}")

        try:
            while True:
                if len(self.buffer) >= self.buffer_size:
                    await self.process_buffer()
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            self._print_summary()
        observer.join()

    def on_modified(self, event):
        if event.src_path == self.log_path:
            with open(self.log_path, 'r') as f:
                f.seek(self.last_position)
                new_logs = [log.strip() for log in f.readlines() if log.strip()]
                self.last_position = f.tell()
                self.buffer.extend(new_logs)

    async def process_buffer(self):
        if not self.buffer:
            return

        start_time = time.time()
        logs_to_process = self.buffer[:self.buffer_size]
        self.buffer = self.buffer[self.buffer_size:]

        analysis = self.analyzer.analyze_chunk(logs_to_process)
        process_time = time.time() - start_time

        await self._handle_analysis_result(analysis, logs_to_process, process_time)
        self.metrics['processed'] += len(logs_to_process)

    async def _handle_analysis_result(self, analysis: Dict[str, Any], logs: list, process_time: float):
        if analysis:
            self.metrics['issues_found'][analysis.get('category', 'Unknown')] += 1
            
            print(f"\nAnalysis Result ({process_time:.2f}s):")
            print(f"Logs Processed: {len(logs)}")
            print(f"Category: {analysis.get('category')}")
            print(f"Severity: {analysis.get('severity')}")
            print(f"Root Cause: {analysis.get('root_cause')}")
            print(f"Remediation: {analysis.get('remediation')}")
            
            if analysis.get('severity') == 'Critical':
                await self._handle_critical_issue(analysis)
            
            print("-" * 50)

    async def _handle_critical_issue(self, analysis: Dict[str, Any]):
        """Handle critical severity issues"""
        print("\n⚠️ CRITICAL ISSUE DETECTED!")
        print(f"Category: {analysis.get('category')}")
        print(f"Root Cause: {analysis.get('root_cause')}")
        print(f"Immediate Action Required: {analysis.get('remediation')}")
        # Add alerting logic here

    def _print_summary(self):
        """Print analysis summary on exit"""
        runtime = time.time() - self.metrics['start_time']
        print("\nAnalysis Summary:")
        print(f"Runtime: {runtime:.2f}s")
        print(f"Logs Processed: {self.metrics['processed']}")
        print("\nIssues by Category:")
        for category, count in self.metrics['issues_found'].items():
            print(f"{category}: {count}")

async def main():
    # Create log directory if it doesn't exist
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Set log file path
    log_path = os.path.join(log_dir, "app.log")
    
    # Create file if it doesn't exist
    if not os.path.exists(log_path):
        open(log_path, 'a').close()
    
    # Initialize and start analyzer
    stream_analyzer = LogStreamAnalyzer(log_path=log_path)
    print(f"Starting log analysis on: {log_path}")
    await stream_analyzer.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())