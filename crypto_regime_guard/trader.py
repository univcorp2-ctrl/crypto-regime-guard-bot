from __future__ import annotations

import csv
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from crypto_regime_guard.backtest import load_candles_csv
from crypto_regime_guard.config import BotConfig
from crypto_regime_guard.models import Candle, Signal
from crypto_regime_guard.risk import RiskManager
from crypto_regime_guard.strategy_catalog import build_strategy

LIVE_ACK_VALUE = "I_UNDERSTAND_THIS_CAN_LOSE_MONEY"


class MarketDataSource(Protocol):
    def fetch_candles(self) -> list[Candle]: ...


class TradeExecutor(Protocol):
    def execute(self, signal: Signal, price: float, quote_order: float) -> dict[str, Any]: ...


@dataclass(frozen=True)
class TradeRunResult:
    signal: Signal
    risk_allowed: bool
    risk_reason: str
    execution: dict[str, Any] | None


class CsvMarketDataSource:
    def __init__(self, path: str | Path, limit: int = 200) -> None:
        self.path = Path(path)
        self.limit = limit

    def fetch_candles(self) -> list[Candle]:
        candles = load_candles_csv(self.path)
        return candles[-self.limit :]


class CcxtMarketDataSource:
    def __init__(self, exchange_id: str, symbol: str, timeframe: str, limit: int) -> None:
        self.exchange_id = exchange_id
        self.symbol = symbol
        self.timeframe = timeframe
        self.limit = limit
        self.exchange = _build_ccxt_exchange(exchange_id)

    def fetch_candles(self) -> list[Candle]:
        rows = self.exchange.fetch_ohlcv(self.symbol, timeframe=self.timeframe, limit=self.limit)
        candles: list[Candle] = []
        for row in rows:
            timestamp_ms, open_, high, low, close, volume = row[:6]
            candles.append(
                Candle(
                    timestamp=str(timestamp_ms),
                    open=float(open_),
                    high=float(high),
                    low=float(low),
                    close=float(close),
                    volume=float(volume),
                )
            )
        return candles


class PaperExecutor:
    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.state_path = Path(config.state_path)
        self.log_path = Path(config.trade_log_path)
        self.state = self._load_state()

    def execute(self, signal: Signal, price: float, quote_order: float) -> dict[str, Any]:
        base = self.state.get("base", 0.0)
        quote = self.state.get("quote", self.config.paper_initial_quote)
        fee_rate = self.state.get("fee_rate", 0.001)
        if signal.action == "BUY":
            spend = min(quote, quote_order)
            fee = spend * fee_rate
            net_spend = max(0.0, spend - fee)
            quantity = net_spend / price
            quote -= spend
            base += quantity
            side = "BUY"
        elif signal.action == "SELL":
            quantity = base
            gross = quantity * price
            fee = gross * fee_rate
            quote += gross - fee
            base = 0.0
            side = "SELL"
        else:
            return {"status": "skipped", "reason": "hold signal"}

        self.state = {"base": base, "quote": quote, "fee_rate": fee_rate, "last_price": price}
        self._save_state()
        row = {
            "mode": "paper",
            "timestamp": signal.timestamp,
            "side": side,
            "price": price,
            "quantity": quantity,
            "quote_after": quote,
            "base_after": base,
            "reason": signal.reason,
        }
        self._append_log(row)
        return {"status": "filled", **row}

    def _load_state(self) -> dict[str, float]:
        if not self.state_path.exists():
            return {"base": 0.0, "quote": self.config.paper_initial_quote, "fee_rate": 0.001}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def _append_log(self, row: dict[str, Any]) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        exists = self.log_path.exists()
        with self.log_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(row))
            if not exists:
                writer.writeheader()
            writer.writerow(row)


class LiveCcxtExecutor:
    def __init__(self, config: BotConfig) -> None:
        if not config.enable_live_trading:
            raise PermissionError("live trading blocked: enable_live_trading is false")
        if os.getenv("CRYPTO_BOT_LIVE_ACK") != LIVE_ACK_VALUE:
            raise PermissionError("live trading blocked: CRYPTO_BOT_LIVE_ACK is not set correctly")
        self.config = config
        self.exchange = _build_ccxt_exchange(config.exchange_id, require_keys=True)

    def execute(self, signal: Signal, price: float, quote_order: float) -> dict[str, Any]:
        if signal.action == "BUY":
            amount = quote_order / price
            order = self.exchange.create_market_buy_order(self.config.symbol, amount)
            return {"status": "submitted", "side": "BUY", "amount": amount, "order": order}
        if signal.action == "SELL":
            base_asset = self.config.symbol.split("/")[0]
            balance = self.exchange.fetch_balance()
            base_free = _extract_free_balance(balance, base_asset)
            if base_free <= 0:
                return {"status": "skipped", "reason": f"no free {base_asset} balance"}
            order = self.exchange.create_market_sell_order(self.config.symbol, base_free)
            return {"status": "submitted", "side": "SELL", "amount": base_free, "order": order}
        return {"status": "skipped", "reason": "hold signal"}


class TradingEngine:
    def __init__(
        self,
        config: BotConfig,
        market_data: MarketDataSource | None = None,
        executor: TradeExecutor | None = None,
    ) -> None:
        self.config = config
        self.strategy = build_strategy(config.strategy, config.strategy_params)
        self.market_data = market_data or build_market_data_source(config)
        self.executor = executor or build_executor(config)
        self.risk = RiskManager(config.risk)

    def run_once(self) -> TradeRunResult:
        candles = self.market_data.fetch_candles()
        signals = self.strategy.generate_signals(candles)
        if not signals:
            raise ValueError("strategy produced no signals")
        latest_signal = signals[-1]
        latest_price = candles[-1].close
        decision = self.risk.evaluate(
            latest_signal,
            requested_quote_order=self.config.quote_order_size,
            live=self.config.mode == "live",
        )
        if not decision.allowed:
            return TradeRunResult(latest_signal, False, decision.reason, None)
        execution = self.executor.execute(latest_signal, latest_price, decision.adjusted_quote_order)
        return TradeRunResult(latest_signal, True, decision.reason, execution)

    def run_forever(self) -> None:
        while True:
            result = self.run_once()
            print_trade_run_result(result)
            time.sleep(self.config.poll_seconds)


def build_market_data_source(config: BotConfig) -> MarketDataSource:
    if config.data_path:
        return CsvMarketDataSource(config.data_path, config.candle_limit)
    return CcxtMarketDataSource(config.exchange_id, config.symbol, config.timeframe, config.candle_limit)


def build_executor(config: BotConfig) -> TradeExecutor:
    if config.mode == "paper":
        return PaperExecutor(config)
    if config.mode == "live":
        return LiveCcxtExecutor(config)
    raise ValueError(f"unsupported mode: {config.mode}")


def print_trade_run_result(result: TradeRunResult) -> None:
    print(
        json.dumps(
            {
                "signal": result.signal.__dict__,
                "risk_allowed": result.risk_allowed,
                "risk_reason": result.risk_reason,
                "execution": result.execution,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


def _build_ccxt_exchange(exchange_id: str, require_keys: bool = False) -> Any:
    try:
        import ccxt  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError("Install live dependencies first: pip install -e '.[live]'") from exc

    exchange_cls = getattr(ccxt, exchange_id)
    config: dict[str, Any] = {"enableRateLimit": True}
    api_key = os.getenv("EXCHANGE_API_KEY")
    api_secret = os.getenv("EXCHANGE_API_SECRET")
    password = os.getenv("EXCHANGE_API_PASSPHRASE")
    if api_key:
        config["apiKey"] = api_key
    if api_secret:
        config["secret"] = api_secret
    if password:
        config["password"] = password
    if require_keys and (not api_key or not api_secret):
        raise PermissionError("EXCHANGE_API_KEY and EXCHANGE_API_SECRET are required for live trading")
    return exchange_cls(config)


def _extract_free_balance(balance: dict[str, Any], asset: str) -> float:
    value = balance.get(asset)
    if isinstance(value, dict):
        return float(value.get("free") or 0.0)
    free = balance.get("free")
    if isinstance(free, dict):
        return float(free.get(asset) or 0.0)
    return 0.0
