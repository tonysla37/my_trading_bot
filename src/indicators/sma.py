"""SMA (Simple Moving Average) indicator."""

from __future__ import annotations

import pandas as pd
import ta

from src.core.enums import Signal

from .base import Indicator


class SMAIndicator(Indicator):
    """SMA with golden/death cross detection."""

    name = "sma"

    def __init__(self, windows: list[int] | None = None):
        self.windows = windows or [50, 200]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        for w in self.windows:
            df[f"sma{w}"] = ta.trend.SMAIndicator(
                close=df["close"], window=w
            ).sma_indicator()
        return df

    def analyze(self, df: pd.DataFrame) -> "IndicatorResult":
        smas = []
        for w in self.windows:
            val = self._safe_iloc(df[f"sma{w}"], -1)
            if val is None:
                return self._make_result(Signal.UNDEFINED, 0.0)
            smas.append(val)

        # Golden cross: SMA50 > SMA200
        if all(smas[i] > smas[i + 1] for i in range(len(smas) - 1)):
            signal = Signal.BULLISH
        # Death cross: SMA200 > SMA50
        elif smas[-1] > smas[0]:
            signal = Signal.BEARISH
        else:
            signal = Signal.NEUTRAL

        metadata = {f"sma{w}": v for w, v in zip(self.windows, smas)}
        return self._make_result(signal, smas[0], **metadata)
