"""Kraken exchange adapter."""

from __future__ import annotations

import logging

from src.core.enums import OrderSide, OrderType

from .base import ExchangeAdapter, OrderRequest, OrderResponse

logger = logging.getLogger(__name__)


class KrakenAdapter(ExchangeAdapter):
    """Kraken order execution adapter."""

    name = "kraken"

    def __init__(self, api_key: str = "", api_secret: str = ""):
        self._api_key = api_key
        self._api_secret = api_secret
        self._api = None

    def _get_api(self):
        if self._api is None:
            import krakenex
            self._api = krakenex.API(key=self._api_key, secret=self._api_secret)
        return self._api

    def place_order(self, order: OrderRequest) -> OrderResponse:
        try:
            api = self._get_api()
            params = {
                "pair": order.pair,
                "type": order.side.value,
                "ordertype": "limit" if order.price else "market",
                "volume": str(order.quantity),
            }
            if order.price:
                params["price"] = str(order.price)

            result = api.query_private("AddOrder", params)

            if result.get("error"):
                return OrderResponse(
                    success=False,
                    message=str(result["error"]),
                )

            txid = result.get("result", {}).get("txid", [""])[0]
            return OrderResponse(success=True, order_id=txid)
        except Exception as e:
            logger.error("Kraken order error: %s", e)
            return OrderResponse(success=False, message=str(e))

    def cancel_order(self, order_id: str, pair: str) -> bool:
        try:
            api = self._get_api()
            result = api.query_private("CancelOrder", {"txid": order_id})
            return not bool(result.get("error"))
        except Exception as e:
            logger.error("Kraken cancel error: %s", e)
            return False

    def get_balance(self, coin: str) -> float:
        try:
            from pykrakenapi import KrakenAPI
            kraken = KrakenAPI(self._get_api())
            balance = kraken.get_account_balance()
            if coin in balance.index:
                return float(balance.loc[coin, "vol"])
            return 0.0
        except Exception as e:
            logger.error("Kraken balance error: %s", e)
            return 0.0
