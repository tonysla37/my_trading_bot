"""Data models for the trading platform."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import pandas as pd

from .enums import MarketRegime, OrderSide, RiskProfile, Signal, TimeFrame


@dataclass
class OHLCV:
    """Single OHLCV candle."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class IndicatorResult:
    """Result from an indicator analysis."""
    name: str
    signal: Signal
    value: float
    metadata: dict = field(default_factory=dict)

    @property
    def is_bullish(self) -> bool:
        return self.signal in (Signal.BULLISH, Signal.OVERSOLD)

    @property
    def is_bearish(self) -> bool:
        return self.signal in (Signal.BEARISH, Signal.OVERBOUGHT)


@dataclass
class MarketContext:
    """Aggregated market context from all indicators."""
    regime: MarketRegime
    regime_confidence: float  # 0.0 to 1.0
    trend_score: int  # sum of indicator signals (-N to +N)
    signal: Signal  # overall market signal
    indicators: list[IndicatorResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TradeSetup:
    """A potential trade setup."""
    side: OrderSide
    pair: str
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    risk_profile: RiskProfile
    timeframe: TimeFrame
    regime: MarketRegime
    confidence: float = 0.0


@dataclass
class TradeResult:
    """Result of a trade execution."""
    success: bool
    side: OrderSide
    pair: str
    price: float
    quantity: float
    fiat_after: float
    crypto_after: float
    total_portfolio_value: float
    trade_in_progress: bool
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    order_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class PortfolioState:
    """Current state of the portfolio."""
    fiat_amount: float
    crypto_amount: float
    pair: str
    current_price: float
    trade_in_progress: bool = False
    consecutive_losses: int = 0
    risk_profile: RiskProfile = RiskProfile.SAFE

    @property
    def total_value(self) -> float:
        return self.fiat_amount + (self.crypto_amount * self.current_price)
