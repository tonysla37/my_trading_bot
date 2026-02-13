"""Enumerations for the trading platform."""

from enum import Enum


class MarketRegime(str, Enum):
    """Market regime detected by the MarketRegimeDetector."""
    BULL = "bull"
    BEAR = "bear"
    RANGE = "range"
    UNKNOWN = "unknown"


class RiskProfile(str, Enum):
    """Risk profiles for position sizing."""
    SAFE = "safe"              # 1% per trade
    AGGRESSIVE = "aggressive"  # 3% per trade
    SAFE_LEVERAGE = "safe_leverage"        # x3 leverage
    AGGRESSIVE_LEVERAGE = "aggressive_leverage"  # x10 leverage


class TimeFrame(str, Enum):
    """Trading timeframes."""
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    DAILY = "daily"
    INTRADAY = "intraday"    # 1h
    SCALPING = "scalping"    # 15m


class Signal(str, Enum):
    """Trading signal types."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    OVERBOUGHT = "overbought"
    OVERSOLD = "oversold"
    UNDEFINED = "undefined"


class OrderSide(str, Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class Exchange(str, Enum):
    """Supported exchanges."""
    BINANCE = "binance"
    KRAKEN = "kraken"
