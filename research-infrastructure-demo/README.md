# Research infrastructure demo

A small, self-contained portfolio demo for research data workflows. It uses
synthetic participant records to show input validation, privacy-conscious
aggregation, processing logs, optional external API configuration, and tests.

This is a learning demo, not production infrastructure. It contains no real
participant data and makes no network request unless `--send-summary` is used.

## Run locally

Requires Python 3.10+ and no third-party packages.

```bash
cd research-infrastructure-demo
python demo.py
python -m unittest discover -s tests -v
```

GitHub Actions runs the same tests when this demo changes.

The run writes `outputs/summary.json` and `outputs/pipeline.jsonl`. The summary
contains only aggregate values. The log records processing steps and row
counts, never participant IDs, row-level values, or credentials.

## Optional external API

The demo sends only the aggregate summary, never the input rows. To configure
an API, copy `.env.example` to `.env` and set `RESEARCH_API_URL` and
`RESEARCH_API_KEY` in your local environment. The program does not load `.env`
automatically, and `.env` is ignored by Git. For example, load the variables in
your shell before running:

```bash
export RESEARCH_API_URL="https://your-approved-service.example/api/summary"
export RESEARCH_API_KEY="your-secret-key"
python demo.py --send-summary
```

The API URL must use HTTPS. The key is sent in an Authorization header and is
never written to logs or output files. A five-second timeout is used. The
network call is opt-in and can be tested without a live service because tests
use a mocked HTTP response.

## Privacy and access considerations

- Use synthetic or appropriately approved data only; never commit secrets or
  identifiable research data.
- Keep API keys in environment variables or an approved secrets manager. Use
  minimum necessary access, rotate keys, and revoke them when no longer needed.
- Send only the minimum aggregate information needed. Cells smaller than five
  are suppressed in the example to reduce disclosure risk; this threshold is
  illustrative and is not a universal privacy guarantee.
- In a real study, follow the project's approvals, data-management plan,
  institutional policies, and applicable privacy requirements. Restrict
  repository and service access to authorized people.

## What this demonstrates

- Python data handling and validation
- A reproducible, documented workflow with synthetic input
- Privacy-aware aggregation and non-sensitive processing logs
- Secure configuration for an optional external API
- Unit tests for data checks, disclosure suppression, and API behavior

The API endpoint is intentionally generic. No external service or API key is
needed to run the demo.
