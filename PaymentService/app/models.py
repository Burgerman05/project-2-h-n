from pydantic import BaseModel

class CreditCard(BaseModel):
    cardNumber: str
    expirationMonth: int
    expirationYear: int
    cvc: int

class OrderEvent(BaseModel):
    id: int
    productId: int
    merchantId: int
    buyerId: int
    creditCard: CreditCard
    discount: float