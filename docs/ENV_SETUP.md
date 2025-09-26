# Environment Setup

Create a `.env` file in the project root. Example values:

```dotenv
OPENAI_API_KEY=your-openai-key
ELASTIC_API_KEY=your-elastic-api-key
SPLUNK_USERNAME=your-splunk-username
SPLUNK_PASSWORD=your-splunk-password
RESULTS_ROOT=results
AWS_REGION=us-east-1
```

Never commit secrets. Use environment variables in CI/CD.

