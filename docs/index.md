# Getting Started with Log Insight

## Installation Guide

### Prerequisites
- Python 3.8 or higher
- OpenAI API key
- pip package manager

### Step-by-Step Installation
1. Clone the repository:
```bash
git clone https://github.com/yourusername/log-insight.git
cd log-insight
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env file to add your OpenAI API key
```

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

## Configuration Guide

### Environment Variables
```plaintext
OPENAI_API_KEY=your-api-key
LOG_CHUNK_SIZE=10
DEFAULT_MODEL=gpt-3.5-turbo
```

### Custom Configuration
You can customize the analysis behavior by adjusting parameters:

```python
analyzer = LLMAnalyzer(
    api_key="your-api-key",
    model="gpt-3.5-turbo",
    chunk_size=20
)
```