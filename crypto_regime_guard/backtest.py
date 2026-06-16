from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from crypto_regime_guard.indicators import max_drawdown, returns_from_equity, sharpe_like
from crypto_regime_guard.models import BacktestResult, Candle, Trade
from crypto_regime_guard.strategy import RegimeGuardStrategy


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 10_000.0
    fee_rate: float = 0.001
    slippage_bps: float = 5.0


class Backtester:
    def __init__(self, strategy: RegimeGuardStrategy, config: BacktestConfig | None = None) -> None:
        self.strategy = strategy
        self.config = config or BacktestConfig()

    def run(self, candles: list[Candle]) -> BacktestResult:
        if len(candles) < self.strategy.config.min_history() + 1:
            raise ValueError("not enough candles for backtest")
        cash = self.config.initial_cash
        units = 0.0
        average_entry = 0.0
        round_trips = 0
        winning_round_trips = 0
        trades: list[Trade] = []
        equity_curve: list[tuple[str, float]] = []
        signals = self.strategy.generate_signals(candles)
        slippage = self.config.slippage_bps / 10_000

        for candle, signal in zip(candles, signals, strict=True):
            mark_price = candle.close
            equity_before = cash + units * mark_price
            target_units = (equity_before * signal.target_position) / mark_price
            delta = target_units - units

            if abs(delta) > 1e-10:
                if delta > 0:
                    execution_price = mark_price * (1 + slippage)
                    max_affordable = cash / (execution_price * (1 + self.config.fee_rate))
                    executed = min(delta, max_affordable)
                    notional = executed * execution_price
                    fee = notional * self.config.fee_rate
                    cash -= notional + fee
                    previous_units = units
                    units += executed
                    average_entry = (
                        (average_entry * previous_units + execution_price * executed) / units
                        if units > 0
                        else 0.0
                    )
                    side = "BUY"
                else:
                    execution_price = mark_price * (1 - slippage)
                    executed = min(abs(delta), units)
                    notional = executed * execution_price
                    fee = notional * self.config.fee_rate
                    cash += notional - fee
                    units -= executed
                    side = "SELL"
                    if units <= 1e-10:
                        pnl = (execution_price - average_entry) * executed - fee
                        round_trips += 1
                        if pnl > 0:
                            winning_round_trips += 1
                        units = 0.0
                        average_entry = 0.0

                equity_after_trade = cash + units * mark_price
                trades.append(
                    Trade(
                        timestamp=candle.timestamp,
                        side=side,
                        price=execution_price,
                        quantity=executed,
                        fee=fee,
                        cash_after=cash,
                        equity_after=equity_after_trade,
                        reason=signal.reason,
                    )
                )

            equity_curve.append((candle.timestamp, cash + units * mark_price))

        final_equity = equity_curve[-1][1]
        total_return = final_equity / self.config.initial_cash - 1
        returns = returns_from_equity(equity_curve)
        win_rate = winning_round_trips / round_trips if round_trips else 0.0

        return BacktestResult(
            initial_cash=self.config.initial_cash,
            final_equity=final_equity,
            total_return=total_return,
            max_drawdown=max_drawdown([value for _, value in equity_curve]),
            sharpe_like=sharpe_like(returns),
            win_rate=win_rate,
            trades=trades,
            equity_curve=equity_curve,
        )


def load_candles_csv(path: str | Path) -> list[Candle]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [Candle.from_mapping(row) for row in reader]


def write_result_json(result: BacktestResult, path: str | Path) -> None:
    payload = result.as_dict() | {
        "trades": [trade.__dict__ for trade in result.trades],
        "equity_curve": result.equity_curve,
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def format_summary(result: BacktestResult) -> str:
    metrics = result.as_dict()
    return "\n".join(
        [
            "Backtest summary",
            "================",
            f"Initial cash : {metrics['initial_cash']:.2f}",
            f"Final equity : {metrics['final_equity']:.2f}",
            f"Total return : {metrics['total_return']:.2%}",
            f"Max drawdown : {metrics['max_drawdown']:.2%}",
            f"Sharpe-like  : {metrics['sharpe_like']:.2f}",
            f"Win rate     : {metrics['win_rate']:.2%}",
            f"Trades       : {metrics['trade_count']}",
        ]
    )
