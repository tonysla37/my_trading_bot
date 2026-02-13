"""Tests for the indicator engine and individual indicators."""

import unittest

import numpy as np
import pandas as pd

from src.core.enums import Signal
from src.indicators.engine import IndicatorEngine
from src.indicators.rsi import RSIIndicator
from src.indicators.macd import MACDIndicator
from src.indicators.bollinger import BollingerIndicator
from src.indicators.ema import EMAIndicator
from src.indicators.sma import SMAIndicator
from src.indicators.adi import ADIIndicator
from src.indicators.stochastic_rsi import StochasticRSIIndicator
from src.indicators.volume import VolumeIndicator
from src.indicators.support_resistance import SupportResistanceIndicator
from src.indicators.fibonacci import FibonacciIndicator
from src.indicators.choppiness import ChoppinessIndicator
from src.indicators.adx import ADXIndicator


def _make_ohlcv(n: int = 300, trend: str = "up") -> pd.DataFrame:
    """Generate synthetic OHLCV data for testing."""
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=n, freq="D")

    if trend == "up":
        base = np.linspace(100, 200, n) + np.random.randn(n) * 3
    elif trend == "down":
        base = np.linspace(200, 100, n) + np.random.randn(n) * 3
    else:  # range
        base = 150 + np.sin(np.linspace(0, 20, n)) * 10 + np.random.randn(n) * 2

    df = pd.DataFrame({
        "open": base - np.random.rand(n) * 2,
        "high": base + np.random.rand(n) * 5,
        "low": base - np.random.rand(n) * 5,
        "close": base,
        "volume": np.random.rand(n) * 1000 + 100,
    }, index=dates)
    return df


class TestIndicatorEngine(unittest.TestCase):
    def test_default_engine_has_all_indicators(self):
        engine = IndicatorEngine.default()
        self.assertGreaterEqual(len(engine.names), 12)

    def test_fast_engine_excludes_external(self):
        engine = IndicatorEngine.fast()
        self.assertNotIn("fear_and_greed", engine.names)
        self.assertNotIn("fibonacci", engine.names)

    def test_compute_and_analyze(self):
        engine = IndicatorEngine.fast()
        df = _make_ohlcv(300, "up")
        df = engine.compute_all(df)
        results = engine.analyze_all(df)
        self.assertGreater(len(results), 0)
        for r in results:
            self.assertIsNotNone(r.signal)
            self.assertIsNotNone(r.name)

    def test_register_unregister(self):
        engine = IndicatorEngine()
        self.assertEqual(len(engine.names), 0)
        engine.register(RSIIndicator())
        self.assertEqual(len(engine.names), 1)
        engine.unregister("rsi")
        self.assertEqual(len(engine.names), 0)


class TestRSI(unittest.TestCase):
    def test_compute_adds_column(self):
        rsi = RSIIndicator()
        df = _make_ohlcv()
        df = rsi.compute(df)
        self.assertIn("rsi", df.columns)

    def test_analyze_uptrend(self):
        rsi = RSIIndicator()
        df = _make_ohlcv(300, "up")
        df = rsi.compute(df)
        result = rsi.analyze(df)
        # In an uptrend, RSI should be bullish or overbought
        self.assertIn(result.signal, [Signal.BULLISH, Signal.OVERBOUGHT, Signal.NEUTRAL])


class TestMACD(unittest.TestCase):
    def test_compute_adds_columns(self):
        macd = MACDIndicator()
        df = _make_ohlcv()
        df = macd.compute(df)
        self.assertIn("macd", df.columns)
        self.assertIn("macd_signal", df.columns)
        self.assertIn("macd_histo", df.columns)


class TestBollinger(unittest.TestCase):
    def test_compute_adds_columns(self):
        bb = BollingerIndicator()
        df = _make_ohlcv()
        df = bb.compute(df)
        self.assertIn("bol_high", df.columns)
        self.assertIn("bol_low", df.columns)
        self.assertIn("bol_medium", df.columns)


class TestEMA(unittest.TestCase):
    def test_compute_adds_columns(self):
        ema = EMAIndicator(windows=[5, 10, 20, 50])
        df = _make_ohlcv()
        df = ema.compute(df)
        for w in [5, 10, 20, 50]:
            self.assertIn(f"ema{w}", df.columns)

    def test_analyze_uptrend_is_bullish(self):
        ema = EMAIndicator()
        df = _make_ohlcv(300, "up")
        df = ema.compute(df)
        result = ema.analyze(df)
        self.assertEqual(result.signal, Signal.BULLISH)


class TestSMA(unittest.TestCase):
    def test_compute_adds_columns(self):
        sma = SMAIndicator()
        df = _make_ohlcv()
        df = sma.compute(df)
        self.assertIn("sma50", df.columns)
        self.assertIn("sma200", df.columns)


class TestADI(unittest.TestCase):
    def test_compute_and_analyze(self):
        adi = ADIIndicator()
        df = _make_ohlcv()
        df = adi.compute(df)
        result = adi.analyze(df)
        self.assertIn(result.signal, list(Signal))


class TestStochasticRSI(unittest.TestCase):
    def test_compute_adds_columns(self):
        stoch = StochasticRSIIndicator()
        df = _make_ohlcv()
        df = stoch.compute(df)
        self.assertIn("stochastic", df.columns)
        self.assertIn("stoch_signal", df.columns)


class TestVolume(unittest.TestCase):
    def test_compute_and_analyze(self):
        vol = VolumeIndicator()
        df = _make_ohlcv()
        df = vol.compute(df)
        result = vol.analyze(df)
        self.assertIn(result.signal, list(Signal))


class TestSupportResistance(unittest.TestCase):
    def test_compute_and_analyze(self):
        sr = SupportResistanceIndicator()
        df = _make_ohlcv()
        df = sr.compute(df)
        result = sr.analyze(df)
        self.assertIn(result.signal, list(Signal))


class TestFibonacci(unittest.TestCase):
    def test_analyze_returns_levels(self):
        fib = FibonacciIndicator()
        df = _make_ohlcv()
        result = fib.analyze(df)
        self.assertIn("retracement_levels", result.metadata)
        levels = result.metadata["retracement_levels"]
        self.assertIn("38.2%", levels)
        self.assertIn("61.8%", levels)


class TestChoppiness(unittest.TestCase):
    def test_compute_and_analyze(self):
        chop = ChoppinessIndicator()
        df = _make_ohlcv()
        df = chop.compute(df)
        result = chop.analyze(df)
        self.assertGreater(result.value, 0)


class TestADX(unittest.TestCase):
    def test_compute_adds_columns(self):
        adx = ADXIndicator()
        df = _make_ohlcv()
        df = adx.compute(df)
        self.assertIn("adx", df.columns)
        self.assertIn("adx_pos", df.columns)
        self.assertIn("adx_neg", df.columns)


if __name__ == "__main__":
    unittest.main()
