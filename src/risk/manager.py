"""Risk Management module - position sizing, risk reduction, leverage safety."""

from __future__ import annotations

import logging
from math import floor

from src.core.config import ProtectionConfig, RiskProfileConfig
from src.core.enums import OrderSide
from src.core.models import PortfolioState, TradeSetup

logger = logging.getLogger(__name__)

# After N consecutive losses, reduce risk by this factor
CONSECUTIVE_LOSS_THRESHOLD = 3
RISK_REDUCTION_FACTOR = 0.5


class RiskManager:
    """Manages position sizing, risk reduction, and leverage safety.

    Features:
    - Position sizing based on risk profile
    - Automatic risk reduction after consecutive losses
    - Leverage safety: SL must be placed before liquidation price
    - Maximum position size as percentage of portfolio
    """

    def __init__(self, risk_profile: RiskProfileConfig, protection: ProtectionConfig):
        self.risk_profile = risk_profile
        self.protection = protection

    def compute_position_size(
        self,
        portfolio: PortfolioState,
        entry_price: float,
    ) -> float:
        """Calculate position size in crypto units."""
        risk = self._effective_risk(portfolio.consecutive_losses)
        capital = portfolio.fiat_amount
        leverage = self.risk_profile.max_leverage

        # Position size = (capital * risk%) / entry_price * leverage
        raw_size = (capital * risk * leverage) / entry_price

        # Cap at max_position_pct of total portfolio
        max_value = portfolio.total_value * self.risk_profile.max_position_pct
        max_size = max_value / entry_price
        size = min(raw_size, max_size)

        return self._truncate(size, 5)

    def compute_stop_loss(self, entry_price: float, side: OrderSide) -> float:
        """Compute stop-loss price."""
        if side == OrderSide.BUY:
            sl = entry_price * (1 - self.protection.sl_level)
        else:
            sl = entry_price * (1 + self.protection.sl_level)

        # Leverage safety: ensure SL is triggered before liquidation
        if self.risk_profile.max_leverage > 1:
            liquidation_distance = 1 / self.risk_profile.max_leverage
            if side == OrderSide.BUY:
                liquidation_price = entry_price * (1 - liquidation_distance)
                # SL must be above liquidation price (with margin)
                min_sl = liquidation_price * 1.05
                sl = max(sl, min_sl)
            else:
                liquidation_price = entry_price * (1 + liquidation_distance)
                max_sl = liquidation_price * 0.95
                sl = min(sl, max_sl)

        return sl

    def compute_take_profit(self, entry_price: float, side: OrderSide) -> float:
        """Compute take-profit price."""
        if side == OrderSide.BUY:
            return entry_price * (1 + self.protection.tp1_level)
        else:
            return entry_price * (1 - self.protection.tp1_level)

    def validate_trade(self, setup: TradeSetup, portfolio: PortfolioState) -> bool:
        """Validate a trade setup against risk rules."""
        # Check minimum fiat for buy
        if setup.side == OrderSide.BUY and portfolio.fiat_amount < 5:
            logger.warning("Insufficient fiat for trade: %.2f", portfolio.fiat_amount)
            return False

        # Check minimum crypto for sell
        min_token = 5 / setup.entry_price
        if setup.side == OrderSide.SELL and portfolio.crypto_amount < min_token:
            logger.warning("Insufficient crypto for trade: %.6f", portfolio.crypto_amount)
            return False

        # Check risk-reward ratio (minimum 1.5 for leveraged trades)
        if self.risk_profile.max_leverage > 1 and setup.risk_reward_ratio < 1.5:
            logger.warning("R:R too low for leveraged trade: %.2f", setup.risk_reward_ratio)
            return False

        return True

    def _effective_risk(self, consecutive_losses: int) -> float:
        """Reduce risk after consecutive losses."""
        risk = self.risk_profile.risk_per_trade
        if consecutive_losses >= CONSECUTIVE_LOSS_THRESHOLD:
            risk *= RISK_REDUCTION_FACTOR
            logger.warning(
                "Risk reduced to %.1f%% after %d consecutive losses",
                risk * 100, consecutive_losses,
            )
        return risk

    @staticmethod
    def _truncate(n: float, decimals: int = 0) -> float:
        return floor(float(n) * 10**decimals) / 10**decimals
