"""Bear Market Strategy - defensive with quick take-profits."""

from __future__ import annotations

import logging

from src.core.enums import MarketRegime, OrderSide, RiskProfile, Signal, TimeFrame
from src.core.models import MarketContext, PortfolioState, TradeSetup

from .base import Strategy

logger = logging.getLogger(__name__)


class BearMarketStrategy(Strategy):
    """Strategy optimized for bear markets.

    Characteristics:
    - Defensive posture
    - Quick take-profit targets (lock in gains)
    - Tight stop-losses
    - Smaller position sizes
    - Prioritizes selling/closing positions
    """

    name = "bear_market"
    target_regime = MarketRegime.BEAR

    def __init__(
        self,
        risk_per_trade: float = 0.01,  # Conservative
        sl_level: float = 0.015,  # 1.5% SL (tight)
        tp_level: float = 0.05,   # 5% TP (quick exit)
    ):
        self.risk_per_trade = risk_per_trade
        self.sl_level = sl_level
        self.tp_level = tp_level

    def evaluate(
        self,
        context: MarketContext,
        portfolio: PortfolioState,
    ) -> TradeSetup | None:
        price = portfolio.current_price
        min_token = 5 / price

        # Priority: close existing positions in bear market
        if portfolio.trade_in_progress and portfolio.crypto_amount > min_token:
            if context.signal == Signal.BEARISH and context.trend_score < -1:
                logger.info("Bear strategy: closing position (defensive)")
                return TradeSetup(
                    side=OrderSide.SELL,
                    pair=portfolio.pair,
                    entry_price=price,
                    quantity=portfolio.crypto_amount,
                    stop_loss=0.0,
                    take_profit=0.0,
                    risk_reward_ratio=0.0,
                    risk_profile=portfolio.risk_profile,
                    timeframe=TimeFrame.DAILY,
                    regime=MarketRegime.BEAR,
                    confidence=context.regime_confidence,
                )

        # Only enter new positions on very strong oversold signals
        if (
            not portfolio.trade_in_progress
            and portfolio.fiat_amount > 5
            and context.trend_score > 2  # Need strong reversal signal
        ):
            quantity = (portfolio.fiat_amount * self.risk_per_trade) / price
            sl = price * (1 - self.sl_level)
            tp = price * (1 + self.tp_level)
            possible_gain = (tp - price) * quantity
            possible_loss = (price - sl) * quantity
            rr = possible_gain / possible_loss if possible_loss > 0 else 0

            if rr >= 2.0:  # Only enter with good R:R in bear
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
                    regime=MarketRegime.BEAR,
                    confidence=context.regime_confidence,
                )

        return None
