"""EMA (Exponential Moving Average) indicator."""

from __future__ import annotations

import pandas as pd
import ta

from src.core.enums import Signal

from .base import Indicator


class EMAIndicator(Indicator):
    """EMA with trend detection based on ordering of multiple EMAs."""

    name = "ema"

    def __init__(self, windows: list[int] | None = None):
        self.windows = windows or [5, 10, 20, 50]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        for w in self.windows:
            df[f"ema{w}"] = ta.trend.EMAIndicator(
                close=df["close"], window=w
            ).ema_indicator()
        return df

    def analyze(self, df: pd.DataFrame) -> "IndicatorResult":
        emas = []
        for w in self.windows:
            val = self._safe_iloc(df[f"ema{w}"], -1)
            if val is None:
                return self._make_result(Signal.UNDEFINED, 0.0)
            emas.append(val)

        # Bullish: short EMAs > long EMAs (perfectly ordered)
        if all(emas[i] > emas[i + 1] for i in range(len(emas) - 1)):
            signal = Signal.BULLISH
        # Bearish: long EMAs > short EMAs
        elif emas[-1] > emas[0]:
            signal = Signal.BEARISH
        else:
            signal = Signal.NEUTRAL

        metadata = {f"ema{w}": v for w, v in zip(self.windows, emas)}
        return self._make_result(signal, emas[0], **metadata)
