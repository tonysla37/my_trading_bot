"""Abstract exchange adapter for order execution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from src.core.enums import OrderSide, OrderType


@dataclass
class OrderRequest:
    """An order to be placed on an exchange."""
    pair: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None  # None for market orders


@dataclass
class OrderResponse:
    """Response from the exchange after placing an order."""
    success: bool
    order_id: str = ""
    message: str = ""
    filled_price: float = 0.0
    filled_quantity: float = 0.0


class ExchangeAdapter(ABC):
    """Abstract base for exchange integrations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Exchange name."""

    @abstractmethod
    def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place an order on the exchange."""

    @abstractmethod
    def cancel_order(self, order_id: str, pair: str) -> bool:
        """Cancel an existing order."""

    @abstractmethod
    def get_balance(self, coin: str) -> float:
        """Get balance for a coin."""
