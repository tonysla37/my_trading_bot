"""Tests for Risk Management module."""

import unittest

from src.core.config import ProtectionConfig, RiskProfileConfig
from src.core.enums import OrderSide, RiskProfile
from src.core.models import PortfolioState, TradeSetup
from src.core.enums import MarketRegime, TimeFrame
from src.risk.manager import RiskManager


class TestRiskManager(unittest.TestCase):
    def setUp(self):
        self.risk_profile = RiskProfileConfig(
            name="safe", risk_per_trade=0.02, max_leverage=1.0, max_position_pct=0.10,
        )
        self.protection = ProtectionConfig(sl_level=0.02, tp1_level=0.10)
        self.manager = RiskManager(self.risk_profile, self.protection)

    def test_position_size(self):
        portfolio = PortfolioState(
            fiat_amount=10000.0,
            crypto_amount=0.0,
            pair="BTCUSDT",
            current_price=50000.0,
        )
        size = self.manager.compute_position_size(portfolio, 50000.0)
        # 10000 * 0.02 / 50000 = 0.004
        self.assertAlmostEqual(size, 0.004, places=3)

    def test_stop_loss_buy(self):
        sl = self.manager.compute_stop_loss(50000.0, OrderSide.BUY)
        self.assertAlmostEqual(sl, 49000.0)  # 50000 * 0.98

    def test_take_profit_buy(self):
        tp = self.manager.compute_take_profit(50000.0, OrderSide.BUY)
        self.assertAlmostEqual(tp, 55000.0)  # 50000 * 1.10

    def test_risk_reduction_after_losses(self):
        portfolio = PortfolioState(
            fiat_amount=10000.0,
            crypto_amount=0.0,
            pair="BTCUSDT",
            current_price=50000.0,
            consecutive_losses=3,
        )
        size = self.manager.compute_position_size(portfolio, 50000.0)
        # Risk reduced by 50%: 10000 * 0.01 / 50000 = 0.002
        self.assertAlmostEqual(size, 0.002, places=3)

    def test_leverage_safety_sl(self):
        """SL must be above liquidation price for leveraged trades."""
        leveraged_profile = RiskProfileConfig(
            name="safe_leverage", risk_per_trade=0.01, max_leverage=10.0,
        )
        manager = RiskManager(leveraged_profile, self.protection)
        sl = manager.compute_stop_loss(50000.0, OrderSide.BUY)
        # Liquidation at 50000 * (1 - 1/10) = 45000
        # SL must be above 45000 * 1.05 = 47250
        self.assertGreater(sl, 47250.0)

    def test_validate_trade_insufficient_fiat(self):
        portfolio = PortfolioState(
            fiat_amount=3.0,
            crypto_amount=0.0,
            pair="BTCUSDT",
            current_price=50000.0,
        )
        setup = TradeSetup(
            side=OrderSide.BUY,
            pair="BTCUSDT",
            entry_price=50000.0,
            quantity=0.001,
            stop_loss=49000.0,
            take_profit=55000.0,
            risk_reward_ratio=5.0,
            risk_profile=RiskProfile.SAFE,
            timeframe=TimeFrame.DAILY,
            regime=MarketRegime.BULL,
        )
        self.assertFalse(self.manager.validate_trade(setup, portfolio))


if __name__ == "__main__":
    unittest.main()
