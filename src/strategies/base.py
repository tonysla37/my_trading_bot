"""Base strategy class for specialist bots."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.enums import MarketRegime
from src.core.models import MarketContext, TradeSetup, PortfolioState


class Strategy(ABC):
    """Base class for market-specific trading strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name."""

    @property
    @abstractmethod
    def target_regime(self) -> MarketRegime:
        """The market regime this strategy is designed for."""

    @abstractmethod
    def evaluate(
        self,
        context: MarketContext,
        portfolio: PortfolioState,
    ) -> TradeSetup | None:
        """Evaluate market conditions and return a trade setup if applicable."""

    def should_activate(self, regime: MarketRegime, confidence: float) -> bool:
        """Whether this strategy should be active given the current regime."""
        return regime == self.target_regime and confidence > 0.3
