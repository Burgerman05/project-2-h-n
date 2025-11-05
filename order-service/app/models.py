from pydantic import BaseModel
from typing import Optional

class CreditCard(BaseModel):
    cardNumber: str
    expirationMonth: int
    expirationYear: int
    cvc: int

class OrderCreate(BaseModel):
    productId: int
    merchantId: int
    buyerId: int
    creditCard: CreditCard
    discount: Optional[float] = 0.0

class OrderResponse(BaseModel):
    productId: int
    merchantId: int
    buyerId: int
    cardNumber: str
    totalPrice: float