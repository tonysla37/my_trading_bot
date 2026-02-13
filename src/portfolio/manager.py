"""Portfolio Manager - orchestrates specialist bots and manages capital allocation."""

from __future__ import annotations

import logging

from src.core.config import Settings
from src.core.enums import MarketRegime, OrderSide, RiskProfile
from src.core.models import MarketContext, PortfolioState, TradeResult, TradeSetup
from src.market.regime_detector import MarketRegimeDetector
from src.strategies.base import Strategy
from src.strategies.bull import BullMarketStrategy
from src.strategies.bear import BearMarketStrategy
from src.strategies.range_strategy import RangeStrategy

logger = logging.getLogger(__name__)


class PortfolioManager:
    """Orchestrates multiple specialist bots based on market regime.

    Responsibilities:
    - Route to the correct strategy based on detected regime
    - Manage capital allocation between strategies
    - Track portfolio state (balances, consecutive losses)
    - Handle regime transitions gracefully
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.regime_detector = MarketRegimeDetector()
        self.strategies: dict[MarketRegime, Strategy] = {
            MarketRegime.BULL: BullMarketStrategy(),
            MarketRegime.BEAR: BearMarketStrategy(),
            MarketRegime.RANGE: RangeStrategy(),
        }
        self._current_regime = MarketRegime.UNKNOWN
        self._regime_confidence = 0.0

    def evaluate(
        self,
        context: MarketContext,
        portfolio: PortfolioState,
    ) -> TradeSetup | None:
        """Main entry point: detect regime and delegate to specialist strategy."""
        self._current_regime = context.regime
        self._regime_confidence = context.regime_confidence

        # Select the appropriate strategy
        strategy = self.strategies.get(context.regime)
        if strategy is None:
            logger.info("No strategy for regime %s, holding", context.regime.value)
            return None

        if not strategy.should_activate(context.regime, context.regime_confidence):
            logger.info(
                "Strategy %s not confident enough (%.2f)",
                strategy.name, context.regime_confidence,
            )
            return None

        logger.info(
            "Activating %s strategy (regime=%s, confidence=%.2f)",
            strategy.name, context.regime.value, context.regime_confidence,
        )
        return strategy.evaluate(context, portfolio)

    def update_after_trade(
        self, portfolio: PortfolioState, result: TradeResult,
    ) -> PortfolioState:
        """Update portfolio state after a trade is executed."""
        portfolio.fiat_amount = result.fiat_after
        portfolio.crypto_amount = result.crypto_after
        portfolio.trade_in_progress = result.trade_in_progress

        # Track consecutive losses for risk reduction
        if result.side == OrderSide.SELL:
            pnl = result.fiat_after - portfolio.fiat_amount
            if pnl < 0:
                portfolio.consecutive_losses += 1
                logger.warning(
                    "Trade loss detected. Consecutive losses: %d",
                    portfolio.consecutive_losses,
                )
            else:
                portfolio.consecutive_losses = 0

        return portfolio

    @property
    def current_regime(self) -> MarketRegime:
        return self._current_regime

    @property
    def regime_confidence(self) -> float:
        return self._regime_confidence
