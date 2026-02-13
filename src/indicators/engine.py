"""Indicator Engine - orchestrates all indicators via plugin pattern."""

from __future__ import annotations

import logging

import pandas as pd

from src.core.models import IndicatorResult

from .base import Indicator
from .adi import ADIIndicator
from .adx import ADXIndicator
from .bollinger import BollingerIndicator
from .choppiness import ChoppinessIndicator
from .ema import EMAIndicator
from .fear_and_greed import FearAndGreedIndicator
from .fibonacci import FibonacciIndicator
from .macd import MACDIndicator
from .rsi import RSIIndicator
from .sma import SMAIndicator
from .stochastic_rsi import StochasticRSIIndicator
from .support_resistance import SupportResistanceIndicator
from .volume import VolumeIndicator

logger = logging.getLogger(__name__)


class IndicatorEngine:
    """Manages and executes all registered indicators.

    Usage:
        engine = IndicatorEngine.default()
        df = engine.compute_all(df)
        results = engine.analyze_all(df)
    """

    def __init__(self, indicators: list[Indicator] | None = None):
        self._indicators: dict[str, Indicator] = {}
        if indicators:
            for ind in indicators:
                self.register(ind)

    def register(self, indicator: Indicator) -> None:
        """Register an indicator plugin."""
        self._indicators[indicator.name] = indicator
        logger.debug("Registered indicator: %s", indicator.name)

    def unregister(self, name: str) -> None:
        """Remove an indicator."""
        self._indicators.pop(name, None)

    @property
    def names(self) -> list[str]:
        return list(self._indicators.keys())

    def compute_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """Run compute() for all registered indicators, enriching the DataFrame."""
        for name, indicator in self._indicators.items():
            try:
                df = indicator.compute(df)
            except Exception as e:
                logger.error("Error computing indicator %s: %s", name, e)
        return df

    def analyze_all(self, df: pd.DataFrame) -> list[IndicatorResult]:
        """Run analyze() for all registered indicators."""
        results = []
        for name, indicator in self._indicators.items():
            try:
                result = indicator.analyze(df)
                results.append(result)
            except Exception as e:
                logger.error("Error analyzing indicator %s: %s", name, e)
        return results

    def analyze_by_name(self, name: str, df: pd.DataFrame) -> IndicatorResult | None:
        """Analyze a single indicator by name."""
        indicator = self._indicators.get(name)
        if indicator is None:
            return None
        return indicator.analyze(df)

    @classmethod
    def default(cls) -> IndicatorEngine:
        """Create an engine with all default indicators registered."""
        return cls(indicators=[
            ADIIndicator(),
            ADXIndicator(),
            BollingerIndicator(),
            ChoppinessIndicator(),
            EMAIndicator(),
            FearAndGreedIndicator(),
            FibonacciIndicator(),
            MACDIndicator(),
            RSIIndicator(),
            SMAIndicator(),
            StochasticRSIIndicator(),
            SupportResistanceIndicator(),
            VolumeIndicator(),
        ])

    @classmethod
    def fast(cls) -> IndicatorEngine:
        """Create an engine with only fast indicators (no external API calls)."""
        return cls(indicators=[
            ADIIndicator(),
            ADXIndicator(),
            BollingerIndicator(),
            ChoppinessIndicator(),
            EMAIndicator(),
            MACDIndicator(),
            RSIIndicator(),
            SMAIndicator(),
            StochasticRSIIndicator(),
            SupportResistanceIndicator(),
            VolumeIndicator(),
        ])
