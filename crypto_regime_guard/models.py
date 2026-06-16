from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Candle:
    """Single OHLCV candle.

    Timestamp is kept as a string so CSV input can be ISO, unix-like, or exchange-native.
    """

    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> "Candle":
        required = ["timestamp", "open", "high", "low", "close"]
        missing = [name for name in required if name not in row or row[name] == ""]
        if missing:
            raise ValueError(f"missing candle fields: {', '.join(missing)}")

        candle = cls(
            timestamp=str(row["timestamp"]),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row.get("volume") or 0.0),
        )
        candle.validate()
        return candle

    def validate(self) -> None:
        if self.open <= 0 or self.high <= 0 or self.low <= 0 or self.close <= 0:
            raise ValueError(f"non-positive OHLC value at {self.timestamp}")
        if self.high < self.low:
            raise ValueError(f"high lower than low at {self.timestamp}")
        if not (self.low <= self.open <= self.high):
            raise ValueError(f"open outside high/low range at {self.timestamp}")
        if not (self.low <= self.close <= self.high):
            raise ValueError(f"close outside high/low range at {self.timestamp}")


@dataclass(frozen=True)
class Signal:
    timestamp: str
    action: str
    target_position: float
    regime: str
    reason: str
    risk_score: float


@dataclass(frozen=True)
class Trade:
    timestamp: str
    side: str
    price: float
    quantity: float
    fee: float
    cash_after: float
    equity_after: float
    reason: str


@dataclass(frozen=True)
class BacktestResult:
    initial_cash: float
    final_equity: float
    total_return: float
    max_drawdown: float
    sharpe_like: float
    win_rate: float
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[tuple[str, float]] = field(default_factory=list)

    def as_dict(self) -> dict[str, float | int]:
        return {
            "initial_cash": self.initial_cash,
            "final_equity": self.final_equity,
            "total_return": self.total_return,
            "max_drawdown": self.max_drawdown,
            "sharpe_like": self.sharpe_like,
            "win_rate": self.win_rate,
            "trade_count": len(self.trades),
        }
