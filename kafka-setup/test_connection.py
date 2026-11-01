"""
Test script to verify laptop can connect to Kafka on EC2.
Usage: python test_connection.py <PUBLIC_IP>
Example: python test_connection.py 13.235.10.20
"""

import sys
import json
import time
import uuid
from confluent_kafka import Producer, Consumer, KafkaError

def test_kafka(public_ip):
    bootstrap = f"{public_ip}:9092"
    topic = "test-connection"
    print(f"\nConnecting to Kafka at {bootstrap}...\n")

    # --- PRODUCER TEST ---
    delivery_errors = []

    def on_delivery(err, msg):
        if err:
            delivery_errors.append(str(err))
            print(f"Delivery FAILED: {err}")
        else:
            print(f"Delivered to {msg.topic()} partition {msg.partition()}")

    producer = Producer({"bootstrap.servers": bootstrap})
    sent = 0
    for i in range(10):
        msg = json.dumps({"test": i, "msg": "hello from laptop"})
        producer.produce(topic, value=msg, callback=on_delivery)
        producer.poll(0)
        sent += 1
    producer.flush()
    print(f"Sent {sent}/10 messages, errors: {len(delivery_errors)}")

    # --- CONSUMER TEST ---
    from confluent_kafka import TopicPartition
    consumer = Consumer({
        "bootstrap.servers": bootstrap,
        "group.id": f"test-group-{uuid.uuid4()}",
        "auto.offset.reset": "earliest",
    })
    # Directly assign partition instead of subscribe() to avoid group coordinator
    consumer.assign([TopicPartition(topic, 0, 0)])

    read = 0
    start = time.time()
    while time.time() - start < 15:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print(f"Error: {msg.error()}")
            continue
        read += 1
        if read >= 10:
            break

    consumer.close()
    print(f"Read {read} messages")

    # --- RESULT ---
    print("")
    if sent == 10 and read >= 10:
        print("PASS - Kafka connection is working!")
    else:
        print("FAIL - Something went wrong. Check the troubleshooting guide.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_connection.py <PUBLIC_IP>")
        sys.exit(1)
    test_kafka(sys.argv[1])
