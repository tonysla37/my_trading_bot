"""Backtest Engine - simulates trading strategies on historical data."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pandas as pd

from src.core.config import Settings, load_settings
from src.core.enums import MarketRegime, OrderSide, RiskProfile, TimeFrame
from src.core.models import MarketContext, PortfolioState, TradeResult
from src.decision.engine import DecisionEngine
from src.indicators.engine import IndicatorEngine
from src.market.regime_detector import MarketRegimeDetector
from src.portfolio.manager import PortfolioManager

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Summary of a backtest run."""
    initial_capital: float
    final_capital: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    trades: list[dict] = field(default_factory=list)

    @property
    def pnl(self) -> float:
        return self.final_capital - self.initial_capital

    @property
    def pnl_pct(self) -> float:
        if self.initial_capital == 0:
            return 0.0
        return (self.pnl / self.initial_capital) * 100

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades

    def summary(self) -> str:
        return (
            f"=== Backtest Results ===\n"
            f"Initial Capital: ${self.initial_capital:,.2f}\n"
            f"Final Capital:   ${self.final_capital:,.2f}\n"
            f"PnL:             ${self.pnl:,.2f} ({self.pnl_pct:+.2f}%)\n"
            f"Total Trades:    {self.total_trades}\n"
            f"Win Rate:        {self.win_rate:.1%}\n"
            f"Winning:         {self.winning_trades}\n"
            f"Losing:          {self.losing_trades}\n"
        )


class BacktestEngine:
    """Runs a full backtest of the v2 trading system.

    Iterates through historical data bar-by-bar, computing indicators,
    detecting regime, and running the decision engine + specialist strategies.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or load_settings()
        # Use fast indicators (no external API calls) for backtesting
        self.indicator_engine = IndicatorEngine.fast()
        self.regime_detector = MarketRegimeDetector()
        self.portfolio_manager = PortfolioManager(self.settings)

    def run(
        self,
        data: pd.DataFrame,
        initial_fiat: float = 10000.0,
        initial_crypto: float = 0.0,
        pair: str = "BTCUSDT",
        timeframe: TimeFrame = TimeFrame.DAILY,
        min_bars: int = 200,
    ) -> BacktestResult:
        """Run the backtest on the given OHLCV DataFrame."""
        total_trades = 0
        winning_trades = 0
        losing_trades = 0
        trades = []

        # Compute all indicators once on full dataset
        data = self.indicator_engine.compute_all(data)

        portfolio = PortfolioState(
            fiat_amount=initial_fiat,
            crypto_amount=initial_crypto,
            pair=pair,
            current_price=data["close"].iloc[-1] if not data.empty else 0,
        )

        entry_price = 0.0

        for i in range(min_bars, len(data)):
            window = data.iloc[:i + 1]
            current_price = window["close"].iloc[-1]
            portfolio.current_price = current_price

            # Analyze indicators on the current window
            results = self.indicator_engine.analyze_all(window)

            # Detect market regime
            regime, confidence = self.regime_detector.detect(window)

            # Build market context
            decision_engine = DecisionEngine(
                risk_profile=list(self.settings.risk_profiles.values())[0],
                protection=self.settings.trading.protection,
            )
            context = decision_engine.compute_market_context(results, regime, confidence)

            # Get trade setup from portfolio manager
            setup = self.portfolio_manager.evaluate(context, portfolio)

            if setup is not None:
                # Simulate execution
                if setup.side == OrderSide.BUY:
                    cost = setup.quantity * current_price
                    if cost <= portfolio.fiat_amount:
                        portfolio.fiat_amount -= cost
                        portfolio.crypto_amount += setup.quantity
                        portfolio.trade_in_progress = True
                        entry_price = current_price

                        trades.append({
                            "bar": i,
                            "side": "buy",
                            "price": current_price,
                            "quantity": setup.quantity,
                            "regime": regime.value,
                        })

                elif setup.side == OrderSide.SELL:
                    revenue = setup.quantity * current_price
                    portfolio.fiat_amount += revenue
                    portfolio.crypto_amount -= setup.quantity
                    portfolio.trade_in_progress = False

                    total_trades += 1
                    if current_price > entry_price:
                        winning_trades += 1
                    else:
                        losing_trades += 1

                    trades.append({
                        "bar": i,
                        "side": "sell",
                        "price": current_price,
                        "quantity": setup.quantity,
                        "regime": regime.value,
                        "pnl": (current_price - entry_price) * setup.quantity,
                    })

        # Final portfolio value
        final_value = portfolio.fiat_amount + (portfolio.crypto_amount * data["close"].iloc[-1])

        return BacktestResult(
            initial_capital=initial_fiat,
            final_capital=final_value,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            trades=trades,
        )
