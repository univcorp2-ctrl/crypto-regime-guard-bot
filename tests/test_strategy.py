from crypto_regime_guard.models import Candle
from crypto_regime_guard.strategy import RegimeGuardStrategy, StrategyConfig


def make_trend_candles(count: int = 140) -> list[Candle]:
    candles: list[Candle] = []
    price = 100.0
    for i in range(count):
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


def test_strategy_generates_breakout_buy_in_trend() -> None:
    strategy = RegimeGuardStrategy(
        StrategyConfig(
            fast_ema=5,
            slow_ema=15,
            breakout_lookback=10,
            mean_reversion_lookback=10,
            trend_slope_bars=3,
            atr_window=5,
            range_efficiency_threshold=0.1,
        )
    )
    signals = strategy.generate_signals(make_trend_candles())
    assert any(signal.action == "BUY" for signal in signals)
    assert signals[-1].regime in {"trend_up", "sideways"}
