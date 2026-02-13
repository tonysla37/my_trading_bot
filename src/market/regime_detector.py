"""Market Regime Detector - top-down multi-timeframe analysis.

Detects 4 market regimes:
- BULL: Strong uptrend (ADX > 25, +DI > -DI, EMA bullish alignment)
- BEAR: Strong downtrend (ADX > 25, -DI > +DI, EMA bearish alignment)
- RANGE: Sideways market (ADX < 20, CHOP > 61.8)
- UNKNOWN: Insufficient data or transitioning
"""

from __future__ import annotations

import logging

import pandas as pd

from src.core.enums import MarketRegime, Signal
from src.core.models import IndicatorResult
from src.indicators.adx import ADXIndicator
from src.indicators.choppiness import ChoppinessIndicator
from src.indicators.ema import EMAIndicator
from src.indicators.bollinger import BollingerIndicator

logger = logging.getLogger(__name__)


class MarketRegimeDetector:
    """Detects the current market regime using multiple indicators.

    Uses a top-down approach:
    1. ADX for trend strength
    2. +DI / -DI for trend direction
    3. CHOP for ranging detection
    4. EMA alignment for confirmation
    """

    def __init__(self):
        self._adx = ADXIndicator(window=14)
        self._chop = ChoppinessIndicator(window=14)
        self._ema = EMAIndicator(windows=[5, 10, 20, 50])
        self._bollinger = BollingerIndicator()

    def detect(self, df: pd.DataFrame) -> tuple[MarketRegime, float]:
        """Detect market regime and return (regime, confidence).

        confidence is a float from 0.0 to 1.0.
        """
        # Ensure indicators are computed
        df = self._adx.compute(df)
        df = self._chop.compute(df)
        df = self._ema.compute(df)
        df = self._bollinger.compute(df)

        adx_result = self._adx.analyze(df)
        chop_result = self._chop.analyze(df)
        ema_result = self._ema.analyze(df)

        adx_value = adx_result.value
        adx_strength = adx_result.metadata.get("strength", "weak")
        plus_di = adx_result.metadata.get("plus_di", 0)
        minus_di = adx_result.metadata.get("minus_di", 0)
        chop_value = chop_result.value
        chop_state = chop_result.metadata.get("state", "transitioning")

        # Decision tree for regime detection
        if adx_value > 25 and adx_strength == "strong":
            # Strong trend detected
            if plus_di > minus_di and ema_result.signal == Signal.BULLISH:
                confidence = min(adx_value / 50, 1.0)
                return MarketRegime.BULL, confidence
            elif minus_di > plus_di and ema_result.signal == Signal.BEARISH:
                confidence = min(adx_value / 50, 1.0)
                return MarketRegime.BEAR, confidence

        if adx_value < 20 and chop_value > 61.8:
            # Ranging market confirmed
            confidence = min(chop_value / 100, 1.0)
            return MarketRegime.RANGE, confidence

        # Moderate trend
        if adx_value > 20:
            if plus_di > minus_di:
                confidence = (adx_value - 20) / 30  # 0 at 20, 0.33 at 30
                return MarketRegime.BULL, min(confidence, 0.6)
            else:
                confidence = (adx_value - 20) / 30
                return MarketRegime.BEAR, min(confidence, 0.6)

        # Choppy/transitioning
        if chop_state == "ranging":
            return MarketRegime.RANGE, 0.4

        return MarketRegime.UNKNOWN, 0.0

    def detect_multi_timeframe(
        self, data_by_timeframe: dict[str, pd.DataFrame]
    ) -> tuple[MarketRegime, float]:
        """Top-down multi-timeframe regime detection.

        Higher timeframes have more weight in the final decision.
        """
        weights = {
            "monthly": 3.0,
            "weekly": 2.5,
            "daily": 2.0,
            "intraday": 1.0,
            "scalping": 0.5,
        }

        regime_scores = {
            MarketRegime.BULL: 0.0,
            MarketRegime.BEAR: 0.0,
            MarketRegime.RANGE: 0.0,
            MarketRegime.UNKNOWN: 0.0,
        }

        total_weight = 0.0
        for tf_name, df in data_by_timeframe.items():
            weight = weights.get(tf_name, 1.0)
            regime, confidence = self.detect(df)
            regime_scores[regime] += weight * confidence
            total_weight += weight

        if total_weight == 0:
            return MarketRegime.UNKNOWN, 0.0

        # Normalize scores
        for regime in regime_scores:
            regime_scores[regime] /= total_weight

        # Pick the regime with the highest score
        best_regime = max(regime_scores, key=regime_scores.get)
        best_score = regime_scores[best_regime]

        logger.info(
            "Multi-TF regime detection: %s (confidence=%.2f) | scores=%s",
            best_regime.value, best_score,
            {k.value: f"{v:.2f}" for k, v in regime_scores.items()},
        )

        return best_regime, best_score
