"""Tests for specialist strategies."""

import unittest

from src.core.enums import MarketRegime, OrderSide, RiskProfile, Signal, TimeFrame
from src.core.models import IndicatorResult, MarketContext, PortfolioState
from src.strategies.bull import BullMarketStrategy
from src.strategies.bear import BearMarketStrategy
from src.strategies.range_strategy import RangeStrategy


def _make_context(signal: Signal, score: int, regime: MarketRegime, confidence: float = 0.8) -> MarketContext:
    return MarketContext(
        regime=regime,
        regime_confidence=confidence,
        trend_score=score,
        signal=signal,
        indicators=[
            IndicatorResult(name="rsi", signal=signal, value=50.0),
            IndicatorResult(name="bollinger", signal=signal, value=100.0,
                           metadata={"upper": 110, "lower": 90, "middle": 100}),
            IndicatorResult(name="support_resistance", signal=signal, value=100.0,
                           metadata={"support": 95, "resistance": 105}),
        ],
    )


class TestBullStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = BullMarketStrategy()

    def test_buy_in_bull_market(self):
        context = _make_context(Signal.BULLISH, 5, MarketRegime.BULL)
        portfolio = PortfolioState(
            fiat_amount=10000.0, crypto_amount=0.0,
            pair="BTCUSDT", current_price=50000.0,
        )
        setup = self.strategy.evaluate(context, portfolio)
        self.assertIsNotNone(setup)
        self.assertEqual(setup.side, OrderSide.BUY)

    def test_no_trade_when_bearish(self):
        context = _make_context(Signal.BEARISH, -3, MarketRegime.BULL)
        portfolio = PortfolioState(
            fiat_amount=10000.0, crypto_amount=0.0,
            pair="BTCUSDT", current_price=50000.0,
        )
        setup = self.strategy.evaluate(context, portfolio)
        self.assertIsNone(setup)

    def test_no_trade_when_already_in_position(self):
        context = _make_context(Signal.BULLISH, 5, MarketRegime.BULL)
        portfolio = PortfolioState(
            fiat_amount=10000.0, crypto_amount=0.1,
            pair="BTCUSDT", current_price=50000.0,
            trade_in_progress=True,
        )
        setup = self.strategy.evaluate(context, portfolio)
        self.assertIsNone(setup)


class TestBearStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = BearMarketStrategy()

    def test_sell_in_bear_market(self):
        context = _make_context(Signal.BEARISH, -5, MarketRegime.BEAR)
        portfolio = PortfolioState(
            fiat_amount=5000.0, crypto_amount=0.1,
            pair="BTCUSDT", current_price=50000.0,
            trade_in_progress=True,
        )
        setup = self.strategy.evaluate(context, portfolio)
        self.assertIsNotNone(setup)
        self.assertEqual(setup.side, OrderSide.SELL)

    def test_no_buy_in_weak_signal(self):
        context = _make_context(Signal.BULLISH, 1, MarketRegime.BEAR)
        portfolio = PortfolioState(
            fiat_amount=10000.0, crypto_amount=0.0,
            pair="BTCUSDT", current_price=50000.0,
        )
        setup = self.strategy.evaluate(context, portfolio)
        self.assertIsNone(setup)


class TestRangeStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = RangeStrategy()

    def test_buy_near_support(self):
        context = MarketContext(
            regime=MarketRegime.RANGE,
            regime_confidence=0.7,
            trend_score=0,
            signal=Signal.NEUTRAL,
            indicators=[
                IndicatorResult(name="bollinger", signal=Signal.OVERSOLD, value=95.0),
                IndicatorResult(name="support_resistance", signal=Signal.BEARISH, value=95.0,
                               metadata={"support": 95.0, "resistance": 105.0}),
            ],
        )
        portfolio = PortfolioState(
            fiat_amount=10000.0, crypto_amount=0.0,
            pair="BTCUSDT", current_price=95.5,  # Near support
        )
        setup = self.strategy.evaluate(context, portfolio)
        self.assertIsNotNone(setup)
        self.assertEqual(setup.side, OrderSide.BUY)

    def test_sell_near_resistance(self):
        context = MarketContext(
            regime=MarketRegime.RANGE,
            regime_confidence=0.7,
            trend_score=0,
            signal=Signal.NEUTRAL,
            indicators=[
                IndicatorResult(name="bollinger", signal=Signal.OVERBOUGHT, value=105.0),
                IndicatorResult(name="support_resistance", signal=Signal.BULLISH, value=104.5,
                               metadata={"support": 95.0, "resistance": 105.0}),
            ],
        )
        portfolio = PortfolioState(
            fiat_amount=5000.0, crypto_amount=100.0,
            pair="BTCUSDT", current_price=104.5,  # Near resistance
            trade_in_progress=True,
        )
        setup = self.strategy.evaluate(context, portfolio)
        self.assertIsNotNone(setup)
        self.assertEqual(setup.side, OrderSide.SELL)


if __name__ == "__main__":
    unittest.main()
