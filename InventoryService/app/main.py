from fastapi import FastAPI, HTTPException
import sqlite3
import json
import threading
from app.models import ProductCreate, ProductResponse
from app.rabbitmq_client import RabbitMQClient

app = FastAPI(title="Inventory Service")

# db setup
def init_db():
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchantId INTEGER NOT NULL,
            productName TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            reserved INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def handle_payment_event(event_data, payment_success: bool):
    """Handle payment success/failure events"""
    product_id = event_data.get('productId')
    
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    
    if payment_success:
        cursor.execute('''
            UPDATE products 
            SET quantity = quantity - 1, reserved = reserved - 1
            WHERE id = ? AND reserved > 0
        ''', (product_id,))
    else:
        cursor.execute('''
            UPDATE products 
            SET reserved = reserved - 1
            WHERE id = ? AND reserved > 0
        ''', (product_id,))
    
    conn.commit()
    conn.close()
    print(f"✅ Updated inventory for product {product_id} - payment {'success' if payment_success else 'failed'}")

def start_rabbitmq_consumer():
    rabbitmq = RabbitMQClient()
    
    def callback(ch, method, properties, body):
        try:
            event_data = json.loads(body)
            print(f"📨 InventoryService received {method.routing_key} event")
            
            if method.routing_key == 'payment_success':
                handle_payment_event(event_data, payment_success=True)
            elif method.routing_key == 'payment_failed':
                handle_payment_event(event_data, payment_success=False)
                
        except Exception as e:
            print(f"❌ Error processing payment event: {e}")
    
    rabbitmq.start_consuming(callback)

rabbitmq_thread = threading.Thread(target=start_rabbitmq_consumer, daemon=True)
rabbitmq_thread.start()

@app.post("/products", status_code=201)
def create_product(product: ProductCreate):
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO products (merchantId, productName, price, quantity, reserved)
        VALUES (?, ?, ?, ?, 0)
    ''', (
        product.merchantId,
        product.productName,
        product.price,
        product.quantity
    ))
    
    product_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {"id": product_id}

@app.get("/products/{product_id}")
def get_product(product_id: int):
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT merchantId, productName, price, quantity, reserved FROM products WHERE id = ?', 
        (product_id,)
    )
    product_row = cursor.fetchone()
    conn.close()
    
    if not product_row:
        raise HTTPException(status_code=404, detail="Product does not exist")
    
    return ProductResponse(
        merchantId=product_row[0],
        productName=product_row[1],
        price=product_row[2],
        quantity=product_row[3],
        reserved=product_row[4]
    )

@app.post("/products/{product_id}/reserve")
def reserve_product(product_id: int):
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT quantity, reserved FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    
    if not product:
        conn.close()
        return {"success": False, "message": "Product does not exist"}
    
    available = product[0] - product[1]  
    if available <= 0:
        conn.close()
        return {"success": False, "message": "Product is sold out"}
    
    # geymir eitt item
    cursor.execute(
        'UPDATE products SET reserved = reserved + 1 WHERE id = ? AND quantity > reserved',
        (product_id,)
    )
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return {"success": success, "message": "Product reserved" if success else "Reservation failed"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)