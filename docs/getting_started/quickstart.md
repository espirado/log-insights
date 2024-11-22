## Quick Start Guide

### Basic Usage
```python
from src.analyzers.llm import LLMAnalyzer
from src.data.log_parser import LogParser

# Initialize
parser = LogParser()
analyzer = LLMAnalyzer(api_key="your-api-key")

# Analyze a log file
results = []
for log_chunk in parser.parse_file("example.log"):
    analysis = analyzer.analyze_chunk(log_chunk)
    results.append(analysis)

# Print results
print(analyzer.get_results())
```

### Supported Log Formats
- Standard datetime formats (YYYY-MM-DD HH:MM:SS)
- ISO 8601 timestamps
- Common log levels (ERROR, WARNING, INFO, DEBUG, CRITICAL)
- Multi-line log entries

### Configuration Options
- Chunk size for batch processing
- LLM model selection
- Analysis sensitivity
- Visualization preferences