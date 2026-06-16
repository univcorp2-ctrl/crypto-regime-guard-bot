# Research Summary: Open-source Crypto Trading Bots

Date: 2026-06-16

## Scope

The research reviewed public GitHub topic pages, highly starred repositories, curated crypto trading bot lists, current 2026 open-source bot rankings, and security research about fake stars/malware risk. The included scanner is designed to evaluate 300+ repositories reproducibly through the GitHub API.

## Key findings

1. The strongest production-grade foundations are maintained frameworks with backtesting, dry-run/paper mode, exchange abstractions, docs, and communities.
2. Star count is useful but dangerous alone. Fake-star campaigns and malware repositories frequently target cryptocurrency/tooling keywords.
3. Archived projects can still have high stars, but are poor bases for new trading systems.
4. Grid/DCA bots can work in ranging markets but can fail badly in one-way trends without regime filters and position caps.
5. Market-making and HFT frameworks need order-book data, latency modeling, and exchange-specific microstructure. They are not appropriate for casual live deployment.
6. ML/AI trading is attractive, but most public repos do not prove durable out-of-sample profitability. Treat AI as a feature generator or risk classifier first, not as an autonomous money printer.

## Representative evaluated projects

| Repo | Approx stars observed | Evaluation |
|---|---:|---|
| freqtrade/freqtrade | 51.5k | Strongest Python retail framework; backtesting, web UI, dry-run, FreqAI; good base for strategy research. |
| hummingbot/hummingbot | 18.9k | Strong market-making framework; CEX/DEX connectors; powerful but steeper operational complexity. |
| askmike/gekko | 10.2k | Historically important; archived; not suitable as a new base. |
| StockSharp/StockSharp | 10.1k | Broad multi-market C# platform; useful for professional devs, heavier than crypto-only use. |
| DeviaVir/zenbot | 8.3k | Historically popular; archived; avoid for new production. |
| jesse-ai/jesse | 8k | Clean research/backtesting framework; useful for Python strategy developers. |
| Drakkar-Software/OctoBot | 6.1k | Active open-source bot with UI, grid/DCA/AI/TradingView; good usability. |
| Superalgos/Superalgos | 5.5k | Visual strategy platform; broad feature set; latest release cadence should be checked. |
| nkaz001/hftbacktest | 4.2k | Serious HFT/backtesting focus with order-book/latency modeling; useful for microstructure research. |
| thrasher-corp/gocryptotrader | 3.4k | Go framework with broad exchange support; notes not production-ready. |
| Open-Trader/opentrader | 2.7k | UI, grid, DCA, RSI, backtest/live commands; promising but smaller community. |
| cassandre-tech/cassandre-trading-bot | 654 | Java/Spring approach; useful for Java teams. |

## Logic selected for this repo

The implemented strategy combines the most robust public lessons:

- Freqtrade/Jesse lesson: strategy must be simple, testable, and backtestable.
- Hummingbot/HFT lesson: market regime and execution risk matter more than indicator count.
- OctoBot/OpenTrader lesson: grid/DCA needs explicit regime gating.
- Security lesson: avoid opaque high-return repos and anything with hack/crack/cheat/private-key marketing.

## What might win now and later

The most plausible durable edges are not a single magic indicator. They are process edges:

- regime-aware trend following on liquid majors,
- conservative mean reversion only in range regimes,
- funding/carry scans with strict liquidation controls,
- volatility breakout with shock exit,
- order-book-aware execution only when you can model latency and fees,
- continuous walk-forward validation and deactivation when edge decays.

This repo starts with the first two because they are transparent, testable with OHLCV, and easier to defend against overfitting.

## Reproducible next step

Run the `Research 300+ GitHub crypto trading bot repos` workflow. The scanner will generate a CSV/Markdown report with 300+ rows, including any matching owner repositories when enabled.
