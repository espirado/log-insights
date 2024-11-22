# src/data/log_parser.py
from typing import List, Generator
import re
from datetime import datetime

class LogParser:
    def __init__(self, chunk_size: int = 10):
        self.chunk_size = chunk_size
        self.timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}',  # 2024-02-20 15:30:45
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',   # 2024-02-20T15:30:45
            r'\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}'    # Feb 20 15:30:45
        ]

    def parse_file(self, filepath: str) -> Generator[List[str], None, None]:
        """
        Parse log file and yield chunks of logs
        """
        current_chunk = []
        
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line:  # Skip empty lines
                    current_chunk.append(line)
                    if len(current_chunk) >= self.chunk_size:
                        yield current_chunk
                        current_chunk = []
            
            if current_chunk:  # Yield remaining logs
                yield current_chunk

    def parse_line(self, line: str) -> dict:
        """
        Parse a single log line into components
        """
        # Extract timestamp
        timestamp = None
        for pattern in self.timestamp_patterns:
            match = re.search(pattern, line)
            if match:
                timestamp = match.group()
                break
        
        # Extract log level
        level_match = re.search(r'ERROR|WARNING|INFO|DEBUG|CRITICAL', line)
        level = level_match.group() if level_match else 'UNKNOWN'
        
        # Extract message (everything after timestamp and level)
        message = line
        if timestamp:
            message = message.replace(timestamp, '', 1)
        if level_match:
            message = message.replace(level, '', 1)
        message = message.strip()
        
        return {
            'timestamp': timestamp,
            'level': level,
            'message': message
        }

    def is_valid_log(self, line: str) -> bool:
        """
        Check if a line contains a valid log entry
        """
        return any(re.search(pattern, line) for pattern in self.timestamp_patterns)