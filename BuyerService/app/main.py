from fastapi import FastAPI, HTTPException
import sqlite3
import os
from app.models import BuyerCreate, BuyerResponse

app = FastAPI(title="Buyer Service")

# db startup
def init_db():
    conn = sqlite3.connect('buyers.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS buyers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ssn TEXT NOT NULL,
            email TEXT NOT NULL,
            phoneNumber TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# byrjar db startup
init_db()

@app.post("/buyers", status_code=201)
def create_buyer(buyer: BuyerCreate):
    conn = sqlite3.connect('buyers.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO buyers (name, ssn, email, phoneNumber)
        VALUES (?, ?, ?, ?)
    ''', (
        buyer.name,
        buyer.ssn,
        buyer.email,
        buyer.phoneNumber
    ))
    
    buyer_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {"id": buyer_id}
#vistar i gagnagrun
@app.get("/buyers/{buyer_id}")
def get_buyer(buyer_id: int):
    conn = sqlite3.connect('buyers.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, ssn, email, phoneNumber FROM buyers WHERE id = ?', (buyer_id,))
    buyer_row = cursor.fetchone()
    conn.close()
    
    if not buyer_row:
        raise HTTPException(status_code=404, detail="Buyer not found")
    
    return BuyerResponse(
        name=buyer_row[0],
        ssn=buyer_row[1],
        email=buyer_row[2],
        phoneNumber=buyer_row[3]
    )

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
