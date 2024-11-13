import os
import redis
import json
from datetime import datetime
import random
import time

# Redis configuration from environment
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
inbound_stream_name = os.getenv("REDIS_STREAM", "pix_payments")  # Stream name for PIX payments
backend_id = os.getenv("BACKEND_ID", "1")  # Backend ID, replace with desired ID
backend_response_prefix = os.getenv("BACKEND_RESPONSE_PREFIX", "backend_bacen_response_")  # Prefix for backend response streams

# Initialize Redis connection
redis_client = redis.from_url(redis_url)


# Generate a single PIX payment message
def generate_pix_payment(transaction_id, backend_id):
    return {
        "transaction_id": transaction_id,
        "backend_id": backend_id,
        "amount": round(random.uniform(1, 1000), 2),  # Random amount between 1 and 1000 BRL
        "timestamp": datetime.now().isoformat()  # Current timestamp
    }


# Function to inject a single PIX payment message and wait for confirmation
def inject_and_wait_for_confirmation():
    transaction_id = f"txn_{random.randint(100000, 999999)}"  # Random transaction ID
    backend_response_stream = f"{backend_response_prefix}{backend_id}"  # Response stream for this backend
    group_name = f"response_group_{backend_id}"  # Consumer group name unique to this backend ID
    consumer_name = f"consumer_{backend_id}"

    # Ensure the consumer group exists for the backend response stream
    try:
        redis_client.xgroup_create(backend_response_stream, group_name, id="0", mkstream=True)
        print(f"Created consumer group '{group_name}' on stream '{backend_response_stream}'")
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP Consumer Group name already exists" in str(e):
            print(f"Consumer group '{group_name}' already exists for stream '{backend_response_stream}'")
        else:
            raise e

    # Send the PIX message to the inbound stream
    pix_message = generate_pix_payment(transaction_id, backend_id)
    redis_client.xadd(inbound_stream_name, pix_message)
    print(f"Sent PIX message to {inbound_stream_name} for transaction {transaction_id}")

    # Wait for confirmation on the backend response stream
    print(f"Waiting for confirmation on stream {backend_response_stream}...")
    while True:
        # Block and read the next message from the group; use '>' to only receive new messages
        messages = redis_client.xreadgroup(group_name, consumer_name, {backend_response_stream: ">"}, block=30000, count=1)

        if messages:
            for stream, message_entries in messages:
                for message_id, message_data in message_entries:
                    # Check if confirmation message corresponds to our transaction
                    if message_data[b"transaction_id"].decode() == transaction_id:
                        print(f"Received confirmation for transaction {transaction_id}: {message_data}")
                        # Acknowledge the message to mark it as processed
                        redis_client.xack(backend_response_stream, group_name, message_id)
                        return  # Exit once confirmation is received


if __name__ == "__main__":
    inject_and_wait_for_confirmation()