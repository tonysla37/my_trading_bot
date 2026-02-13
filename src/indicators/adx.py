"""ADX (Average Directional Index) indicator - NEW for v2."""

from __future__ import annotations

import pandas as pd
import ta

from src.core.enums import Signal

from .base import Indicator


class ADXIndicator(Indicator):
    """ADX measures trend strength. Key for Market Regime Detection."""

    name = "adx"

    def __init__(self, window: int = 14):
        self.window = window

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        adx = ta.trend.ADXIndicator(
            high=df["high"], low=df["low"], close=df["close"],
            window=self.window,
        )
        df["adx"] = adx.adx()
        df["adx_pos"] = adx.adx_pos()  # +DI
        df["adx_neg"] = adx.adx_neg()  # -DI
        return df

    def analyze(self, df: pd.DataFrame) -> "IndicatorResult":
        adx = self._safe_iloc(df["adx"], -1)
        plus_di = self._safe_iloc(df["adx_pos"], -1)
        minus_di = self._safe_iloc(df["adx_neg"], -1)

        if any(v is None for v in [adx, plus_di, minus_di]):
            return self._make_result(Signal.UNDEFINED, 0.0)

        # ADX > 25 = strong trend, < 20 = weak/no trend
        if adx > 25:
            signal = Signal.BULLISH if plus_di > minus_di else Signal.BEARISH
            strength = "strong"
        elif adx < 20:
            signal = Signal.NEUTRAL  # No clear trend (range market)
            strength = "weak"
        else:
            signal = Signal.BULLISH if plus_di > minus_di else Signal.BEARISH
            strength = "moderate"

        return self._make_result(
            signal, adx,
            plus_di=plus_di, minus_di=minus_di, strength=strength,
        )
