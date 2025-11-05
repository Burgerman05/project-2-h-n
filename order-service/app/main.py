from fastapi import FastAPI, HTTPException
import requests
import os
import sqlite3
from app.models import OrderCreate, OrderResponse
from app.rabbitmq_client import RabbitMQClient

app = FastAPI(title="Order Service")

# Environment variables
MERCHANT_SERVICE_URL = os.getenv('MERCHANT_SERVICE_URL', 'http://merchant-service:8001')
BUYER_SERVICE_URL = os.getenv('BUYER_SERVICE_URL', 'http://buyer-service:8002') 
INVENTORY_SERVICE_URL = os.getenv('INVENTORY_SERVICE_URL', 'http://inventory-service:8003')

rabbitmq_client = RabbitMQClient()

# Database setup
def init_db():
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            productId INTEGER NOT NULL,
            merchantId INTEGER NOT NULL,
            buyerId INTEGER NOT NULL,
            cardNumber TEXT NOT NULL,
            expirationMonth INTEGER NOT NULL,
            expirationYear INTEGER NOT NULL,
            cvc INTEGER NOT NULL,
            discount REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def check_merchant_exists(merchant_id: int) -> bool:
    try:
        response = requests.get(f"{MERCHANT_SERVICE_URL}/merchants/{merchant_id}")
        return response.status_code == 200
    except:
        return False

def check_buyer_exists(buyer_id: int) -> bool:
    try:
        response = requests.get(f"{BUYER_SERVICE_URL}/buyers/{buyer_id}")
        return response.status_code == 200
    except:
        return False

def check_product_exists(product_id: int) -> bool:
    try:
        response = requests.get(f"{INVENTORY_SERVICE_URL}/products/{product_id}")
        return response.status_code == 200
    except:
        return False

def check_product_belongs_to_merchant(product_id: int, merchant_id: int) -> bool:
    try:
        response = requests.get(f"{INVENTORY_SERVICE_URL}/products/{product_id}")
        if response.status_code == 200:
            product_data = response.json()
            return product_data.get('merchantId') == merchant_id
        return False
    except:
        return False

def check_merchant_allows_discount(merchant_id: int) -> bool:
    try:
        response = requests.get(f"{MERCHANT_SERVICE_URL}/merchants/{merchant_id}")
        if response.status_code == 200:
            merchant_data = response.json()
            return merchant_data.get('allowsDiscount', False)
        return False
    except:
        return False

def reserve_product(product_id: int) -> bool:
    try:
        response = requests.get(f"{INVENTORY_SERVICE_URL}/products/{product_id}")
        if response.status_code == 200:
            product_data = response.json()
            return product_data.get('quantity', 0) > 0
        return False
    except:
        return False

def get_product_price(product_id: int) -> float:
    try:
        response = requests.get(f"{INVENTORY_SERVICE_URL}/products/{product_id}")
        if response.status_code == 200:
            product_data = response.json()
            return product_data.get('price', 0.0)
        return 0.0
    except:
        return 0.0

@app.post("/orders", status_code=201)
def create_order(order: OrderCreate):
    # Validatar hvort seljandi sé til
    if not check_merchant_exists(order.merchantId):
        raise HTTPException(status_code=400, detail="Merchant does not exist")
    
    # Validatar hvort kaupandi sé til
    if not check_buyer_exists(order.buyerId):
        raise HTTPException(status_code=400, detail="Buyer does not exist")
    
    # validatar hvort vara sé til
    if not check_product_exists(order.productId):
        raise HTTPException(status_code=400, detail="Product does not exist")
    
    # kjíkir hvort varan er í eigu merchant
    if not check_product_belongs_to_merchant(order.productId, order.merchantId):
        raise HTTPException(status_code=400, detail="Product does not belong to merchant")
    
    # Kíkjir hvor merchent leyfir Discount
    if order.discount and order.discount > 0:
        if not check_merchant_allows_discount(order.merchantId):
            raise HTTPException(status_code=400, detail="Merchant does not allow discount")
    
    # gaymir vöru
    if not reserve_product(order.productId):
        raise HTTPException(status_code=400, detail="Product is sold out")
    
    # býr til order í db
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO orders (productId, merchantId, buyerId, cardNumber, expirationMonth, expirationYear, cvc, discount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        order.productId,
        order.merchantId,
        order.buyerId,
        order.creditCard.cardNumber,
        order.creditCard.expirationMonth,
        order.creditCard.expirationYear,
        order.creditCard.cvc,
        order.discount or 0.0
    ))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Try to publish RabbitMQ event, but don't fail if it doesn't work
    try:
        order_data = {
            "id": order_id,
            "productId": order.productId,
            "merchantId": order.merchantId,
            "buyerId": order.buyerId,
            "creditCard": order.creditCard.dict(),
            "discount": order.discount or 0.0
        }
        rabbitmq_client.publish_order_created(order_data)
        print(f"✅ Order {order_id} created and event published")
    except Exception as e:
        print(f"⚠️ Order {order_id} created but RabbitMQ event failed: {e}")
        # Don't raise the exception - order was successfully created
    
    return {"id": order_id}

@app.get("/orders/{order_id}")
def get_order(order_id: int):
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
    order_row = cursor.fetchone()
    conn.close()
    
    if not order_row:
        raise HTTPException(status_code=404, detail="Order does not exist")
    
    # order row
    product_price = get_product_price(order_row[1])  # productId
    total_price = product_price * (1 - order_row[8])  # discount
    
    # Mask fyirr Card Number
    card_number = order_row[4]  
    masked_card = "**********" + card_number[-4:]
    
    return OrderResponse(
        productId=order_row[1],
        merchantId=order_row[2],
        buyerId=order_row[3],
        cardNumber=masked_card,
        totalPrice=round(total_price, 2)
    )

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)