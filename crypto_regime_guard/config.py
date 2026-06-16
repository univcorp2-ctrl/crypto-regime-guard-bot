from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from crypto_regime_guard.risk import RiskConfig


@dataclass(frozen=True)
class BotConfig:
    mode: str = "paper"
    exchange_id: str = "binance"
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    strategy: str = "regime_guard"
    candle_limit: int = 200
    quote_order_size: float = 25.0
    poll_seconds: int = 60
    enable_live_trading: bool = False
    data_path: str | None = "data/sample_btc_usdt_1h.csv"
    paper_initial_quote: float = 1000.0
    state_path: str = "state/paper_state.json"
    trade_log_path: str = "logs/trades.csv"
    strategy_params: dict[str, Any] = field(default_factory=dict)
    risk: RiskConfig = field(default_factory=RiskConfig)


def load_bot_config(path: str | Path) -> BotConfig:
    raw = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    bot = raw.get("bot", {})
    risk = raw.get("risk", {})
    strategy_params = raw.get("strategy_params", {})
    mode = str(bot.get("mode", "paper"))
    if mode not in {"paper", "live"}:
        raise ValueError("bot.mode must be 'paper' or 'live'")
    return BotConfig(
        mode=mode,
        exchange_id=str(bot.get("exchange_id", bot.get("exchange", "binance"))),
        symbol=str(bot.get("symbol", "BTC/USDT")),
        timeframe=str(bot.get("timeframe", "1h")),
        strategy=str(bot.get("strategy", "regime_guard")),
        candle_limit=int(bot.get("candle_limit", 200)),
        quote_order_size=float(bot.get("quote_order_size", 25.0)),
        poll_seconds=int(bot.get("poll_seconds", 60)),
        enable_live_trading=bool(bot.get("enable_live_trading", False)),
        data_path=bot.get("data_path", "data/sample_btc_usdt_1h.csv"),
        paper_initial_quote=float(bot.get("paper_initial_quote", 1000.0)),
        state_path=str(bot.get("state_path", "state/paper_state.json")),
        trade_log_path=str(bot.get("trade_log_path", "logs/trades.csv")),
        strategy_params=dict(strategy_params),
        risk=RiskConfig(
            min_quote_order=float(risk.get("min_quote_order", 10.0)),
            max_single_trade_quote=float(risk.get("max_single_trade_quote", 50.0)),
            max_risk_score=float(risk.get("max_risk_score", 85.0)),
            allow_live_market_orders=bool(risk.get("allow_live_market_orders", True)),
        ),
    )
