from __future__ import annotations
from typing import List

from pydantic import BaseModel


class AccountBalance(BaseModel):
    account_type: str
    currency: str
    balance: float


class CustomerBalanceResponse(BaseModel):
    customer_id: str
    balances: List[AccountBalance]
