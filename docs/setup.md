# Setup Guide

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
python -m crypto_regime_guard.cli backtest data/sample_btc_usdt_1h.csv
```

## GitHub Actions

Two workflows are included:

- `CI`: lint, tests, sample backtest, artifact upload.
- `Research 300+ GitHub crypto trading bot repos`: manual scan of GitHub repositories and artifact upload.

## Secrets

No secret is required for normal CI or local sample backtests.

Optional future/live secrets:

- `GITHUB_TOKEN`: only needed locally for high-rate GitHub repo scanning. GitHub Actions provides `github.token` automatically.
- `EXCHANGE_API_KEY`: future live/paper exchange adapter.
- `EXCHANGE_API_SECRET`: future live/paper exchange adapter.
- `EXCHANGE_API_PASSPHRASE`: only for exchanges that require it.

Keep withdrawals disabled on any exchange API key. Use read-only keys for research wherever possible.

## Running the 300+ repo scan in GitHub

1. Open the repository Actions tab.
2. Select `Research 300+ GitHub crypto trading bot repos`.
3. Run workflow with `limit=350`.
4. Download artifact `repo-research-report`.

The artifact contains:

- `repo-evaluation.csv`
- `repo-evaluation.md`

## Going live later

Before live trading, add:

- exchange adapter with dry-run mode,
- order-size validation,
- rate-limit handling,
- persistent positions,
- emergency flat command,
- monitoring and alerts,
- walk-forward and out-of-sample reports.
