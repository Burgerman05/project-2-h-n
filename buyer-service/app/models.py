from pydantic import BaseModel

class BuyerCreate(BaseModel):
    name: str
    email: str
    ssn: str
    phoneNumber: str

class BuyerResponse(BaseModel):
    name: str
    ssn: str
    email: str
    phoneNumber: str