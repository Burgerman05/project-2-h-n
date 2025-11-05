from pydantic import BaseModel
from typing import Optional

class ProductCreate(BaseModel):
    merchantId: int
    productName: str
    price: float
    quantity: int

class ProductResponse(BaseModel):
    merchantId: int
    productName: str
    price: float
    quantity: int
    reserved: int

class PaymentEvent(BaseModel):
    id: int
    productId: int
    merchantId: int
    buyerId: int
    creditCard: dict
    discount: float