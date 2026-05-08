# ============================================================
# main.py — Processing Service entry point
# This service has NO HTTP endpoints — it's a pure Kafka consumer
# It runs forever, waiting for messages on "doc.uploaded"
# ============================================================
import asyncio
import json
from aiokafka import AIOKafkaConsumer
from app.core.config import settings
from app.core.database import get_pool, close_pool
from app.workers.pipeline import process_document


async def consume():
    """
    Main consumer loop.
    Reads from Kafka topic 'doc.uploaded' and processes each message.
    """
    pool = await get_pool()

    consumer = AIOKafkaConsumer(
        "doc.uploaded",
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="processing-workers",   # consumer group for load balancing
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",    # start from beginning if no offset saved
        enable_auto_commit=True,         # commit offset after processing
    )

    await consumer.start()
    print("✅ Processing worker started — listening on 'doc.uploaded'")

    try:
        async for message in consumer:
            event = message.value
            print(f"\n📩 Received event: {event.get('filename')} "
                  f"(partition={message.partition}, offset={message.offset})")

            await process_document(event, pool)

    except asyncio.CancelledError:
        print("🛑 Consumer shutting down...")
    finally:
        await consumer.stop()
        await close_pool()


if __name__ == "__main__":
    print("🚀 Processing Service starting...")
    asyncio.run(consume())