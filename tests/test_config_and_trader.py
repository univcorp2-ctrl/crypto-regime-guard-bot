from pathlib import Path

import pytest

from crypto_regime_guard.config import load_bot_config
from crypto_regime_guard.models import Candle, Signal
from crypto_regime_guard.trader import LiveCcxtExecutor, TradingEngine


class FakeMarketData:
    def fetch_candles(self) -> list[Candle]:
        candles: list[Candle] = []
        price = 100.0
        for i in range(140):
            price *= 1.006
            candles.append(
                Candle(
                    timestamp=f"2026-01-01T{i:02d}:00:00Z",
                    open=price * 0.995,
                    high=price * 1.01,
                    low=price * 0.99,
                    close=price,
                    volume=1000 + i,
                )
            )
        return candles


class FakeExecutor:
    def __init__(self) -> None:
        self.calls: list[Signal] = []

    def execute(self, signal: Signal, price: float, quote_order: float) -> dict[str, object]:
        self.calls.append(signal)
        return {"status": "fake-filled", "price": price, "quote_order": quote_order}


def test_load_paper_config() -> None:
    config = load_bot_config("config/paper.example.toml")
    assert config.mode == "paper"
    assert config.strategy == "regime_guard"


def test_trading_engine_runs_once_with_fake_executor(tmp_path: Path) -> None:
    config = load_bot_config("config/ema-cross.paper.toml")
    executor = FakeExecutor()
    engine = TradingEngine(config, market_data=FakeMarketData(), executor=executor)
    result = engine.run_once()
    assert result.signal.action in {"BUY", "SELL", "HOLD"}
    assert result.risk_reason


def test_live_executor_requires_ack(monkeypatch: pytest.MonkeyPatch) -> None:
    config = load_bot_config("config/live.example.toml")
    monkeypatch.delenv("CRYPTO_BOT_LIVE_ACK", raising=False)
    with pytest.raises(PermissionError):
        LiveCcxtExecutor(config)
