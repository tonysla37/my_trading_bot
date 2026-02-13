"""Binance exchange adapter."""

from __future__ import annotations

import logging

from src.core.enums import OrderSide, OrderType

from .base import ExchangeAdapter, OrderRequest, OrderResponse

logger = logging.getLogger(__name__)


class BinanceAdapter(ExchangeAdapter):
    """Binance order execution adapter."""

    name = "binance"

    def __init__(self, api_key: str = "", api_secret: str = ""):
        self._api_key = api_key
        self._api_secret = api_secret
        self._client = None

    def _get_client(self):
        if self._client is None:
            from binance.client import Client
            self._client = Client(self._api_key, self._api_secret)
        return self._client

    def place_order(self, order: OrderRequest) -> OrderResponse:
        try:
            client = self._get_client()
            if order.order_type == OrderType.MARKET:
                if order.side == OrderSide.BUY:
                    result = client.order_market_buy(
                        symbol=order.pair, quantity=order.quantity,
                    )
                else:
                    result = client.order_market_sell(
                        symbol=order.pair, quantity=order.quantity,
                    )
            else:
                side_str = "BUY" if order.side == OrderSide.BUY else "SELL"
                result = client.create_order(
                    symbol=order.pair,
                    side=side_str,
                    type="LIMIT",
                    timeInForce="GTC",
                    quantity=order.quantity,
                    price=str(order.price),
                )

            return OrderResponse(
                success=True,
                order_id=str(result.get("orderId", "")),
                filled_price=float(result.get("price", 0)),
                filled_quantity=float(result.get("executedQty", 0)),
            )
        except Exception as e:
            logger.error("Binance order error: %s", e)
            return OrderResponse(success=False, message=str(e))

    def cancel_order(self, order_id: str, pair: str) -> bool:
        try:
            client = self._get_client()
            client.cancel_order(symbol=pair, orderId=order_id)
            return True
        except Exception as e:
            logger.error("Binance cancel error: %s", e)
            return False

    def get_balance(self, coin: str) -> float:
        try:
            client = self._get_client()
            info = client.get_asset_balance(asset=coin)
            return float(info["free"]) if info else 0.0
        except Exception as e:
            logger.error("Binance balance error: %s", e)
            return 0.0
