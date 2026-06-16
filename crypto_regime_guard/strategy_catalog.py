from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any, Protocol

from crypto_regime_guard.classic_strategies import (
    BollingerBreakoutConfig,
    BollingerBreakoutStrategy,
    DonchianTrendConfig,
    DonchianTrendStrategy,
    EmaCrossConfig,
    EmaCrossStrategy,
    RsiReversionConfig,
    RsiReversionStrategy,
)
from crypto_regime_guard.models import Candle, Signal
from crypto_regime_guard.strategy import RegimeGuardStrategy, StrategyConfig


class TradingStrategy(Protocol):
    def generate_signals(self, candles: list[Candle]) -> list[Signal]: ...


_STRATEGIES: dict[str, tuple[type[Any], type[Any]]] = {
    "regime_guard": (RegimeGuardStrategy, StrategyConfig),
    "ema_cross": (EmaCrossStrategy, EmaCrossConfig),
    "donchian_trend": (DonchianTrendStrategy, DonchianTrendConfig),
    "rsi_reversion": (RsiReversionStrategy, RsiReversionConfig),
    "bollinger_breakout": (BollingerBreakoutStrategy, BollingerBreakoutConfig),
}


def strategy_names() -> list[str]:
    return sorted(_STRATEGIES)


def build_strategy(name: str, params: dict[str, Any] | None = None) -> TradingStrategy:
    if name not in _STRATEGIES:
        available = ", ".join(strategy_names())
        raise ValueError(f"unknown strategy '{name}'. Available strategies: {available}")
    strategy_cls, config_cls = _STRATEGIES[name]
    config = build_config(config_cls, params or {})
    return strategy_cls(config)


def build_config(config_cls: type[Any], params: dict[str, Any]) -> Any:
    if not is_dataclass(config_cls):
        raise TypeError("strategy config must be a dataclass")
    allowed = {field.name: field for field in fields(config_cls)}
    unknown = sorted(set(params) - set(allowed))
    if unknown:
        raise ValueError(f"unknown config key(s): {', '.join(unknown)}")
    converted: dict[str, Any] = {}
    default_config = config_cls()
    for key, value in params.items():
        default_value = getattr(default_config, key)
        converted[key] = _coerce_value(value, default_value)
    return config_cls(**converted)


def _coerce_value(value: Any, default_value: Any) -> Any:
    if isinstance(value, str):
        if isinstance(default_value, bool):
            return value.lower() in {"1", "true", "yes", "on"}
        if isinstance(default_value, int) and not isinstance(default_value, bool):
            return int(value)
        if isinstance(default_value, float):
            return float(value)
    return value
