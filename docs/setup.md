# Setup Guide

## 最短セットアップ

```bash
git clone https://github.com/univcorp2-ctrl/crypto-regime-guard-bot.git
cd crypto-regime-guard-bot
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,live]'
pytest
```

## 戦略一覧

```bash
python -m crypto_regime_guard.cli list-strategies
```

## バックテスト

```bash
python -m crypto_regime_guard.cli backtest data/sample_btc_usdt_1h.csv --strategy regime_guard
python -m crypto_regime_guard.cli backtest data/sample_btc_usdt_1h.csv --strategy ema_cross
python -m crypto_regime_guard.cli backtest data/sample_btc_usdt_1h.csv --strategy rsi_reversion
```

## 紙取引

```bash
python -m crypto_regime_guard.cli trade --config config/paper.example.toml --once
```

## ライブ取引

```bash
export EXCHANGE_API_KEY='your_key'
export EXCHANGE_API_SECRET='your_secret'
export CRYPTO_BOT_LIVE_ACK='I_UNDERSTAND_THIS_CAN_LOSE_MONEY'
python -m crypto_regime_guard.cli trade --config config/live.example.toml --once
```

詳細は `docs/live-trading.md` を読んでください。

## GitHub Actions

現在のGitHub automation tokenでは `.github/workflows/*` の作成が404で失敗したため、workflow定義は `docs/workflows/` に保存しています。

- `docs/workflows/ci.yml`
- `docs/workflows/research.yml`

workflow-file作成権限があるtokenで `.github/workflows/` に移せばCIが動きます。
