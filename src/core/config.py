"""Configuration management using Pydantic-style dataclasses."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ProtectionConfig:
    """Stop-loss and take-profit configuration."""
    sl_level: float = 0.02
    sl_amount: float = 1.0
    tp1_level: float = 0.10
    tp1_amount: float = 1.0


@dataclass
class RiskProfileConfig:
    """Risk parameters per profile."""
    name: str = "safe"
    risk_per_trade: float = 0.01  # fraction of capital
    max_leverage: float = 1.0
    max_position_pct: float = 0.10  # max 10% of portfolio


@dataclass
class TradingConfig:
    """Trading-specific configuration."""
    pair_symbol: str = "BTCUSDT"
    fiat_symbol: str = "USD"
    crypto_symbol: str = "BTC"
    capital: float = 1000.0
    target: float = 200000.0
    risk_level: str = "Max"
    my_truncate: int = 5
    dca: float = 100.0
    temps: int = 5
    bench_mode: bool = True
    backtest: bool = True
    buy_ready: bool = True
    sell_ready: bool = True
    protection: ProtectionConfig = field(default_factory=ProtectionConfig)


@dataclass
class ExchangeConfig:
    """Exchange API configuration (loaded from env)."""
    binance_api_key: str = ""
    binance_api_secret: str = ""
    kraken_api_key: str = ""
    kraken_api_secret: str = ""

    @classmethod
    def from_env(cls) -> ExchangeConfig:
        return cls(
            binance_api_key=os.getenv("BINANCE_API_KEY", ""),
            binance_api_secret=os.getenv("BINANCE_API_SECRET", ""),
            kraken_api_key=os.getenv("KRAKEN_API_KEY", ""),
            kraken_api_secret=os.getenv("KRAKEN_API_SECRET", ""),
        )


@dataclass
class NotificationConfig:
    """Notification configuration."""
    discord_webhook_url: str = ""

    @classmethod
    def from_env(cls) -> NotificationConfig:
        return cls(
            discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL", ""),
        )


@dataclass
class Settings:
    """Root settings object."""
    trading: TradingConfig = field(default_factory=TradingConfig)
    exchange: ExchangeConfig = field(default_factory=ExchangeConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)

    # Pre-defined risk profiles
    risk_profiles: dict = field(default_factory=lambda: {
        "safe": RiskProfileConfig(name="safe", risk_per_trade=0.01, max_leverage=1.0),
        "aggressive": RiskProfileConfig(name="aggressive", risk_per_trade=0.03, max_leverage=1.0),
        "safe_leverage": RiskProfileConfig(name="safe_leverage", risk_per_trade=0.01, max_leverage=3.0),
        "aggressive_leverage": RiskProfileConfig(name="aggressive_leverage", risk_per_trade=0.03, max_leverage=10.0),
    })


def load_settings(config_path: str | Path | None = None) -> Settings:
    """Load settings from config.yaml + environment variables."""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
    else:
        config_path = Path(config_path)

    settings = Settings()

    if config_path.exists():
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}

        trading_raw = raw.get("trading", {})
        protection_raw = trading_raw.pop("protection", {})

        # Map old config keys to new structure
        settings.trading = TradingConfig(
            pair_symbol=trading_raw.get("pair_symbol", "BTCUSDT"),
            fiat_symbol=trading_raw.get("fiat_symbol", "USD"),
            crypto_symbol=trading_raw.get("crypto_symbol", "BTC"),
            capital=trading_raw.get("capital", 1000.0),
            target=trading_raw.get("cible", 200000.0),
            risk_level=trading_raw.get("risk_level", "Max"),
            my_truncate=trading_raw.get("my_truncate", 5),
            dca=trading_raw.get("dca", 100.0),
            temps=trading_raw.get("temps", 5),
            bench_mode=trading_raw.get("bench_mode", True),
            backtest=bool(trading_raw.get("backtest", True)),
            buy_ready=trading_raw.get("buy_ready", True),
            sell_ready=trading_raw.get("sell_ready", True),
            protection=ProtectionConfig(
                sl_level=protection_raw.get("sl_level", 0.02),
                sl_amount=protection_raw.get("sl_amount", 1.0),
                tp1_level=protection_raw.get("tp1_level", 0.10),
                tp1_amount=protection_raw.get("tp1_amount", 1.0),
            ),
        )

    # Load exchange config from environment
    settings.exchange = ExchangeConfig.from_env()
    settings.notifications = NotificationConfig.from_env()

    return settings
