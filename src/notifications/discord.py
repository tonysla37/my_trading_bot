"""Discord notification service - uses env var for webhook URL."""

from __future__ import annotations

import logging
import os

import aiohttp
import asyncio
import ssl

from src.core.models import TradeSetup, TradeResult

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Sends rich trade notifications to Discord via webhook."""

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL", "")

    def notify_trade(self, setup: TradeSetup, result: TradeResult) -> None:
        """Send a trade notification to Discord."""
        if not self.webhook_url:
            logger.warning("Discord webhook URL not configured")
            return

        side_emoji = "BUY" if setup.side.value == "buy" else "SELL"
        lines = [
            f"**{side_emoji} - {setup.pair}**",
            f"Regime: {setup.regime.value} (confidence: {setup.confidence:.0%})",
            f"Price: {setup.entry_price:.2f}",
            f"Quantity: {setup.quantity:.6f}",
        ]
        if setup.stop_loss:
            lines.append(f"SL: {setup.stop_loss:.2f}")
        if setup.take_profit:
            lines.append(f"TP: {setup.take_profit:.2f}")
        if setup.risk_reward_ratio:
            lines.append(f"R:R = {setup.risk_reward_ratio:.2f}")
        lines.append(f"Portfolio: {result.total_portfolio_value:.2f} USD")

        message = "\n".join(lines)
        self._send(message)

    def notify_regime_change(self, old_regime: str, new_regime: str, confidence: float) -> None:
        """Notify when market regime changes."""
        if not self.webhook_url:
            return
        message = (
            f"**Regime Change**\n"
            f"{old_regime} -> {new_regime} (confidence: {confidence:.0%})"
        )
        self._send(message)

    def _send(self, content: str) -> None:
        """Send a message to the Discord webhook."""
        try:
            asyncio.run(self._async_send(content))
        except Exception as e:
            logger.error("Discord notification error: %s", e)

    async def _async_send(self, content: str) -> None:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.webhook_url, json={"content": content}, ssl=ssl_context,
            ) as response:
                if response.status != 204:
                    logger.error(
                        "Discord send failed: %d - %s",
                        response.status, await response.text(),
                    )
