from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime

class BaseAnalyzer(ABC):
    def __init__(self):
        self.processing_time = 0
        self.results = {
            'issues': {},
            'severities': {},
            'timeline': []
        }

    @abstractmethod
    def analyze_chunk(self, logs: List[str]) -> Dict[str, Any]:
        """Analyze a chunk of logs"""
        pass

    @abstractmethod
    def process_stream(self, log_stream: Any):
        """Process streaming logs"""
        pass

    def clear_results(self):
        """Reset analysis results"""
        self.results = {
            'issues': {},
            'severities': {},
            'timeline': []
        }
        self.processing_time = 0

    def get_results(self) -> Dict[str, Any]:
        """Return analysis results"""
        return {
            'results': self.results,
            'processing_time': self.processing_time
        }