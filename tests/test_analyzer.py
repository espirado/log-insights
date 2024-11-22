# tests/test_analyzers.py
import pytest
from src.analyzers.llm import LLMAnalyzer
from src.data.log_parser import LogParser
from datetime import datetime
import os

@pytest.fixture
def sample_logs():
    return [
        "2024-02-20 10:15:30 ERROR Database connection timeout",
        "2024-02-20 10:15:35 WARNING High memory usage: 90%",
        "2024-02-20 10:15:40 ERROR Maximum retry attempts reached"
    ]

@pytest.fixture
def mock_openai_response():
    return {
        "category": "Database",
        "severity": "High",
        "root_cause": "Connection timeout",
        "remediation": "Check database connectivity",
        "timestamp": "2024-02-20 10:15:30"
    }

def test_log_parser(sample_logs):
    parser = LogParser()
    parsed = parser.parse_line(sample_logs[0])
    assert parsed['timestamp'] == "2024-02-20 10:15:30"
    assert parsed['level'] == "ERROR"
    assert "Database connection timeout" in parsed['message']

def test_llm_analyzer(sample_logs, mock_openai_response, monkeypatch):
    def mock_openai_completion(*args, **kwargs):
        class MockResponse:
            def __init__(self):
                self.choices = [type('Choices', (), {
                    'message': type('Message', (), {
                        'content': str(mock_openai_response)
                    })
                })]
        return MockResponse()
    
    monkeypatch.setattr("openai.OpenAI.chat.completions.create", mock_openai_completion)
    
    analyzer = LLMAnalyzer("mock-api-key")
    result = analyzer.analyze_chunk(sample_logs)
    
    assert result['category'] == "Database"
    assert result['severity'] == "High"
    assert 'root_cause' in result
    assert 'remediation' in result

# tests/test_parser.py
def test_log_parser_file_reading(tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text("\n".join([
        "2024-02-20 10:15:30 ERROR Test error",
        "2024-02-20 10:15:35 WARNING Test warning"
    ]))
    
    parser = LogParser(chunk_size=1)
    chunks = list(parser.parse_file(str(log_file)))
    assert len(chunks) == 2
    assert "ERROR" in chunks[0][0]
    assert "WARNING" in chunks[1][0]

def test_log_parser_invalid_logs():
    parser = LogParser()
    assert not parser.is_valid_log("Invalid log line")
    assert parser.is_valid_log("2024-02-20 10:15:30 ERROR Valid log")

# tests/test_visualization.py
def test_chart_generator(sample_logs):
    from src.visualization.charts import ChartGenerator
    
    results = {
        'results': {
            'issues': {'Database': 2, 'Memory': 1},
            'severities': {'High': 2, 'Medium': 1},
            'timeline': [
                {
                    'timestamp': '2024-02-20 10:15:30',
                    'category': 'Database',
                    'severity': 'High',
                    'root_cause': 'Connection timeout',
                    'remediation': 'Check connectivity'
                }
            ]
        }
    }
    
    generator = ChartGenerator()
    fig = generator.create_dashboard(results)
    assert fig is not None