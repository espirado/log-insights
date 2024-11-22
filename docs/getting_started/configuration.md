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