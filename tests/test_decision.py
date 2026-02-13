"""Tests for the Decision Engine."""

import unittest

from src.core.config import ProtectionConfig, RiskProfileConfig
from src.core.enums import MarketRegime, OrderSide, Signal, TimeFrame
from src.core.models import IndicatorResult, MarketContext
from src.decision.engine import DecisionEngine


class TestDecisionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = DecisionEngine(
            risk_profile=RiskProfileConfig(name="safe", risk_per_trade=0.02),
            protection=ProtectionConfig(sl_level=0.02, tp1_level=0.10),
        )

    def _make_results(self, bullish_count: int, bearish_count: int) -> list[IndicatorResult]:
        results = []
        indicator_names = ["adi", "bollinger", "ema", "macd", "rsi", "sma", "stoch_rsi", "volume", "fear_and_greed"]
        for i, name in enumerate(indicator_names):
            if i < bullish_count:
                results.append(IndicatorResult(name=name, signal=Signal.BULLISH, value=1.0))
            elif i < bullish_count + bearish_count:
                results.append(IndicatorResult(name=name, signal=Signal.BEARISH, value=-1.0))
            else:
                results.append(IndicatorResult(name=name, signal=Signal.NEUTRAL, value=0.0))
        return results

    def test_bullish_market_context(self):
        results = self._make_results(6, 2)
        context = self.engine.compute_market_context(results)
        self.assertEqual(context.signal, Signal.BULLISH)
        self.assertGreater(context.trend_score, 0)

    def test_bearish_market_context(self):
        results = self._make_results(2, 6)
        context = self.engine.compute_market_context(results)
        self.assertEqual(context.signal, Signal.BEARISH)
        self.assertLess(context.trend_score, 0)

    def test_buy_signal_generated(self):
        results = self._make_results(7, 1)
        context = self.engine.compute_market_context(results, MarketRegime.BULL, 0.8)
        setup = self.engine.evaluate(
            context=context,
            pair="BTCUSDT",
            current_price=50000.0,
            fiat_amount=10000.0,
            crypto_amount=0.0,
            trade_in_progress=False,
        )
        self.assertIsNotNone(setup)
        self.assertEqual(setup.side, OrderSide.BUY)
        self.assertGreater(setup.quantity, 0)
        self.assertGreater(setup.risk_reward_ratio, 0)

    def test_sell_signal_generated(self):
        results = self._make_results(1, 7)
        context = self.engine.compute_market_context(results, MarketRegime.BEAR, 0.8)
        setup = self.engine.evaluate(
            context=context,
            pair="BTCUSDT",
            current_price=50000.0,
            fiat_amount=10000.0,
            crypto_amount=0.1,
            trade_in_progress=True,
        )
        self.assertIsNotNone(setup)
        self.assertEqual(setup.side, OrderSide.SELL)

    def test_no_signal_in_neutral_market(self):
        results = self._make_results(4, 4)
        context = self.engine.compute_market_context(results)
        setup = self.engine.evaluate(
            context=context,
            pair="BTCUSDT",
            current_price=50000.0,
            fiat_amount=10000.0,
            crypto_amount=0.0,
            trade_in_progress=False,
        )
        self.assertIsNone(setup)

    def test_no_buy_when_insufficient_fiat(self):
        results = self._make_results(7, 1)
        context = self.engine.compute_market_context(results)
        setup = self.engine.evaluate(
            context=context,
            pair="BTCUSDT",
            current_price=50000.0,
            fiat_amount=2.0,  # Less than $5
            crypto_amount=0.0,
            trade_in_progress=False,
        )
        self.assertIsNone(setup)


if __name__ == "__main__":
    unittest.main()
