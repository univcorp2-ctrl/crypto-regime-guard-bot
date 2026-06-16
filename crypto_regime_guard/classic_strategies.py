from __future__ import annotations

from dataclasses import dataclass

from crypto_regime_guard.indicators import atr, bollinger_bands, ema, rsi, rolling_high, rolling_low
from crypto_regime_guard.models import Candle, Signal


def _signal(
    candle: Candle,
    previous_target: float,
    target: float,
    regime: str,
    reason: str,
    risk_score: float = 0.0,
) -> Signal:
    action = "HOLD"
    if target > previous_target:
        action = "BUY"
    elif target < previous_target:
        action = "SELL"
    return Signal(
        timestamp=candle.timestamp,
        action=action,
        target_position=round(target, 6),
        regime=regime,
        reason=reason,
        risk_score=round(risk_score, 2),
    )


@dataclass(frozen=True)
class EmaCrossConfig:
    fast_ema: int = 20
    slow_ema: int = 80
    target_position: float = 1.0

    def min_history(self) -> int:
        return max(self.fast_ema, self.slow_ema) + 1


class EmaCrossStrategy:
    def __init__(self, config: EmaCrossConfig | None = None) -> None:
        self.config = config or EmaCrossConfig()

    def generate_signals(self, candles: list[Candle]) -> list[Signal]:
        closes = [candle.close for candle in candles]
        fast = ema(closes, self.config.fast_ema)
        slow = ema(closes, self.config.slow_ema)
        signals: list[Signal] = []
        target = 0.0
        for i, candle in enumerate(candles):
            previous = target
            if i < self.config.min_history() or fast[i] is None or slow[i] is None:
                signals.append(_signal(candle, previous, 0.0, "warmup", "not enough history"))
                continue
            if fast[i] > slow[i]:
                target = self.config.target_position
                reason = "fast EMA above slow EMA"
                regime = "trend_up"
            else:
                target = 0.0
                reason = "fast EMA below slow EMA"
                regime = "trend_down"
            signals.append(_signal(candle, previous, target, regime, reason))
        return signals


@dataclass(frozen=True)
class DonchianTrendConfig:
    lookback: int = 55
    target_position: float = 1.0

    def min_history(self) -> int:
        return self.lookback + 1


class DonchianTrendStrategy:
    def __init__(self, config: DonchianTrendConfig | None = None) -> None:
        self.config = config or DonchianTrendConfig()

    def generate_signals(self, candles: list[Candle]) -> list[Signal]:
        highs = [candle.high for candle in candles]
        lows = [candle.low for candle in candles]
        high_band = rolling_high(highs, self.config.lookback)
        low_band = rolling_low(lows, self.config.lookback)
        signals: list[Signal] = []
        target = 0.0
        for i, candle in enumerate(candles):
            previous = target
            if i < self.config.min_history() or high_band[i - 1] is None or low_band[i - 1] is None:
                signals.append(_signal(candle, previous, 0.0, "warmup", "not enough history"))
                continue
            if candle.close > high_band[i - 1]:
                target = self.config.target_position
                reason = "close broke previous Donchian high"
                regime = "breakout_up"
            elif candle.close < low_band[i - 1]:
                target = 0.0
                reason = "close broke previous Donchian low"
                regime = "breakout_down"
            else:
                reason = "inside Donchian channel"
                regime = "hold_channel"
            signals.append(_signal(candle, previous, target, regime, reason))
        return signals


@dataclass(frozen=True)
class RsiReversionConfig:
    rsi_window: int = 14
    atr_window: int = 14
    entry_rsi: float = 30.0
    exit_rsi: float = 52.0
    target_position: float = 0.5
    max_atr_ratio: float = 0.08

    def min_history(self) -> int:
        return max(self.rsi_window, self.atr_window) + 1


class RsiReversionStrategy:
    def __init__(self, config: RsiReversionConfig | None = None) -> None:
        self.config = config or RsiReversionConfig()

    def generate_signals(self, candles: list[Candle]) -> list[Signal]:
        closes = [candle.close for candle in candles]
        highs = [candle.high for candle in candles]
        lows = [candle.low for candle in candles]
        rsi_values = rsi(closes, self.config.rsi_window)
        atr_values = atr(highs, lows, closes, self.config.atr_window)
        signals: list[Signal] = []
        target = 0.0
        for i, candle in enumerate(candles):
            previous = target
            if i < self.config.min_history() or rsi_values[i] is None or atr_values[i] is None:
                signals.append(_signal(candle, previous, 0.0, "warmup", "not enough history"))
                continue
            atr_ratio = atr_values[i] / candle.close
            risk_score = min(100.0, 100.0 * atr_ratio / self.config.max_atr_ratio)
            if atr_ratio > self.config.max_atr_ratio:
                target = 0.0
                reason = "volatility shock: exit mean-reversion trade"
                regime = "shock"
            elif target == 0.0 and rsi_values[i] <= self.config.entry_rsi:
                target = self.config.target_position
                reason = "RSI oversold entry without averaging down"
                regime = "range_reversion"
            elif target > 0.0 and rsi_values[i] >= self.config.exit_rsi:
                target = 0.0
                reason = "RSI recovered to exit threshold"
                regime = "range_recovery"
            else:
                reason = "RSI between entry and exit thresholds"
                regime = "range_wait"
            signals.append(_signal(candle, previous, target, regime, reason, risk_score))
        return signals


@dataclass(frozen=True)
class BollingerBreakoutConfig:
    window: int = 20
    stddev_multiple: float = 2.0
    trend_ema: int = 80
    target_position: float = 0.75

    def min_history(self) -> int:
        return max(self.window, self.trend_ema) + 1


class BollingerBreakoutStrategy:
    def __init__(self, config: BollingerBreakoutConfig | None = None) -> None:
        self.config = config or BollingerBreakoutConfig()

    def generate_signals(self, candles: list[Candle]) -> list[Signal]:
        closes = [candle.close for candle in candles]
        middle, upper, _lower = bollinger_bands(
            closes, self.config.window, self.config.stddev_multiple
        )
        trend = ema(closes, self.config.trend_ema)
        signals: list[Signal] = []
        target = 0.0
        for i, candle in enumerate(candles):
            previous = target
            if (
                i < self.config.min_history()
                or middle[i] is None
                or upper[i] is None
                or trend[i] is None
            ):
                signals.append(_signal(candle, previous, 0.0, "warmup", "not enough history"))
                continue
            if target == 0.0 and candle.close > upper[i] and candle.close > trend[i]:
                target = self.config.target_position
                reason = "Bollinger upper breakout with trend filter"
                regime = "volatility_expansion"
            elif target > 0.0 and candle.close < middle[i]:
                target = 0.0
                reason = "breakout failed below Bollinger middle"
                regime = "breakout_exit"
            else:
                reason = "waiting for confirmed volatility expansion"
                regime = "breakout_wait"
            signals.append(_signal(candle, previous, target, regime, reason))
        return signals
