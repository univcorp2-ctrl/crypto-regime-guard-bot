from __future__ import annotations

import math
from collections.abc import Sequence


def sma(values: Sequence[float], window: int) -> list[float | None]:
    _validate_window(window)
    out: list[float | None] = []
    running = 0.0
    for i, value in enumerate(values):
        running += value
        if i >= window:
            running -= values[i - window]
        out.append(running / window if i + 1 >= window else None)
    return out


def ema(values: Sequence[float], window: int) -> list[float | None]:
    _validate_window(window)
    if not values:
        return []
    alpha = 2 / (window + 1)
    out: list[float | None] = []
    current = values[0]
    for i, value in enumerate(values):
        current = value if i == 0 else alpha * value + (1 - alpha) * current
        out.append(current if i + 1 >= window else None)
    return out


def true_range(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float]) -> list[float]:
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("high, low and close series must have the same length")
    out: list[float] = []
    for i, high in enumerate(highs):
        low = lows[i]
        if i == 0:
            out.append(high - low)
        else:
            prev_close = closes[i - 1]
            out.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    return out


def atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], window: int) -> list[float | None]:
    return sma(true_range(highs, lows, closes), window)


def rolling_high(values: Sequence[float], window: int) -> list[float | None]:
    _validate_window(window)
    out: list[float | None] = []
    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
        else:
            out.append(max(values[i + 1 - window : i + 1]))
    return out


def rolling_low(values: Sequence[float], window: int) -> list[float | None]:
    _validate_window(window)
    out: list[float | None] = []
    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
        else:
            out.append(min(values[i + 1 - window : i + 1]))
    return out


def rolling_zscore(values: Sequence[float], window: int) -> list[float | None]:
    _validate_window(window)
    out: list[float | None] = []
    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
            continue
        segment = values[i + 1 - window : i + 1]
        mean = sum(segment) / window
        variance = sum((value - mean) ** 2 for value in segment) / window
        std = math.sqrt(variance)
        out.append(0.0 if std == 0 else (values[i] - mean) / std)
    return out


def range_efficiency(values: Sequence[float], lookback: int, index: int) -> float | None:
    """Absolute displacement divided by path length.

    A value near 1 means clean trend. A value near 0 means noisy chop.
    """

    if lookback <= 0:
        raise ValueError("lookback must be positive")
    if index < lookback:
        return None
    displacement = abs(values[index] - values[index - lookback])
    path = sum(abs(values[i] - values[i - 1]) for i in range(index - lookback + 1, index + 1))
    return 0.0 if path == 0 else displacement / path


def returns_from_equity(equity_curve: Sequence[tuple[str, float]]) -> list[float]:
    returns: list[float] = []
    for i in range(1, len(equity_curve)):
        prev = equity_curve[i - 1][1]
        current = equity_curve[i][1]
        if prev > 0:
            returns.append((current / prev) - 1)
    return returns


def max_drawdown(equity_values: Sequence[float]) -> float:
    peak = -math.inf
    worst = 0.0
    for value in equity_values:
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, value / peak - 1)
    return abs(worst)


def sharpe_like(returns: Sequence[float], periods_per_year: int = 365 * 24) -> float:
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / (len(returns) - 1)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return (mean / std) * math.sqrt(periods_per_year)


def _validate_window(window: int) -> None:
    if window <= 0:
        raise ValueError("window must be positive")
