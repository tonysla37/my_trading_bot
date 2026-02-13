"""Fear & Greed Index indicator (external data)."""

from __future__ import annotations

import logging

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.core.enums import Signal

from .base import Indicator

logger = logging.getLogger(__name__)


def fetch_fear_and_greed_index() -> int | None:
    """Fetch the Bitcoin Fear & Greed Index from alternative.me."""
    try:
        url = "https://alternative.me/crypto/fear-and-greed-index/"
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")
        value = soup.find("div", class_="fng-circle").text.strip()
        return int(value)
    except Exception as e:
        logger.warning("Could not fetch Fear & Greed index: %s", e)
        return None


class FearAndGreedIndicator(Indicator):
    """Bitcoin Fear & Greed Index analysis."""

    name = "fear_and_greed"

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        # External indicator - no DataFrame enrichment needed
        return df

    def analyze(self, df: pd.DataFrame) -> "IndicatorResult":
        index_value = fetch_fear_and_greed_index()
        if index_value is None:
            return self._make_result(Signal.UNDEFINED, 0.0)

        if index_value < 20:
            signal = Signal.BULLISH  # Extreme fear = buying opportunity
            sentiment = "extreme_fear"
        elif index_value < 40:
            signal = Signal.BULLISH
            sentiment = "fear"
        elif index_value < 60:
            signal = Signal.NEUTRAL
            sentiment = "neutral"
        elif index_value < 80:
            signal = Signal.BEARISH
            sentiment = "greed"
        else:
            signal = Signal.BEARISH  # Extreme greed = take profits
            sentiment = "extreme_greed"

        return self._make_result(
            signal, float(index_value), sentiment=sentiment,
        )
