from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AssetClass(str, Enum):
    ACAO = "ACAO"
    FII = "FII"
    ETF = "ETF"
    BDR = "BDR"
    CRYPTO = "CRYPTO"
    TESOURO = "TESOURO"
    RENDA_FIXA_PRIVADA = "RENDA_FIXA_PRIVADA"

    @classmethod
    def from_str(cls, value: str) -> AssetClass:
        try:
            return cls(value.upper())
        except ValueError:
            return cls.ACAO


class ZoneStatus(str, Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"


class OrderAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Asset:
    ticker: str
    asset_class: AssetClass
    quantity: float
    avg_price: float
    current_price: float = 0.0
    target_weight: float = 0.0  # percentage [0, 100]
    current_weight: float = 0.0  # computed at runtime

    @property
    def current_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_price

    @property
    def pnl(self) -> float:
        return self.current_value - self.cost_basis


@dataclass
class Band:
    target_weight: float
    relative_pct: float
    absolute_pp: float
    lower_bound: float = field(init=False)
    upper_bound: float = field(init=False)

    def __post_init__(self) -> None:
        self.lower_bound = max(self.target_weight - self.target_weight * self.relative_pct - self.absolute_pp, 0.0)
        self.upper_bound = self.target_weight + self.target_weight * self.relative_pct + self.absolute_pp


@dataclass
class Order:
    ticker: str
    action: OrderAction
    quantity: float
    price: float

    @property
    def amount(self) -> float:
        return self.quantity * self.price
