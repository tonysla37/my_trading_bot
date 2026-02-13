"""Support and Resistance indicator."""

from __future__ import annotations

import pandas as pd

from src.core.enums import Signal

from .base import Indicator


class SupportResistanceIndicator(Indicator):
    """Support/Resistance levels with breakout detection."""

    name = "support_resistance"

    def __init__(self, period: int = 20):
        self.period = period

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df["resistance"] = df["close"].rolling(window=self.period).max().shift(1)
        df["support"] = df["close"].rolling(window=self.period).min().shift(1)
        return df

    def analyze(self, df: pd.DataFrame) -> "IndicatorResult":
        price = self._safe_iloc(df["close"], -1)
        support = self._safe_iloc(df["support"], -1)
        resistance = self._safe_iloc(df["resistance"], -1)

        if any(v is None for v in [price, support, resistance]):
            return self._make_result(Signal.UNDEFINED, 0.0)

        if price > resistance:
            signal = Signal.BULLISH  # Breakout above resistance
        elif price < support:
            signal = Signal.BEARISH  # Breakdown below support
        else:
            signal = Signal.NEUTRAL

        return self._make_result(
            signal, price, support=support, resistance=resistance,
        )
