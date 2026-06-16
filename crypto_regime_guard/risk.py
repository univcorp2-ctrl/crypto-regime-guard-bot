from __future__ import annotations

from dataclasses import dataclass

from crypto_regime_guard.models import Signal


@dataclass(frozen=True)
class RiskConfig:
    min_quote_order: float = 10.0
    max_single_trade_quote: float = 50.0
    max_risk_score: float = 85.0
    allow_live_market_orders: bool = True


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: str
    adjusted_quote_order: float


class RiskManager:
    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or RiskConfig()

    def evaluate(self, signal: Signal, requested_quote_order: float, live: bool) -> RiskDecision:
        if signal.action == "HOLD":
            return RiskDecision(False, "no trade signal", 0.0)
        if signal.risk_score > self.config.max_risk_score:
            return RiskDecision(False, "risk score above max threshold", 0.0)
        if signal.action == "BUY" and requested_quote_order < self.config.min_quote_order:
            return RiskDecision(False, "quote order below minimum", 0.0)
        if live and not self.config.allow_live_market_orders:
            return RiskDecision(False, "live market orders disabled by risk config", 0.0)
        adjusted = min(requested_quote_order, self.config.max_single_trade_quote)
        return RiskDecision(True, "risk checks passed", adjusted)
