"""Base indicator class - plugin pattern."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from src.core.enums import Signal
from src.core.models import IndicatorResult


class Indicator(ABC):
    """Base class for all technical indicators.

    Each indicator must:
    1. Enrich the DataFrame with computed columns (via `compute`)
    2. Analyze the latest data and return an IndicatorResult (via `analyze`)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this indicator."""

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add indicator columns to the DataFrame. Must be idempotent."""

    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> IndicatorResult:
        """Analyze the latest row(s) and return a signal."""

    def _safe_iloc(self, series: pd.Series, index: int, default=None):
        """Safely access a series by iloc index."""
        try:
            val = series.iloc[index]
            if pd.isna(val):
                return default
            return val
        except (IndexError, KeyError):
            return default

    def _make_result(
        self, signal: Signal, value: float = 0.0, **metadata
    ) -> IndicatorResult:
        return IndicatorResult(
            name=self.name,
            signal=signal,
            value=value,
            metadata=metadata,
        )
