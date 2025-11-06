import pika
import json
import os
import requests
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# For demo purposes - in production use SendGrid
# SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
# SENDGRID_SENDER_EMAIL = os.getenv('SENDGRID_SENDER_EMAIL')

def send_email(to_email, subject, body):
    """
    Simplified email function - prints to console for demo
    In production, replace with SendGrid code
    """
    print("=" * 50)
    print(f"📧 EMAIL SENT:")
    print(f"To: {to_email}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Uncomment for actual SendGrid integration:
    # from sendgrid import SendGridAPIClient
    # from sendgrid.helpers.mail import Mail
    # message = Mail(
    #     from_email=SENDGRID_SENDER_EMAIL,
    #     to_emails=to_email,
    #     subject=subject,
    #     html_content=body)
    # try:
    #     sg = SendGridAPIClient(SENDGRID_API_KEY)
    #     response = sg.send(message)
    #     print(f"SendGrid Response: {response.status_code}")
    # except Exception as e:
    #     print(f"SendGrid Error: {e}")

def get_buyer_email(buyer_id):
    try:
        response = requests.get(f"http://buyer-service:8002/buyers/{buyer_id}")
        if response.status_code == 200:
            return response.json().get('email')
    except:
        pass
    return f"buyer{buyer_id}@example.com"

def get_merchant_email(merchant_id):
    try:
        response = requests.get(f"http://merchant-service:8001/merchants/{merchant_id}")
        if response.status_code == 200:
            return response.json().get('email')
    except:
        pass
    return f"merchant{merchant_id}@example.com"

def get_product_name(product_id):
    return f"Product {product_id}"

def handle_order_created(event_data):
    order_id = event_data.get('id')
    buyer_id = event_data.get('buyerId')
    merchant_id = event_data.get('merchantId')
    product_id = event_data.get('productId')
    discount = event_data.get('discount', 0)
    
    buyer_email = get_buyer_email(buyer_id)
    merchant_email = get_merchant_email(merchant_id)
    product_name = get_product_name(product_id)
    
    subject = "Order has been created"
    body = f"Order {order_id} has been created for product '{product_name}' with discount {discount*100}%"
    
    # Send to kaupanda
    send_email(buyer_email, subject, body)
    # Send to seljanda
    send_email(merchant_email, subject, body)

def handle_payment_success(event_data):
    """Handle payment_success event"""
    order_id = event_data.get('id')
    buyer_id = event_data.get('buyerId')
    merchant_id = event_data.get('merchantId')
    
    buyer_email = get_buyer_email(buyer_id)
    merchant_email = get_merchant_email(merchant_id)
    
    subject = "Order has been purchased"
    body = f"Order {order_id} has been successfully purchased"
    
    # Sendir til kaupanda
    send_email(buyer_email, subject, body)
    # Sendir til seljanda
    send_email(merchant_email, subject, body)

def handle_payment_failure(event_data):
    """Handle payment_failed event"""
    order_id = event_data.get('id')
    buyer_id = event_data.get('buyerId')
    merchant_id = event_data.get('merchantId')
    
    buyer_email = get_buyer_email(buyer_id)
    merchant_email = get_merchant_email(merchant_id)
    
    subject = "Order purchase failed"
    body = f"Order {order_id} purchase has failed"
    
    # Sendir til kaupanda
    send_email(buyer_email, subject, body)
    # Sendir til seljanda
    send_email(merchant_email, subject, body)

def start_consuming():
    """Start consuming RabbitMQ events"""
    print("🚀 Starting EmailService...")
    
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=os.getenv('RABBITMQ_URL', 'rabbitmq'),
                    port=5672
                )
            )
            channel = connection.channel()
            
            # declare queues
            queues = ['order_created', 'payment_success', 'payment_failed']
            for queue in queues:
                channel.queue_declare(queue=queue)
            
            print("✅ Connected to RabbitMQ. Waiting for events...")
            
            def callback(ch, method, properties, body):
                try:
                    event_data = json.loads(body)
                    print(f"📨 Received event from queue: {method.routing_key}")
                    print(f"Event data: {event_data}")
                    
                    if method.routing_key == 'order_created':
                        handle_order_created(event_data)
                    elif method.routing_key == 'payment_success':
                        handle_payment_success(event_data)
                    elif method.routing_key == 'payment_failed':
                        handle_payment_failure(event_data)
                    
                    print(f"✅ Processed event from {method.routing_key}")
                    
                except Exception as e:
                    print(f"❌ Error processing event: {e}")
            
            # tekur frá öllum queues
            for queue in queues:
                channel.basic_consume(
                    queue=queue,
                    on_message_callback=callback,
                    auto_ack=True
                )
            
            channel.start_consuming()
            
        except pika.exceptions.AMQPConnectionError:
            print("❌ Cannot connect to RabbitMQ. Retrying in 5 seconds...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("🛑 EmailService stopped by user")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}. Restarting in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    start_consuming()