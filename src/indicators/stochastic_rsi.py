"""Stochastic RSI indicator."""

from __future__ import annotations

import pandas as pd
import ta

from src.core.enums import Signal

from .base import Indicator


class StochasticRSIIndicator(Indicator):
    """Stochastic oscillator with overbought/oversold and divergence."""

    name = "stoch_rsi"

    def __init__(self, window: int = 14, smooth_window: int = 3):
        self.window = window
        self.smooth_window = smooth_window

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        stoch = ta.momentum.StochasticOscillator(
            high=df["high"], low=df["low"], close=df["close"],
            window=self.window, smooth_window=self.smooth_window,
        )
        df["stochastic"] = stoch.stoch()
        df["stoch_signal"] = stoch.stoch_signal()
        return df

    def analyze(self, df: pd.DataFrame) -> "IndicatorResult":
        blue = self._safe_iloc(df["stochastic"], -1)
        orange = self._safe_iloc(df["stoch_signal"], -1)
        prev_blue = self._safe_iloc(df["stochastic"], -3)
        prev_orange = self._safe_iloc(df["stoch_signal"], -3)

        if any(v is None for v in [blue, orange, prev_blue, prev_orange]):
            return self._make_result(Signal.UNDEFINED, 0.0)

        if blue <= 20 or orange <= 20:
            signal = Signal.OVERSOLD
        elif blue >= 80 or orange >= 80:
            signal = Signal.OVERBOUGHT
        elif blue > orange:
            signal = Signal.BULLISH
        elif blue < orange:
            signal = Signal.BEARISH
        else:
            signal = Signal.NEUTRAL

        return self._make_result(
            signal, blue,
            signal_line=orange,
            prev_blue=prev_blue,
            prev_orange=prev_orange,
        )
