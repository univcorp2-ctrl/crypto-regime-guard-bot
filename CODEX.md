# CODEX / Agent Notes

## Goal

Create a transparent, paper-first crypto trading research repo. Do not present profitability as guaranteed. Keep live trading disabled until explicit exchange adapters, monitoring, and secrets management are added.

## Commands

```bash
pip install -e '.[dev]'
ruff check .
pytest -q
python -m crypto_regime_guard.cli backtest data/sample_btc_usdt_1h.csv
```

## Guardrails

- No hard-coded API keys or secrets.
- No live order placement in default code.
- No martingale/unbounded averaging down.
- Any new strategy must include tests and an out-of-sample evaluation note.
- Scanner risk flags should be treated as triage, not proof of malware.
