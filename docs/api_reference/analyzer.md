
## Analyzers

### BaseAnalyzer

Base class for all analyzers.

```python
class BaseAnalyzer:
    def analyze_chunk(self, logs: List[str]) -> Dict[str, Any]:
        """
        Analyze a chunk of logs
        
        Args:
            logs: List of log strings
            
        Returns:
            Dictionary containing analysis results
        """
        pass
```

### LLMAnalyzer

LLM-powered log analyzer.

```python
class LLMAnalyzer(BaseAnalyzer):
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        """
        Initialize LLM analyzer
        
        Args:
            api_key: OpenAI API key
            model: Model to use for analysis
        """
        pass
```