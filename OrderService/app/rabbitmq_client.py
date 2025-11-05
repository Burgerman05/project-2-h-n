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
                    port=5672
                )
            )
            self.channel = self.connection.channel()
            #  lætur vit hvernig gengur
            self.channel.queue_declare(queue='order_created')
            self.channel.queue_declare(queue='payment_success')
            self.channel.queue_declare(queue='payment_failed')
        except Exception as e:
            print(f"Failed to connect to RabbitMQ: {e}")
    
    def publish_order_created(self, order_data):
        if not self.channel:
            self.connect()
            
        self.channel.basic_publish(
            exchange='',
            routing_key='order_created',
            body=json.dumps(order_data)
        )
        print(f"Published order_created event for order {order_data.get('id')}")
    
    def close(self):
        if self.connection:
            self.connection.close()