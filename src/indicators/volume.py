"""Volume analysis indicator."""

from __future__ import annotations

import pandas as pd

from src.core.enums import Signal

from .base import Indicator


class VolumeIndicator(Indicator):
    """Volume analysis with whale activity detection."""

    name = "volume"

    def __init__(self, short_window: int = 5, long_window: int = 14):
        self.short_window = short_window
        self.long_window = long_window

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df["volume_short_ma"] = df["volume"].rolling(window=self.short_window).mean()
        df["volume_long_ma"] = df["volume"].rolling(window=self.long_window).mean()
        return df

    def analyze(self, df: pd.DataFrame) -> "IndicatorResult":
        current_vol = self._safe_iloc(df["volume"], -1)
        prev_vol = self._safe_iloc(df["volume"], -2)
        long_ma = self._safe_iloc(df["volume_long_ma"], -1)

        if any(v is None for v in [current_vol, prev_vol, long_ma]):
            return self._make_result(Signal.UNDEFINED, 0.0)

        # Trend based on volume vs long-term average
        if current_vol > long_ma:
            signal = Signal.BULLISH
        elif current_vol < long_ma:
            signal = Signal.BEARISH
        else:
            signal = Signal.NEUTRAL

        whale_activity = current_vol > 2 * long_ma
        vol_change = current_vol - prev_vol

        return self._make_result(
            signal, current_vol,
            long_ma=long_ma,
            volume_change=vol_change,
            whale_activity=whale_activity,
        )
