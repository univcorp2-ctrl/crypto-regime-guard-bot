from __future__ import annotations

import argparse
from pathlib import Path

from crypto_regime_guard.backtest import (
    BacktestConfig,
    Backtester,
    format_summary,
    load_candles_csv,
    write_result_json,
)
from crypto_regime_guard.config import load_bot_config
from crypto_regime_guard.scanner import main as scanner_main
from crypto_regime_guard.strategy_catalog import build_strategy, strategy_names
from crypto_regime_guard.trader import TradingEngine, print_trade_run_result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Crypto Regime Guard CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-strategies", help="Show selectable trading strategies")

    backtest = subparsers.add_parser("backtest", help="Run a CSV backtest")
    backtest.add_argument("csv_path", type=Path)
    backtest.add_argument("--strategy", choices=strategy_names(), default="regime_guard")
    backtest.add_argument(
        "--strategy-param",
        action="append",
        default=[],
        help="Override strategy config, e.g. fast_ema=10. Can be repeated.",
    )
    backtest.add_argument("--initial-cash", type=float, default=10_000.0)
    backtest.add_argument("--fee-rate", type=float, default=0.001)
    backtest.add_argument("--slippage-bps", type=float, default=5.0)
    backtest.add_argument("--json-output", type=Path)

    trade = subparsers.add_parser("trade", help="Run paper or live trading from config")
    trade.add_argument("--config", type=Path, default=Path("config/paper.example.toml"))
    trade.add_argument("--once", action="store_true", help="Run one cycle and exit")

    validate = subparsers.add_parser("validate-config", help="Validate a bot config")
    validate.add_argument("--config", type=Path, default=Path("config/paper.example.toml"))

    scan = subparsers.add_parser("scan-repos", help="Evaluate GitHub crypto trading bot repos")
    scan.add_argument("--limit", type=int, default=350)
    scan.add_argument("--output", type=Path, default=Path("artifacts/repo-evaluation.csv"))
    scan.add_argument("--markdown", type=Path, default=Path("artifacts/repo-evaluation.md"))
    scan.add_argument("--include-owner-repos", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "list-strategies":
        for name in strategy_names():
            print(name)
        return 0

    if args.command == "scan-repos":
        scanner_args = [
            "--limit",
            str(args.limit),
            "--output",
            str(args.output),
            "--markdown",
            str(args.markdown),
        ]
        if args.include_owner_repos:
            scanner_args.append("--include-owner-repos")
        return scanner_main(scanner_args)

    if args.command == "validate-config":
        config = load_bot_config(args.config)
        build_strategy(config.strategy, config.strategy_params)
        print(f"OK: {args.config} uses strategy={config.strategy} mode={config.mode}")
        return 0

    if args.command == "trade":
        config = load_bot_config(args.config)
        engine = TradingEngine(config)
        if args.once:
            print_trade_run_result(engine.run_once())
            return 0
        engine.run_forever()
        return 0

    strategy_params = _parse_strategy_params(args.strategy_param)
    candles = load_candles_csv(args.csv_path)
    backtester = Backtester(
        build_strategy(args.strategy, strategy_params),
        BacktestConfig(
            initial_cash=args.initial_cash,
            fee_rate=args.fee_rate,
            slippage_bps=args.slippage_bps,
        ),
    )
    result = backtester.run(candles)
    print(format_summary(result))
    if args.json_output:
        write_result_json(result, args.json_output)
    return 0


def _parse_strategy_params(items: list[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"strategy param must be key=value, got: {item}")
        key, value = item.split("=", 1)
        params[key] = value
    return params


if __name__ == "__main__":
    raise SystemExit(main())
