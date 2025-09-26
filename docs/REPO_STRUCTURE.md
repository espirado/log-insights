## Repository Structure and Conventions

Top-level layout:

- `src/` — all application code
  - `analyzers/` — analyzers (`ContextAwareLLMAnalyzer`, stream analyzer)
  - `data/` — IO connectors (parsers, EC2/CloudWatch, ELK, Splunk)
  - `evaluation/` — evaluators and statistical utilities
  - `visualization/` — charts and dashboards
  - `benchmarks/` — baselines and comparative benchmarking
  - `experiments/` — experiment runner and publish utilities
  - `cli.py` — CLI entrypoint
- `infra/terraform/` — EC2 infrastructure for real-world benchmarks
- `docs/` — documentation and manuscript
  - `results/` — manuscript and appended figures
  - `REPO_STRUCTURE.md` — this doc
- `results/` — generated outputs (gitignored)
  - `experiments/` — experiment runs (one subfolder per run)
  - `benchmarks/` — benchmark outputs
  - `reports/` — HTML/PDF reports
  - `figures/` — PNG/SVG figures for the paper

Conventions:
- All generated artifacts must be written under `RESULTS_ROOT` (default: `results/`).
- CLIs accept `--out-prefix` or `--output` within the `results/*` tree.
- Secrets via environment variables or `.env` only. Never commit keys.



