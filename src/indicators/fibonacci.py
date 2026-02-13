"""Fibonacci retracement & extension indicator."""

from __future__ import annotations

import pandas as pd

from src.core.enums import Signal

from .base import Indicator


class FibonacciIndicator(Indicator):
    """Fibonacci retracement and extension levels."""

    name = "fibonacci"

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        # Fibonacci levels are computed on-the-fly in analyze()
        return df

    def analyze(self, df: pd.DataFrame) -> "IndicatorResult":
        price_max = df["close"].max()
        price_min = df["close"].min()
        current = self._safe_iloc(df["close"], -1)

        if any(v is None for v in [price_max, price_min, current]):
            return self._make_result(Signal.UNDEFINED, 0.0)

        diff = price_max - price_min
        levels = {
            "0%": price_max,
            "23.6%": price_max - diff * 0.236,
            "38.2%": price_max - diff * 0.382,
            "50%": price_max - diff * 0.5,
            "61.8%": price_max - diff * 0.618,
            "100%": price_min,
        }
        extensions = {
            "161.8%": price_max + diff * 0.618,
            "261.8%": price_max + diff * 1.618,
        }

        # Signal based on position relative to key levels
        mid = levels["50%"]
        if current > mid:
            signal = Signal.BULLISH
        elif current < mid:
            signal = Signal.BEARISH
        else:
            signal = Signal.NEUTRAL

        return self._make_result(
            signal, current,
            retracement_levels=levels,
            extension_levels=extensions,
        )
