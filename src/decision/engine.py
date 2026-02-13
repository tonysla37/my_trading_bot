"""Decision Engine - transforms indicator signals into trading decisions."""

from __future__ import annotations

import logging
from math import floor

from src.core.config import ProtectionConfig, RiskProfileConfig
from src.core.enums import MarketRegime, OrderSide, RiskProfile, Signal, TimeFrame
from src.core.models import IndicatorResult, MarketContext, TradeSetup

logger = logging.getLogger(__name__)

# Indicators that contribute to the market trend score
SCORING_INDICATORS = {
    "adi", "bollinger", "ema", "macd", "rsi", "sma",
    "stoch_rsi", "volume", "fear_and_greed",
}


class DecisionEngine:
    """Converts indicator results + market context into trade decisions.

    Supports 4 risk profiles with different position sizing.
    """

    def __init__(
        self,
        risk_profile: RiskProfileConfig | None = None,
        protection: ProtectionConfig | None = None,
    ):
        self.risk_profile = risk_profile or RiskProfileConfig()
        self.protection = protection or ProtectionConfig()

    def compute_market_context(
        self,
        results: list[IndicatorResult],
        regime: MarketRegime = MarketRegime.UNKNOWN,
        regime_confidence: float = 0.0,
    ) -> MarketContext:
        """Score all indicator results and compute overall market context."""
        score = 0
        for r in results:
            if r.name not in SCORING_INDICATORS:
                continue
            if r.signal in (Signal.BULLISH, Signal.OVERSOLD):
                score += 1
            elif r.signal in (Signal.BEARISH, Signal.OVERBOUGHT):
                score -= 1

        if score > 0:
            signal = Signal.BULLISH
        elif score < 0:
            signal = Signal.BEARISH
        else:
            signal = Signal.NEUTRAL

        return MarketContext(
            regime=regime,
            regime_confidence=regime_confidence,
            trend_score=score,
            signal=signal,
            indicators=results,
        )

    def evaluate(
        self,
        context: MarketContext,
        pair: str,
        current_price: float,
        fiat_amount: float,
        crypto_amount: float,
        trade_in_progress: bool,
        timeframe: TimeFrame = TimeFrame.DAILY,
    ) -> TradeSetup | None:
        """Evaluate whether to open/close a position.

        Returns a TradeSetup if a trade should be placed, None otherwise.
        """
        risk = self.risk_profile.risk_per_trade

        # BUY condition: bullish market, no trade in progress, sufficient fiat
        if (
            context.signal == Signal.BULLISH
            and context.trend_score > 0
            and not trade_in_progress
            and fiat_amount > 5
        ):
            quantity = (fiat_amount * risk) / current_price
            sl_price = current_price * (1 - self.protection.sl_level)
            tp_price = current_price * (1 + self.protection.tp1_level)
            possible_gain = (tp_price - current_price) * quantity
            possible_loss = (current_price - sl_price) * quantity
            rr_ratio = possible_gain / possible_loss if possible_loss > 0 else 0

            return TradeSetup(
                side=OrderSide.BUY,
                pair=pair,
                entry_price=current_price,
                quantity=quantity,
                stop_loss=sl_price,
                take_profit=tp_price,
                risk_reward_ratio=rr_ratio,
                risk_profile=RiskProfile(self.risk_profile.name),
                timeframe=timeframe,
                regime=context.regime,
                confidence=context.regime_confidence,
            )

        # SELL condition: bearish market, trade in progress, sufficient crypto
        min_token = 5 / current_price
        if (
            context.signal == Signal.BEARISH
            and context.trend_score < 0
            and trade_in_progress
            and crypto_amount > min_token
        ):
            quantity = (fiat_amount * risk) / current_price

            return TradeSetup(
                side=OrderSide.SELL,
                pair=pair,
                entry_price=current_price,
                quantity=quantity,
                stop_loss=0.0,
                take_profit=0.0,
                risk_reward_ratio=0.0,
                risk_profile=RiskProfile(self.risk_profile.name),
                timeframe=timeframe,
                regime=context.regime,
                confidence=context.regime_confidence,
            )

        logger.info("No trade opportunity (score=%d, signal=%s)", context.trend_score, context.signal.value)
        return None
