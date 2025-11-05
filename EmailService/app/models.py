from pydantic import BaseModel
from typing import Optional

class OrderEvent(BaseModel):
    id: int
    productId: int
    merchantId: int
    buyerId: int
    creditCard: dict
    discount: float

class CreditCard(BaseModel):
    cardNumber: str
    expirationMonth: int
    expirationYear: int
    cvc: int