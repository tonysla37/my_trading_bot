"""Range Market Strategy - mean reversion between support and resistance."""

from __future__ import annotations

import logging

from src.core.enums import MarketRegime, OrderSide, Signal, TimeFrame
from src.core.models import MarketContext, PortfolioState, TradeSetup

from .base import Strategy

logger = logging.getLogger(__name__)


class RangeStrategy(Strategy):
    """Strategy optimized for ranging/sideways markets.

    Characteristics:
    - Mean reversion approach
    - Buy at support, sell at resistance
    - Uses Bollinger Bands for entry/exit
    - Moderate position sizes
    - Tight profit targets (range width)
    """

    name = "range_market"
    target_regime = MarketRegime.RANGE

    def __init__(
        self,
        risk_per_trade: float = 0.015,
        sl_level: float = 0.02,
        tp_level: float = 0.04,
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

        # Find support/resistance and Bollinger from indicators
        support = None
        resistance = None
        bol_signal = None

        for ind in context.indicators:
            if ind.name == "support_resistance":
                support = ind.metadata.get("support")
                resistance = ind.metadata.get("resistance")
            elif ind.name == "bollinger":
                bol_signal = ind.signal

        # Buy near support (oversold / lower Bollinger)
        if (
            not portfolio.trade_in_progress
            and portfolio.fiat_amount > 5
            and bol_signal in (Signal.OVERSOLD, Signal.BEARISH)
            and support is not None
            and price <= support * 1.02  # Within 2% of support
        ):
            quantity = (portfolio.fiat_amount * self.risk_per_trade) / price
            sl = price * (1 - self.sl_level)
            # Target = resistance or Bollinger TP
            tp_price = resistance if resistance else price * (1 + self.tp_level)
            tp = min(tp_price, price * (1 + self.tp_level))

            possible_gain = (tp - price) * quantity
            possible_loss = (price - sl) * quantity
            rr = possible_gain / possible_loss if possible_loss > 0 else 0

            logger.info("Range strategy: buying near support (%.2f)", price)
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
                regime=MarketRegime.RANGE,
                confidence=context.regime_confidence,
            )

        # Sell near resistance (overbought / upper Bollinger)
        min_token = 5 / price
        if (
            portfolio.trade_in_progress
            and portfolio.crypto_amount > min_token
            and bol_signal in (Signal.OVERBOUGHT, Signal.BULLISH)
            and resistance is not None
            and price >= resistance * 0.98  # Within 2% of resistance
        ):
            logger.info("Range strategy: selling near resistance (%.2f)", price)
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
                regime=MarketRegime.RANGE,
                confidence=context.regime_confidence,
            )

        return None
