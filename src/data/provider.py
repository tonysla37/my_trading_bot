"""DataProvider abstraction - dual mode (live / backtest)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import pandas as pd

from src.core.enums import TimeFrame

logger = logging.getLogger(__name__)

# Mapping from our TimeFrame enum to Binance interval strings
BINANCE_INTERVALS = {
    TimeFrame.MONTHLY: "1M",
    TimeFrame.WEEKLY: "1w",
    TimeFrame.DAILY: "1d",
    TimeFrame.INTRADAY: "1h",
    TimeFrame.SCALPING: "15m",
}


class DataProvider(ABC):
    """Abstract data provider for OHLCV data."""

    @abstractmethod
    def fetch_ohlcv(
        self, symbol: str, timeframe: TimeFrame, start: str = "1 Jan, 2020"
    ) -> pd.DataFrame:
        """Fetch OHLCV data and return a DataFrame with columns:
        open, high, low, close, volume (numeric), indexed by timestamp.
        """

    @abstractmethod
    def get_balance(self, coin: str) -> float:
        """Get balance for a given coin."""


class BinanceProvider(DataProvider):
    """Binance exchange data provider."""

    def __init__(self, api_key: str = "", api_secret: str = ""):
        from binance.client import Client

        if api_key and api_secret:
            self._client = Client(api_key, api_secret)
        else:
            self._client = Client()  # No-auth client for public data
        self._authenticated = bool(api_key and api_secret)

    def fetch_ohlcv(
        self, symbol: str, timeframe: TimeFrame, start: str = "1 Jan, 2020"
    ) -> pd.DataFrame:
        interval = BINANCE_INTERVALS.get(timeframe, "1d")
        try:
            klines = self._client.get_historical_klines(symbol, interval, start)
            df = pd.DataFrame(
                klines,
                columns=[
                    "timestamp", "open", "high", "low", "close", "volume",
                    "close_time", "quote_av", "trades", "tb_base_av",
                    "tb_quote_av", "ignore",
                ],
            )
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            logger.info("Binance OHLCV fetched for %s (%s)", symbol, timeframe.value)
            return df
        except Exception as e:
            logger.error("Error fetching Binance data: %s", e)
            return pd.DataFrame()

    def get_balance(self, coin: str) -> float:
        if not self._authenticated:
            logger.warning("Binance client not authenticated, returning 0")
            return 0.0
        try:
            balances = self._client.get_balances()
            if not balances:
                return 0.0
            df = pd.DataFrame(balances)
            row = df.loc[df["coin"] == coin, "total"]
            return float(row.values[0]) if not row.empty else 0.0
        except Exception as e:
            logger.error("Error getting balance for %s: %s", coin, e)
            return 0.0


class KrakenProvider(DataProvider):
    """Kraken exchange data provider."""

    def __init__(self, api_key: str = "", api_secret: str = ""):
        import krakenex
        from pykrakenapi import KrakenAPI

        api = krakenex.API(key=api_key, secret=api_secret)
        self._client = KrakenAPI(api)

    def fetch_ohlcv(
        self, symbol: str, timeframe: TimeFrame, start: str = "1 Jan, 2020"
    ) -> pd.DataFrame:
        # Kraken uses minutes for interval
        interval_map = {
            TimeFrame.MONTHLY: 43200,
            TimeFrame.WEEKLY: 10080,
            TimeFrame.DAILY: 1440,
            TimeFrame.INTRADAY: 60,
            TimeFrame.SCALPING: 15,
        }
        interval = interval_map.get(timeframe, 1440)
        try:
            df = self._client.get_ohlc_data(pair=symbol, interval=interval)[0]
            for col in ["open", "high", "low", "close", "vwap", "volume", "count"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col])
            df.reset_index(inplace=True)
            if "time" in df.columns:
                df["timestamp"] = pd.to_datetime(df["time"], unit="s")
                df.set_index("timestamp", inplace=True)
                df.drop(columns=["time"], inplace=True)
            logger.info("Kraken OHLCV fetched for %s (%s)", symbol, timeframe.value)
            return df
        except Exception as e:
            logger.error("Error fetching Kraken data: %s", e)
            return pd.DataFrame()

    def get_balance(self, coin: str) -> float:
        try:
            balance = self._client.get_account_balance()
            if coin in balance.index:
                return float(balance.loc[coin, "vol"])
            return 0.0
        except Exception as e:
            logger.error("Error getting Kraken balance for %s: %s", coin, e)
            return 0.0
