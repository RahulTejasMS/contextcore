#!/bin/bash
# ============================================================
# topics.sh — Creates all Kafka topics for ContextCore
# Run this once after Kafka starts
# ============================================================

KAFKA_CONTAINER="contextcore-kafka"

echo "Creating Kafka topics..."

# doc.uploaded — fired when a file is uploaded to MinIO
docker exec $KAFKA_CONTAINER kafka-topics \
  --create --if-not-exists \
  --bootstrap-server localhost:9092 \
  --topic doc.uploaded \
  --partitions 3 \
  --replication-factor 1

# doc.chunked — fired when a document has been parsed and chunked
docker exec $KAFKA_CONTAINER kafka-topics \
  --create --if-not-exists \
  --bootstrap-server localhost:9092 \
  --topic doc.chunked \
  --partitions 3 \
  --replication-factor 1

# doc.embedded — fired when chunks have been embedded into Qdrant
docker exec $KAFKA_CONTAINER kafka-topics \
  --create --if-not-exists \
  --bootstrap-server localhost:9092 \
  --topic doc.embedded \
  --partitions 3 \
  --replication-factor 1

# doc.failed — fired when any stage fails (dead letter queue)
docker exec $KAFKA_CONTAINER kafka-topics \
  --create --if-not-exists \
  --bootstrap-server localhost:9092 \
  --topic doc.failed \
  --partitions 1 \
  --replication-factor 1

echo "Listing all topics:"
docker exec $KAFKA_CONTAINER kafka-topics \
  --list \
  --bootstrap-server localhost:9092