from __future__ import annotations

from dataclasses import dataclass

from crypto_regime_guard.indicators import atr, ema, range_efficiency, rolling_zscore
from crypto_regime_guard.models import Candle, Signal


@dataclass(frozen=True)
class StrategyConfig:
    fast_ema: int = 20
    slow_ema: int = 80
    atr_window: int = 14
    breakout_lookback: int = 55
    mean_reversion_lookback: int = 40
    trend_slope_bars: int = 10
    range_efficiency_threshold: float = 0.25
    shock_atr_multiple: float = 3.0
    max_atr_ratio: float = 0.08
    max_position: float = 1.0
    sideways_position: float = 0.35
    mean_reversion_entry_z: float = -1.8
    mean_reversion_exit_z: float = 0.4

    def min_history(self) -> int:
        return max(
            self.slow_ema + self.trend_slope_bars,
            self.breakout_lookback + 1,
            self.mean_reversion_lookback,
            self.atr_window + 1,
        )


class RegimeGuardStrategy:
    """Regime-aware long-only spot strategy.

    It is deliberately defensive. The strategy only targets long exposure when trend and
    volatility filters agree, and it moves flat during downtrends or shock candles.
    """

    def __init__(self, config: StrategyConfig | None = None) -> None:
        self.config = config or StrategyConfig()

    def generate_signals(self, candles: list[Candle]) -> list[Signal]:
        if not candles:
            return []

        closes = [candle.close for candle in candles]
        highs = [candle.high for candle in candles]
        lows = [candle.low for candle in candles]
        fast = ema(closes, self.config.fast_ema)
        slow = ema(closes, self.config.slow_ema)
        atr_values = atr(highs, lows, closes, self.config.atr_window)
        zscores = rolling_zscore(closes, self.config.mean_reversion_lookback)

        signals: list[Signal] = []
        target_position = 0.0

        for i, candle in enumerate(candles):
            if i < self.config.min_history():
                signals.append(
                    Signal(
                        timestamp=candle.timestamp,
                        action="HOLD",
                        target_position=0.0,
                        regime="warmup",
                        reason="not enough history",
                        risk_score=0.0,
                    )
                )
                continue

            assert fast[i] is not None
            assert slow[i] is not None
            assert slow[i - self.config.trend_slope_bars] is not None
            assert atr_values[i] is not None
            assert zscores[i] is not None

            previous_high = max(highs[i - self.config.breakout_lookback : i])
            previous_low = min(lows[i - self.config.breakout_lookback : i])
            efficiency = range_efficiency(closes, self.config.breakout_lookback, i) or 0.0
            slow_slope = (slow[i] - slow[i - self.config.trend_slope_bars]) / slow[i]
            atr_ratio = atr_values[i] / candle.close
            previous_atr = atr_values[i - 1] or atr_values[i]
            current_true_range = max(
                candle.high - candle.low,
                abs(candle.high - candles[i - 1].close),
                abs(candle.low - candles[i - 1].close),
            )
            shock = (
                atr_ratio > self.config.max_atr_ratio
                or current_true_range > self.config.shock_atr_multiple * previous_atr
            )
            risk_score = min(100.0, 100.0 * atr_ratio / self.config.max_atr_ratio)

            if shock:
                regime = "shock"
            elif (
                candle.close > slow[i]
                and fast[i] > slow[i]
                and slow_slope > 0
                and efficiency >= self.config.range_efficiency_threshold
            ):
                regime = "trend_up"
            elif candle.close < slow[i] and fast[i] < slow[i] and slow_slope < 0:
                regime = "trend_down"
            else:
                regime = "sideways"

            previous_target = target_position
            reason = "no edge"

            if regime in {"shock", "trend_down"}:
                target_position = 0.0
                reason = f"flat during {regime}"
            elif regime == "trend_up" and candle.close > previous_high:
                target_position = self.config.max_position
                reason = "donchian breakout in confirmed uptrend"
            elif previous_target > 0 and (candle.close < previous_low or candle.close < slow[i]):
                target_position = 0.0
                reason = "trend exit: price below stop/reference"
            elif regime == "sideways" and zscores[i] <= self.config.mean_reversion_entry_z:
                target_position = self.config.sideways_position
                reason = "small sideways mean-reversion entry"
            elif previous_target > 0 and regime == "sideways" and zscores[i] >= self.config.mean_reversion_exit_z:
                target_position = 0.0
                reason = "sideways mean-reversion exit"

            action = "HOLD"
            if target_position > previous_target:
                action = "BUY"
            elif target_position < previous_target:
                action = "SELL"

            signals.append(
                Signal(
                    timestamp=candle.timestamp,
                    action=action,
                    target_position=round(target_position, 6),
                    regime=regime,
                    reason=reason,
                    risk_score=round(risk_score, 2),
                )
            )

        return signals
