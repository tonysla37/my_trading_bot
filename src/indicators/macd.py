"""MACD (Moving Average Convergence Divergence) indicator."""

from __future__ import annotations

import pandas as pd
import ta

from src.core.enums import Signal

from .base import Indicator


class MACDIndicator(Indicator):
    """MACD with crossover and divergence detection."""

    name = "macd"

    def __init__(self, fast: int = 12, slow: int = 26, signal_window: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal_window = signal_window

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        macd = ta.trend.MACD(
            close=df["close"],
            window_fast=self.fast,
            window_slow=self.slow,
            window_sign=self.signal_window,
        )
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_histo"] = macd.macd_diff()
        return df

    def analyze(self, df: pd.DataFrame) -> "IndicatorResult":
        macd = self._safe_iloc(df["macd"], -1)
        signal_line = self._safe_iloc(df["macd_signal"], -1)
        prev_macd = self._safe_iloc(df["macd"], -2)
        prev_signal = self._safe_iloc(df["macd_signal"], -2)
        histogram = self._safe_iloc(df["macd_histo"], -1)

        if any(v is None for v in [macd, signal_line, prev_macd, prev_signal]):
            return self._make_result(Signal.UNDEFINED, 0.0)

        # Crossover detection
        bullish_cross = prev_macd < prev_signal and macd > signal_line
        bearish_cross = prev_macd > prev_signal and macd < signal_line

        if macd > 0 and (bullish_cross or macd > signal_line):
            signal = Signal.BULLISH
        elif macd < 0 and (bearish_cross or macd < signal_line):
            signal = Signal.BEARISH
        else:
            signal = Signal.NEUTRAL

        return self._make_result(
            signal, macd,
            signal_line=signal_line,
            histogram=histogram,
            bullish_cross=bullish_cross,
            bearish_cross=bearish_cross,
        )
