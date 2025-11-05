from fastapi import FastAPI, HTTPException
import sqlite3
import os
from app.models import MerchantCreate, MerchantResponse

app = FastAPI(title="Merchant Service")

# Database setup
def init_db():
    conn = sqlite3.connect('merchants.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS merchants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ssn TEXT NOT NULL,
            email TEXT NOT NULL,
            phoneNumber TEXT NOT NULL,
            allowsDiscount BOOLEAN NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# db startup
init_db()

@app.post("/merchants", status_code=201)
def create_merchant(merchant: MerchantCreate):
    conn = sqlite3.connect('merchants.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO merchants (name, ssn, email, phoneNumber, allowsDiscount)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        merchant.name,
        merchant.ssn,
        merchant.email,
        merchant.phoneNumber,
        merchant.allowsDiscount
    ))
    
    merchant_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {"id": merchant_id}

@app.get("/merchants/{merchant_id}")
def get_merchant(merchant_id: int):
    conn = sqlite3.connect('merchants.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, ssn, email, phoneNumber, allowsDiscount FROM merchants WHERE id = ?', (merchant_id,))
    merchant_row = cursor.fetchone()
    conn.close()
    
    if not merchant_row:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    return MerchantResponse(
        name=merchant_row[0],
        ssn=merchant_row[1],
        email=merchant_row[2],
        phoneNumber=merchant_row[3],
        allowsDiscount=bool(merchant_row[4])
    )

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)