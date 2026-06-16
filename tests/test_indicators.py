from crypto_regime_guard.indicators import bollinger_bands, ema, max_drawdown, rolling_zscore, rsi, sma


def test_sma_and_ema_lengths() -> None:
    values = [1, 2, 3, 4, 5]
    assert sma(values, 3) == [None, None, 2.0, 3.0, 4.0]
    assert len(ema(values, 3)) == len(values)


def test_zscore_flat_series_is_zero_after_warmup() -> None:
    values = [5.0] * 10
    zscores = rolling_zscore(values, 5)
    assert zscores[-1] == 0.0


def test_max_drawdown() -> None:
    assert max_drawdown([100, 120, 90, 130]) == 0.25


def test_rsi_and_bollinger_lengths() -> None:
    values = [float(i) for i in range(1, 40)]
    assert len(rsi(values, 14)) == len(values)
    middle, upper, lower = bollinger_bands(values, 20)
    assert len(middle) == len(values)
    assert upper[-1] is not None
    assert lower[-1] is not None
