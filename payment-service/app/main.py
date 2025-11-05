import pika
import json
import sqlite3
import os
import time
from models import OrderEvent

# db setup
def init_db():
    conn = sqlite3.connect('payments.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            orderId INTEGER NOT NULL,
            success BOOLEAN NOT NULL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def luhn_check(card_number: str) -> bool:
    def digits_of(n):
        return [int(d) for d in str(n)]
    
    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    
    checksum = sum(odd_digits)
    
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    
    return checksum % 10 == 0

def validate_credit_card(credit_card: dict) -> tuple[bool, str]:
    card_number = str(credit_card.get('cardNumber', ''))
    
    # Luhn check
    if not luhn_check(card_number):
        return False, "Invalid card number"
    
    # Month validation (1-12)
    month = credit_card.get('expirationMonth')
    if not (1 <= month <= 12):
        return False, "Invalid expiration month"
    
    # Year validation (4 digits)
    year = credit_card.get('expirationYear')
    if not (1000 <= year <= 9999):
        return False, "Invalid expiration year"
    
    # CVC validation (3 digits)
    cvc = str(credit_card.get('cvc'))
    if len(cvc) != 3 or not cvc.isdigit():
        return False, "Invalid CVC"
    
    return True, "Validation successful"

def store_payment_result(order_id: int, success: bool, reason: str):
    """Store payment result in database"""
    conn = sqlite3.connect('payments.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO payments (orderId, success, reason) VALUES (?, ?, ?)',
        (order_id, success, reason)
    )
    conn.commit()
    conn.close()

def process_order_event(event_data: dict):
    """Process order_created event and validate payment"""
    order_id = event_data.get('id')
    credit_card = event_data.get('creditCard', {})
    
    print(f"💳 Processing payment for order {order_id}")
    
    # Validatar credit card
    is_valid, reason = validate_credit_card(credit_card)
    
    # Store result
    store_payment_result(order_id, is_valid, reason)
    
    # Send appropriate event
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=os.getenv('RABBITMQ_URL', 'rabbitmq'),
            port=5672
        )
    )
    channel = connection.channel()
    
    if is_valid:
        channel.basic_publish(
            exchange='',
            routing_key='payment_success',
            body=json.dumps(event_data)
        )
        print(f"✅ Payment SUCCESS for order {order_id}")
    else:
        channel.basic_publish(
            exchange='',
            routing_key='payment_failed', 
            body=json.dumps(event_data)
        )
        print(f"❌ Payment FAILED for order {order_id}: {reason}")
    
    connection.close()

def start_consuming():
    """Start consuming order_created events"""
    print("🚀 Starting PaymentService...")
    
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=os.getenv('RABBITMQ_URL', 'rabbitmq'),
                    port=5672
                )
            )
            channel = connection.channel()
            
            # Declare queue
            channel.queue_declare(queue='order_created')
            channel.queue_declare(queue='payment_success')
            channel.queue_declare(queue='payment_failed')
            
            print("✅ Connected to RabbitMQ. Waiting for order events...")
            
            def callback(ch, method, properties, body):
                try:
                    event_data = json.loads(body)
                    print(f"📨 Received order_created event for order {event_data.get('id')}")
                    process_order_event(event_data)
                except Exception as e:
                    print(f"❌ Error processing order event: {e}")
            
            channel.basic_consume(
                queue='order_created',
                on_message_callback=callback,
                auto_ack=True
            )
            
            channel.start_consuming()
            
        except pika.exceptions.AMQPConnectionError:
            print("❌ Cannot connect to RabbitMQ. Retrying in 5 seconds...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("🛑 PaymentService stopped by user")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}. Restarting in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    start_consuming()