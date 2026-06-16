import pytest

from crypto_regime_guard.strategy_catalog import build_strategy, strategy_names


def test_strategy_catalog_lists_expected_strategies() -> None:
    names = strategy_names()
    assert "regime_guard" in names
    assert "ema_cross" in names
    assert "rsi_reversion" in names


def test_strategy_catalog_builds_with_overrides() -> None:
    strategy = build_strategy("ema_cross", {"fast_ema": "5", "slow_ema": "10"})
    assert strategy.config.fast_ema == 5
    assert strategy.config.slow_ema == 10


def test_strategy_catalog_rejects_unknown_strategy() -> None:
    with pytest.raises(ValueError):
        build_strategy("magic_money_printer")
