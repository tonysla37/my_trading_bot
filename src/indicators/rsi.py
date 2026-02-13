"""RSI (Relative Strength Index) indicator."""

from __future__ import annotations

import pandas as pd
import ta

from src.core.enums import Signal

from .base import Indicator


class RSIIndicator(Indicator):
    """RSI with overbought/oversold detection and divergence analysis."""

    name = "rsi"

    def __init__(self, window: int = 14):
        self.window = window

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df["rsi"] = ta.momentum.RSIIndicator(
            close=df["close"], window=self.window
        ).rsi()
        return df

    def analyze(self, df: pd.DataFrame) -> "IndicatorResult":
        rsi = self._safe_iloc(df["rsi"], -1)
        prev_rsi = self._safe_iloc(df["rsi"], -3)

        if rsi is None or prev_rsi is None:
            return self._make_result(Signal.UNDEFINED, 0.0)

        if rsi <= 30:
            signal = Signal.OVERSOLD
        elif rsi >= 70:
            signal = Signal.OVERBOUGHT
        elif rsi > 50:
            signal = Signal.BULLISH if rsi > prev_rsi else Signal.NEUTRAL
        elif rsi < 50:
            signal = Signal.BEARISH if rsi < prev_rsi else Signal.NEUTRAL
        else:
            signal = Signal.NEUTRAL

        return self._make_result(signal, rsi, prev_rsi=prev_rsi)
