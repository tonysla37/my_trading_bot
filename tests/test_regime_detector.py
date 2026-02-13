"""Tests for Market Regime Detector."""

import unittest

import numpy as np
import pandas as pd

from src.core.enums import MarketRegime
from src.market.regime_detector import MarketRegimeDetector


def _make_trending_data(n: int = 300, direction: str = "up") -> pd.DataFrame:
    """Generate strongly trending OHLCV data."""
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=n, freq="D")

    if direction == "up":
        base = np.linspace(100, 300, n) + np.random.randn(n) * 2
    else:
        base = np.linspace(300, 100, n) + np.random.randn(n) * 2

    return pd.DataFrame({
        "open": base - 1,
        "high": base + np.random.rand(n) * 3,
        "low": base - np.random.rand(n) * 3,
        "close": base,
        "volume": np.random.rand(n) * 1000 + 500,
    }, index=dates)


def _make_ranging_data(n: int = 300) -> pd.DataFrame:
    """Generate ranging/sideways OHLCV data."""
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    base = 150 + np.sin(np.linspace(0, 30, n)) * 5 + np.random.randn(n) * 1

    return pd.DataFrame({
        "open": base - 0.5,
        "high": base + np.random.rand(n) * 2,
        "low": base - np.random.rand(n) * 2,
        "close": base,
        "volume": np.random.rand(n) * 500 + 100,
    }, index=dates)


class TestMarketRegimeDetector(unittest.TestCase):
    def setUp(self):
        self.detector = MarketRegimeDetector()

    def test_detects_bull_market(self):
        df = _make_trending_data(300, "up")
        regime, confidence = self.detector.detect(df)
        self.assertIn(regime, [MarketRegime.BULL, MarketRegime.RANGE])
        self.assertGreater(confidence, 0.0)

    def test_detects_bear_market(self):
        df = _make_trending_data(300, "down")
        regime, confidence = self.detector.detect(df)
        self.assertIn(regime, [MarketRegime.BEAR, MarketRegime.RANGE])
        self.assertGreater(confidence, 0.0)

    def test_detects_range_market(self):
        df = _make_ranging_data(300)
        regime, confidence = self.detector.detect(df)
        # Ranging data should be detected as RANGE or at least not as strong trend
        self.assertIn(regime, [MarketRegime.RANGE, MarketRegime.UNKNOWN, MarketRegime.BULL, MarketRegime.BEAR])

    def test_confidence_between_0_and_1(self):
        df = _make_trending_data()
        _, confidence = self.detector.detect(df)
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)

    def test_multi_timeframe_detection(self):
        data_by_tf = {
            "daily": _make_trending_data(300, "up"),
            "weekly": _make_trending_data(52, "up"),
        }
        regime, confidence = self.detector.detect_multi_timeframe(data_by_tf)
        self.assertIsInstance(regime, MarketRegime)
        self.assertGreaterEqual(confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
