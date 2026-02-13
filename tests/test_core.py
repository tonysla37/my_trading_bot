"""Tests for core module (config, enums, models)."""

import os
import tempfile
import unittest

import yaml

from src.core.config import (
    Settings, TradingConfig, ProtectionConfig, RiskProfileConfig,
    load_settings,
)
from src.core.enums import MarketRegime, RiskProfile, Signal, TimeFrame, OrderSide
from src.core.models import (
    IndicatorResult, MarketContext, PortfolioState, TradeSetup, TradeResult,
)


class TestEnums(unittest.TestCase):
    def test_market_regime_values(self):
        self.assertEqual(MarketRegime.BULL.value, "bull")
        self.assertEqual(MarketRegime.BEAR.value, "bear")
        self.assertEqual(MarketRegime.RANGE.value, "range")

    def test_risk_profiles(self):
        self.assertEqual(RiskProfile.SAFE.value, "safe")
        self.assertEqual(RiskProfile.AGGRESSIVE.value, "aggressive")

    def test_timeframes(self):
        self.assertEqual(len(TimeFrame), 5)


class TestConfig(unittest.TestCase):
    def test_default_settings(self):
        settings = Settings()
        self.assertEqual(settings.trading.pair_symbol, "BTCUSDT")
        self.assertEqual(settings.trading.capital, 1000.0)
        self.assertIn("safe", settings.risk_profiles)
        self.assertIn("aggressive", settings.risk_profiles)

    def test_load_from_yaml(self):
        config = {
            "trading": {
                "pair_symbol": "ETHUSDT",
                "capital": 5000,
                "cible": 100000,
                "risk_level": "Mid",
                "fiat_symbol": "USD",
                "crypto_symbol": "ETH",
                "my_truncate": 5,
                "dca": 200,
                "temps": 3,
                "bench_mode": True,
                "backtest": False,
                "buy_ready": True,
                "sell_ready": True,
                "protection": {
                    "sl_level": 0.03,
                    "sl_amount": 1,
                    "tp1_level": 0.15,
                    "tp1_amount": 1,
                },
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            tmp_path = f.name

        try:
            settings = load_settings(tmp_path)
            self.assertEqual(settings.trading.pair_symbol, "ETHUSDT")
            self.assertEqual(settings.trading.capital, 5000)
            self.assertEqual(settings.trading.protection.sl_level, 0.03)
            self.assertFalse(settings.trading.backtest)
        finally:
            os.unlink(tmp_path)

    def test_risk_profile_config(self):
        profile = RiskProfileConfig(
            name="safe", risk_per_trade=0.01, max_leverage=1.0,
        )
        self.assertEqual(profile.risk_per_trade, 0.01)
        self.assertEqual(profile.max_leverage, 1.0)


class TestModels(unittest.TestCase):
    def test_indicator_result_bullish(self):
        result = IndicatorResult(name="rsi", signal=Signal.BULLISH, value=55.0)
        self.assertTrue(result.is_bullish)
        self.assertFalse(result.is_bearish)

    def test_indicator_result_bearish(self):
        result = IndicatorResult(name="macd", signal=Signal.OVERBOUGHT, value=80.0)
        self.assertFalse(result.is_bullish)
        self.assertTrue(result.is_bearish)

    def test_portfolio_state_total_value(self):
        portfolio = PortfolioState(
            fiat_amount=5000.0,
            crypto_amount=0.1,
            pair="BTCUSDT",
            current_price=50000.0,
        )
        self.assertEqual(portfolio.total_value, 10000.0)

    def test_trade_result(self):
        result = TradeResult(
            success=True,
            side=OrderSide.BUY,
            pair="BTCUSDT",
            price=50000.0,
            quantity=0.01,
            fiat_after=9500.0,
            crypto_after=0.01,
            total_portfolio_value=10000.0,
            trade_in_progress=True,
        )
        self.assertTrue(result.success)
        self.assertEqual(result.price, 50000.0)


if __name__ == "__main__":
    unittest.main()
