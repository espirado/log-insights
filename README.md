# Log Insight - AI-Powered Log Analysis

An intelligent log analysis tool using LLMs for context-aware insights, benchmarking, and publication-ready statistical evaluation.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # set secrets
```

## Core Workflows

Analyze a file and create a dashboard:

```bash
python -m src.cli analyze logs/app.log --chunk-size 10 --format html --output $(echo ${RESULTS_ROOT:-results})/reports/analysis_results.html
```

Run a benchmarking comparison and append stats to the manuscript:

```bash
python -m src.cli benchmark path/to/logs.txt path/to/ground_truth.json \
  --out-prefix $(echo ${RESULTS_ROOT:-results})/benchmarks/bench \
  --model o3-mini --manuscript docs/results/manuscript.md
```

Provision EC2, stream CloudWatch logs, analyze, and save a live-updated dashboard:

```bash
python -m src.cli experiment --region us-east-1 --key-name YOUR_KEYPAIR \
  --duration 300 --chunk-size 5 --out-root $(echo ${RESULTS_ROOT:-results})/experiments
```

Publish figures and stats to the manuscript:

```bash
python -m src.cli publish results/experiments/run_YYYYMMDD_HHMMSS --manuscript docs/results/manuscript.md
python -m src.cli publish_stats --results publication_ready_results.json --manuscript docs/results/manuscript.md
```

One-click statistical analysis (synthetic, for paper numbers):

```bash
python quick_statistical_analysis.py
```

## Repository Structure

See `docs/REPO_STRUCTURE.md` for details. Generated artifacts go under `results/` (configurable via `RESULTS_ROOT`).

## Environment Variables

- `OPENAI_API_KEY` (required for LLM)
- `ELASTIC_API_KEY`, `SPLUNK_USERNAME`, `SPLUNK_PASSWORD` (optional connectors)
- `RESULTS_ROOT` (default: `results`)
- `AWS_REGION` (default: `us-east-1`)

## Makefile Shortcuts

```bash
make install
make experiment KEY_NAME=your-keypair AWS_REGION=us-east-1
make benchmark LOG_FILE=path/to/logs.txt GROUND_TRUTH=path/to/gt.json
make publish EXP_DIR=results/experiments/run_YYYYMMDD_HHMMSS
make publish-stats
```

## Notes

- All outputs are parameterized to land under `results/*`.
- Manuscript lives at `docs/results/manuscript.md`. Figures and stats can be appended via CLI.
