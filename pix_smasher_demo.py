import os
import random
import redis
import time
import socket
from datetime import datetime

# Redis configuration from environment
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
stream_name = os.getenv("REDIS_STREAM", "pix_payments")  # Stream name for PIX payments
group_name = os.getenv("GROUP_NAME", "pix_consumers")  # Consumer group name
consumer_name = f"consumer_{socket.gethostname()}_{random.randint(1000, 9999)}"
idle_threshold_ms = int(os.getenv("IDLE_THRESHOLD_MS", 5000))  # Idle threshold for claiming messages (default 5s)
backend_response_prefix = os.getenv("BACKEND_RESPONSE_PREFIX",
                                    "backend_bacen_response_")  # Prefix for backend response streams

# Initialize Redis connection
redis_client = redis.from_url(redis_url)


# Function to initialize the consumer group
def initialize_consumer_group():
    while True:
        try:
            redis_client.xgroup_create(stream_name, group_name, id='0', mkstream=True)
            print(f"Created consumer group '{group_name}' on stream '{stream_name}'")
            break
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP Consumer Group name already exists" in str(e):
                print(f"Consumer group '{group_name}' already exists on stream '{stream_name}'")
                break
            elif "NOGROUP" in str(e) or "NO such key" in str(e):
                print(f"Waiting for stream '{stream_name}' to be created by the producer...")
                time.sleep(2)
            else:
                raise e


# Process messages from the stream
def process_messages():
    print(f"Starting consumer {consumer_name} for stream: {stream_name}...")
    initialize_consumer_group()

    while True:
        try:
            messages = redis_client.xreadgroup(
                groupname=group_name,
                consumername=consumer_name,
                streams={stream_name: '>'},
                count=1,
                block=5000  # Block for 5 seconds if no new messages
            )
        except redis.exceptions.ResponseError as e:
            if "NOGROUP" in str(e):
                print("Consumer group or stream was deleted, reinitializing consumer group...")
                initialize_consumer_group()
                continue
            else:
                raise e

        if not messages:
            review_pending()  # Check for stalled messages if no new messages are available
            continue

        for stream, message_entries in messages:
            for message_id, message_data in message_entries:
                try:
                    # Extract amount, transaction_id, and backend_id from message data
                    amount = float(message_data.get(b"amount", 0))
                    transaction_id = message_data.get(b"transaction_id", b"").decode("utf-8")
                    backend_id = message_data.get(b"backend_id", b"").decode("utf-8")

                    # Perform the dummy processing (count and sum amounts)
                    redis_client.incr("processed_count")
                    #redis_client.incrbyfloat("total_amount", amount)

                    # Acknowledge the message as processed
                    redis_client.xack(stream_name, group_name, message_id)
                    print(
                        f"Processed message ID: {message_id}, Amount: {amount}, Backend ID: {backend_id}, Transaction ID: {transaction_id}")

                    # Send confirmation to the specific backend's response stream
                    response_stream_name = f"{backend_response_prefix}{backend_id}"
                    confirmation_message = {
                        "transaction_id": transaction_id,
                        "status": "confirmed",
                        "processed_amount": amount,
                        "backend_id": backend_id,
                        "timestamp": datetime.now().isoformat()
                    }
                    redis_client.xadd(response_stream_name, confirmation_message)
                    print(f"Sent confirmation to {response_stream_name} for transaction ID: {transaction_id}")

                except (ValueError, KeyError) as e:
                    print(f"Error processing message ID {message_id}: {e}")


# Function to review and claim pending messages if they've been idle too long
def review_pending():
    print("Reviewing pending messages for entire consumer group...")

    # Fetch up to 10 pending messages in the consumer group with idle time above the threshold
    pending_messages = redis_client.xpending_range(
        stream_name, group_name, "-", "+", 10
    )

    for pending in pending_messages:
        message_id = pending["message_id"]
        idle_time = pending["time_since_delivered"]

        # Claim message if idle time exceeds threshold, allowing any consumer to claim it
        if idle_time > idle_threshold_ms:
            claimed_messages = redis_client.xclaim(
                stream_name, group_name, consumer_name, min_idle_time=idle_threshold_ms, message_ids=[message_id]
            )
            for msg_id, msg_data in claimed_messages:
                try:
                    # Similar processing for the re-claimed message
                    amount = float(msg_data.get(b"amount", 0))
                    transaction_id = msg_data.get(b"transaction_id", b"").decode("utf-8")
                    backend_id = msg_data.get(b"backend_id", b"").decode("utf-8")

                    # Process and acknowledge
                    redis_client.incr("processed_count")
                    #redis_client.incrbyfloat("total_amount", amount)
                    redis_client.xack(stream_name, group_name, msg_id)
                    print(
                        f"Claimed and processed stalled message ID: {msg_id}, Amount: {amount}, Backend ID: {backend_id}")

                    # Send confirmation to specific backend's response stream
                    response_stream_name = f"{backend_response_prefix}{backend_id}"
                    confirmation_message = {
                        "transaction_id": transaction_id,
                        "status": "confirmed",
                        "processed_amount": amount,
                        "backend_id": backend_id,
                        "timestamp": datetime.now().isoformat()
                    }
                    redis_client.xadd(response_stream_name, confirmation_message)
                    print(f"Sent confirmation to {response_stream_name} for transaction ID: {transaction_id}")

                except (ValueError, KeyError) as e:
                    print(f"Error processing stalled message ID {msg_id}: {e}")


if __name__ == "__main__":
    process_messages()