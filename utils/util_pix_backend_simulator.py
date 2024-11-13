import os
import redis
import json
from datetime import datetime
import random
import time

# Redis configuration from environment
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
inbound_stream_name = os.getenv("REDIS_STREAM", "pix_payments")  # Stream name for PIX payments
backend_id = os.getenv("BACKEND_ID", "1")  # Example backend ID, replace with desired ID
backend_response_prefix = os.getenv("BACKEND_RESPONSE_PREFIX", "backend_bacen_response_")  # Prefix for backend response streams
num_requests = int(os.getenv("NUM_REQUESTS", 1000))  # Number of PIX requests to inject

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

# Function to inject multiple PIX payment messages into the inbound stream
def inject_multiple_messages(num_requests):
    # Create backend-specific response stream (e.g., backend_bacen_response_1)
    backend_response_stream = f"{backend_response_prefix}{backend_id}"

    # Try to create the consumer group, ignore error if it already exists
    try:
        redis_client.xgroup_create(backend_response_stream, "response_group", id="0", mkstream=True)
        print(f"Created backend response stream: {backend_response_stream}")
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP Consumer Group name already exists" in str(e):
            print(f"Consumer group for {backend_response_stream} already exists.")
        else:
            raise e

    # Send multiple PIX messages to the inbound stream
    for _ in range(num_requests):
        transaction_id = f"txn_{random.randint(100000, 999999)}"  # Random transaction ID
        pix_message = generate_pix_payment(transaction_id, backend_id)
        redis_client.xadd(inbound_stream_name, pix_message)
        print(f"Sent PIX message to {inbound_stream_name} for transaction {transaction_id}")
        time.sleep(0.01)  # Optional: slight delay to simulate realistic injection

if __name__ == "__main__":
    inject_multiple_messages(num_requests)