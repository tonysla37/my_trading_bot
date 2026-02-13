"""ADI (Accumulation/Distribution Index) indicator."""

from __future__ import annotations

import pandas as pd
import ta

from src.core.enums import Signal

from .base import Indicator


class ADIIndicator(Indicator):
    """ADI with trend direction and strength analysis."""

    name = "adi"

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df["adi"] = ta.volume.acc_dist_index(
            high=df["high"], low=df["low"],
            close=df["close"], volume=df["volume"],
        )
        return df

    def analyze(self, df: pd.DataFrame) -> "IndicatorResult":
        adi = self._safe_iloc(df["adi"], -1)
        prev_adi = self._safe_iloc(df["adi"], -2)

        if adi is None or prev_adi is None:
            return self._make_result(Signal.UNDEFINED, 0.0)

        diff = adi - prev_adi
        strength = "strong" if abs(diff) >= 0.1 else "weak"

        if diff > 0:
            signal = Signal.BULLISH
        elif diff < 0:
            signal = Signal.BEARISH
        else:
            signal = Signal.NEUTRAL

        return self._make_result(signal, adi, prev_adi=prev_adi, strength=strength)
