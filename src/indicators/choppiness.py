"""Choppiness Index indicator."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.core.enums import Signal

from .base import Indicator


class ChoppinessIndicator(Indicator):
    """Choppiness Index - measures whether market is trending or ranging."""

    name = "choppiness"

    def __init__(self, window: int = 14):
        self.window = window

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        tr1 = df["high"] - df["low"]
        tr2 = (df["high"] - df["close"].shift(1)).abs()
        tr3 = (df["low"] - df["close"].shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(1).mean()

        high_max = df["high"].rolling(self.window).max()
        low_min = df["low"].rolling(self.window).min()

        denominator = high_max - low_min
        denominator = denominator.replace(0, np.nan)

        df["chop"] = (
            100
            * np.log10(atr.rolling(self.window).sum() / denominator)
            / np.log10(self.window)
        )
        return df

    def analyze(self, df: pd.DataFrame) -> "IndicatorResult":
        chop = self._safe_iloc(df["chop"], -1)
        if chop is None:
            return self._make_result(Signal.UNDEFINED, 0.0)

        # CHOP > 61.8 = choppy/ranging, CHOP < 38.2 = trending
        if chop > 61.8:
            signal = Signal.NEUTRAL  # Market is ranging
            state = "ranging"
        elif chop < 38.2:
            signal = Signal.BULLISH  # Market is trending (direction TBD by other indicators)
            state = "trending"
        else:
            signal = Signal.NEUTRAL
            state = "transitioning"

        return self._make_result(signal, chop, state=state)
