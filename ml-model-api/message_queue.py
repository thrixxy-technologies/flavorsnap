import os
import json
import logging
import pika
from pika.exchange_type import ExchangeType
from typing import Callable, Any, Dict

logger = logging.getLogger(__name__)

class MessageQueueManager:
    """Advanced message queue manager with reliability and DLX support"""
    
    def __init__(self, amqp_url: str = None):
        self.amqp_url = amqp_url or os.environ.get("AMQP_URL", "amqp://guest:guest@localhost:5672/")
        self.connection = None
        self.channel = None
        self._setup_connection()

    def _setup_connection(self):
        """Setup connection with retry logic and exchange/queue declarations"""
        try:
            params = pika.URLParameters(self.amqp_url)
            self.connection = pika.BlockingConnection(params)
            self.channel = self.connection.channel()
            
            # Setup Dead Letter Exchange
            self.channel.exchange_declare(
                exchange='dlx', 
                exchange_type=ExchangeType.direct
            )
            self.channel.queue_declare(queue='dead_letter_queue', durable=True)
            self.channel.queue_bind(exchange='dlx', queue='dead_letter_queue', routing_key='dead_letter')
            
            # Setup Main Exchange and Queue with DLX
            self.channel.exchange_declare(
                exchange='flavorsnap_main',
                exchange_type=ExchangeType.topic,
                durable=True
            )
            
            args = {
                'x-dead-letter-exchange': 'dlx',
                'x-dead-letter-routing-key': 'dead_letter'
            }
            self.channel.queue_declare(queue='inference_tasks', durable=True, arguments=args)
            self.channel.queue_bind(exchange='flavorsnap_main', queue='inference_tasks', routing_key='task.inference')
            
            logger.info("Message Queue connection and schema initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Message Queue: {e}")

    def publish_task(self, task_type: str, data: Dict[str, Any], priority: int = 0):
        """Publish a task with persistence and priority"""
        if not self.channel:
            logger.error("Channel not initialized, cannot publish task")
            return False
            
        try:
            properties = pika.BasicProperties(
                delivery_mode=2,  # make message persistent
                priority=priority,
                content_type='application/json',
                headers={'x-request-id': data.get('request_id', 'unknown')}
            )
            
            self.channel.basic_publish(
                exchange='flavorsnap_main',
                routing_key=f'task.{task_type}',
                body=json.dumps(data),
                properties=properties
            )
            logger.info(f"Published task {task_type} with priority {priority}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish task: {e}")
            return False

    def consume_tasks(self, task_type: str, callback: Callable):
        """Consume tasks with manual acknowledgements"""
        if not self.channel:
            logger.error("Channel not initialized, cannot consume tasks")
            return
            
        def on_message(ch, method, properties, body):
            try:
                data = json.loads(body)
                success = callback(data)
                if success:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                else:
                    # Nack and don't requeue if it failed processing - it will go to DLX
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        queue_name = 'inference_tasks' if task_type == 'inference' else f'{task_type}_tasks'
        self.channel.basic_qos(prefetch_count=1) # Fair dispatch
        self.channel.basic_consume(queue=queue_name, on_message_callback=on_message)
        
        logger.info(f"Started consuming tasks from {queue_name}")
        self.channel.start_consuming()

    def get_queue_status(self):
        """Get monitoring info for queues"""
        if not self.channel:
            return {"status": "disconnected"}
            
        q = self.channel.queue_declare(queue='inference_tasks', passive=True)
        return {
            "status": "connected",
            "message_count": q.method.message_count,
            "consumer_count": q.method.consumer_count
        }

# Global instance
mq_manager = MessageQueueManager()
