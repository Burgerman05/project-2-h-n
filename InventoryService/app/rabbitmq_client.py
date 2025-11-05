import pika
import json
import os

class RabbitMQClient:
    def __init__(self):
        self.connection = None
        self.channel = None
        
    def connect(self):
        try:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=os.getenv('RABBITMQ_URL', 'rabbitmq'),
                    port=5672,
                    connection_attempts=5,  
                    retry_delay=5  
                )
            )
            self.channel = self.connection.channel()
            # Declare queues we listen to
            self.channel.queue_declare(queue='payment_success')
            self.channel.queue_declare(queue='payment_failed')
            print("✅ Connected to RabbitMQ")
        except Exception as e:
            print(f"❌ Failed to connect to RabbitMQ: {e}")
            self.connection = None
            self.channel = None
    
    def start_consuming(self, callback):
        if not self.channel:
            self.connect()
            
        # Consume from payment queues
        self.channel.basic_consume(
            queue='payment_success', 
            on_message_callback=callback, 
            auto_ack=True
        )
        self.channel.basic_consume(
            queue='payment_failed', 
            on_message_callback=callback, 
            auto_ack=True
        )
        
        print("🔄 InventoryService listening for payment events...")
        self.channel.start_consuming()
    
    def close(self):
        if self.connection:
            self.connection.close()