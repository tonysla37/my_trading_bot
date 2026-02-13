"""Bull Market Strategy - trend following with Fibonacci trailing SL."""

from __future__ import annotations

import logging

from src.core.enums import MarketRegime, OrderSide, RiskProfile, Signal, TimeFrame
from src.core.models import MarketContext, PortfolioState, TradeSetup

from .base import Strategy

logger = logging.getLogger(__name__)


class BullMarketStrategy(Strategy):
    """Strategy optimized for bull markets.

    Characteristics:
    - Trend following (buy the dip)
    - Uses Fibonacci retracement for entries
    - Wider take-profit targets
    - Trailing stop-loss based on ATR
    - Higher risk tolerance
    """

    name = "bull_market"
    target_regime = MarketRegime.BULL

    def __init__(
        self,
        risk_per_trade: float = 0.02,
        sl_level: float = 0.03,  # 3% SL (wider in bull)
        tp_level: float = 0.15,  # 15% TP (aggressive in bull)
    ):
        self.risk_per_trade = risk_per_trade
        self.sl_level = sl_level
        self.tp_level = tp_level

    def evaluate(
        self,
        context: MarketContext,
        portfolio: PortfolioState,
    ) -> TradeSetup | None:
        # Only act on bullish signals in bull market
        if context.signal != Signal.BULLISH or context.trend_score <= 0:
            return None

        if portfolio.trade_in_progress:
            return None

        if portfolio.fiat_amount < 5:
            return None

        price = portfolio.current_price
        quantity = (portfolio.fiat_amount * self.risk_per_trade) / price
        sl = price * (1 - self.sl_level)
        tp = price * (1 + self.tp_level)

        # Use Fibonacci levels if available
        for ind in context.indicators:
            if ind.name == "fibonacci":
                levels = ind.metadata.get("retracement_levels", {})
                fib_382 = levels.get("38.2%")
                if fib_382 and price <= fib_382 * 1.02:
                    # Near Fibonacci 38.2% retracement - good entry
                    logger.info("Bull entry near Fibonacci 38.2%% level")
                    quantity *= 1.2  # Slightly larger position
                break

        possible_gain = (tp - price) * quantity
        possible_loss = (price - sl) * quantity
        rr = possible_gain / possible_loss if possible_loss > 0 else 0

        return TradeSetup(
            side=OrderSide.BUY,
            pair=portfolio.pair,
            entry_price=price,
            quantity=quantity,
            stop_loss=sl,
            take_profit=tp,
            risk_reward_ratio=rr,
            risk_profile=portfolio.risk_profile,
            timeframe=TimeFrame.DAILY,
            regime=MarketRegime.BULL,
            confidence=context.regime_confidence,
        )
