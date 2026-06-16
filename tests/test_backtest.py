from crypto_regime_guard.backtest import BacktestConfig, Backtester, load_candles_csv
from crypto_regime_guard.strategy import RegimeGuardStrategy, StrategyConfig


def test_backtest_runs_on_sample_data() -> None:
    candles = load_candles_csv("data/sample_btc_usdt_1h.csv")
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
    result = Backtester(strategy, BacktestConfig(initial_cash=10_000)).run(candles)
    assert result.final_equity > 0
    assert result.max_drawdown >= 0
    assert len(result.equity_curve) == len(candles)
