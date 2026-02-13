"""Bollinger Bands indicator."""

from __future__ import annotations

import pandas as pd
import ta

from src.core.enums import Signal

from .base import Indicator


class BollingerIndicator(Indicator):
    """Bollinger Bands with overbought/oversold and volatility analysis."""

    name = "bollinger"

    def __init__(self, window: int = 20, window_dev: int = 2):
        self.window = window
        self.window_dev = window_dev

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        bb = ta.volatility.BollingerBands(
            close=df["close"], window=self.window, window_dev=self.window_dev
        )
        df["bol_high"] = bb.bollinger_hband()
        df["bol_low"] = bb.bollinger_lband()
        df["bol_medium"] = bb.bollinger_mavg()
        df["bol_gap"] = bb.bollinger_wband()
        return df

    def analyze(self, df: pd.DataFrame) -> "IndicatorResult":
        close = self._safe_iloc(df["close"], -1)
        high = self._safe_iloc(df["bol_high"], -1)
        low = self._safe_iloc(df["bol_low"], -1)
        avg = self._safe_iloc(df["bol_medium"], -1)

        if any(v is None for v in [close, high, low, avg]):
            return self._make_result(Signal.UNDEFINED, 0.0)

        spread = high - low
        volatility_pct = (spread / close) * 100 if close else 0

        if close > high:
            signal = Signal.OVERBOUGHT
        elif close < low:
            signal = Signal.OVERSOLD
        elif close > avg:
            signal = Signal.BULLISH
        else:
            signal = Signal.BEARISH

        return self._make_result(
            signal, close,
            upper=high, lower=low, middle=avg,
            volatility_pct=volatility_pct,
        )
