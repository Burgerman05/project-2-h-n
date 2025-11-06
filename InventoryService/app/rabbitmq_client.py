import pika
import json
import os
import time
import logging

class RabbitMQClient:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.max_retries = 5
        self.retry_delay = 5

    def connect(self):
        """Establish connection to RabbitMQ with retry logic"""
        for attempt in range(self.max_retries):
            try:
                self.connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=os.getenv('RABBITMQ_URL', 'rabbitmq'),
                        port=5672,
                        connection_attempts=3,
                        retry_delay=3,
                        heartbeat=600,
                        blocked_connection_timeout=300
                    )
                )
                self.channel = self.connection.channel()
                
                # Declare queues as durable to survive broker restarts
                self.channel.queue_declare(queue='payment_success', durable=True)
                self.channel.queue_declare(queue='payment_failed', durable=True)
                
                logging.info("✅ Successfully connected to RabbitMQ")
                return True
                
            except Exception as e:
                logging.warning(f"❌ Failed to connect to RabbitMQ (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    
        logging.error("❌ Could not connect to RabbitMQ after all retries")
        self.connection = None
        self.channel = None
        return False

    def is_connected(self):
        """Check if we have a valid connection"""
        return (self.connection and not self.connection.is_closed and 
                self.channel and not self.channel.is_closed)

    def ensure_connection(self):
        """Ensure we have a valid connection before consuming"""
        if not self.is_connected():
            return self.connect()
        return True

    def start_consuming(self, callback):
        """Start consuming messages with connection validation"""
        if not self.ensure_connection():
            logging.error("❌ Cannot start consuming: No RabbitMQ connection")
            return False
            
        try:
            # Set up quality of service
            self.channel.basic_qos(prefetch_count=1)
            
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
            
            logging.info("🔄 InventoryService listening for payment events...")
            self.channel.start_consuming()
            return True
            
        except Exception as e:
            logging.error(f"❌ Error while starting consumer: {e}")
            # Try to reconnect and restart consuming
            self.close()
            time.sleep(2)
            return self.start_consuming(callback)  # Recursive retry

    def safe_consume(self, callback):
        """Wrapper for consuming with automatic reconnection"""
        while True:
            try:
                if self.start_consuming(callback):
                    break  # Successfully started consuming
                else:
                    logging.warning("🔄 Retrying to connect in 10 seconds...")
                    time.sleep(10)
            except KeyboardInterrupt:
                logging.info("🛑 Consumer stopped by user")
                break
            except Exception as e:
                logging.error(f"❌ Unexpected error in consumer: {e}")
                logging.warning("🔄 Reconnecting in 10 seconds...")
                time.sleep(10)

    def close(self):
        """Close the connection gracefully"""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                logging.info("🔌 RabbitMQ connection closed")
        except Exception as e:
            logging.error(f"❌ Error closing connection: {e}")
        finally:
            self.connection = None
            self.channel = None