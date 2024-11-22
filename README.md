# Log Insight - AI-Powered Log Analysis

An intelligent log analysis tool that uses LLMs to provide deep insights into system logs.

## Features

- AI-powered log analysis using OpenAI's GPT models
- Identification of issues, patterns, and anomalies
- Root cause analysis and remediation suggestions
- Real-time visualization of log patterns
- Support for various log formats

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/log-insight.git
cd log-insight
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and add your OpenAI API key:
```bash
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=your_key_here
```

## Usage

Basic usage:
```python
from src.analyzers.llm import LLMAnalyzer
from src.data.log_parser import LogParser

# Initialize components
parser = LogParser(chunk_size=10)
analyzer = LLMAnalyzer(api_key="your-api-key")

# Analyze logs
for log_chunk in parser.parse_file("path/to/logs.txt"):
    analysis = analyzer.analyze_chunk(log_chunk)
    print(analysis)
```

## Project Structure

```
log-insight/
├── src/
│   ├── analyzers/      # Log analysis implementations
│   ├── visualization/  # Data visualization
│   ├── data/          # Log parsing and data handling
│   └── utils/         # Helper utilities
└── tests/             # Test cases
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.