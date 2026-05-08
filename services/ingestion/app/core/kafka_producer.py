# ============================================================
# kafka_producer.py — Sends messages to Kafka topics
# ============================================================
import json
from aiokafka import AIOKafkaProducer
from app.core.config import settings

_producer = None


async def get_producer() -> AIOKafkaProducer:
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await _producer.start()
    return _producer


async def close_producer():
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None


async def publish(topic: str, message: dict):
    """
    Publishes a message to a Kafka topic.

    Example:
        await publish("doc.uploaded", {
            "document_id": "abc-123",
            "tenant_id": "xyz-456",
            "s3_key": "tenants/xyz-456/doc.pdf"
        })
    """
    producer = await get_producer()
    await producer.send_and_wait(topic, message)
    print(f"📨 Published to {topic}: {message}")