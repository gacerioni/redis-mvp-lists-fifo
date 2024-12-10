import os
import redis
import json
from datetime import datetime
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# Redis configuration from environment
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
inbound_stream_name = os.getenv("REDIS_STREAM", "pix_payments")  # Stream name for PIX payments
backend_id = os.getenv("BACKEND_ID", "1")  # Example backend ID, replace with desired ID
randomize_backend_id = os.getenv("RANDOMIZE_BACKEND_ID", "false").lower() == "true" # this changes the backend_id to a random value
backend_ids = [f"{i}" for i in range(1, 5)]  # BE IDs: 1, 2, 3, 4 - in case you want to randomize the backend_id
backend_response_prefix = os.getenv("BACKEND_RESPONSE_PREFIX", "backend_bacen_response_")  # Prefix for backend response streams
num_requests = int(os.getenv("NUM_REQUESTS", 1000))  # Number of PIX requests to inject
batch_size = int(os.getenv("BATCH_SIZE", 250))  # Number of messages per batch
num_threads = int(os.getenv("NUM_THREADS", 5))  # Number of parallel threads

# Initialize Redis connection
redis_client = redis.from_url(redis_url)

# Generate a single PIX payment message
def generate_pix_payment(transaction_id):
    assigned_backend_id = random.choice(backend_ids) if randomize_backend_id else backend_id
    return {
        "transaction_id": transaction_id,
        "backend_id": assigned_backend_id,
        "amount": round(random.uniform(1, 1000), 2),  # Random amount between 1 and 1000 BRL
        "timestamp": datetime.now().isoformat()  # Current timestamp
    }

# Function to inject a batch of PIX payment messages using a pipeline
def inject_batch(batch_size):
    with redis_client.pipeline() as pipe:
        for _ in range(batch_size):
            transaction_id = f"txn_{random.randint(100000, 999999)}"  # Random transaction ID
            pix_message = generate_pix_payment(transaction_id)
            pipe.xadd(inbound_stream_name, pix_message)
        pipe.execute()

# Function to handle multithreaded injection
def inject_multiple_messages(num_requests, batch_size, num_threads):
    # Create backend-specific response streams for all backend IDs
    if randomize_backend_id:
        for be_id in backend_ids:
            backend_response_stream = f"{backend_response_prefix}{be_id}"
            try:
                redis_client.xgroup_create(backend_response_stream, "response_group", id="0", mkstream=True)
                print(f"Created backend response stream: {backend_response_stream}")
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP Consumer Group name already exists" in str(e):
                    print(f"Consumer group for {backend_response_stream} already exists.")
                else:
                    raise e
    else:
        # Default single backend ID response stream
        backend_response_stream = f"{backend_response_prefix}{backend_id}"
        try:
            redis_client.xgroup_create(backend_response_stream, "response_group", id="0", mkstream=True)
            print(f"Created backend response stream: {backend_response_stream}")
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP Consumer Group name already exists" in str(e):
                print(f"Consumer group for {backend_response_stream} already exists.")
            else:
                raise e

    # Using ThreadPoolExecutor for parallel message injection
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [
            executor.submit(inject_batch, min(batch_size, num_requests - i))
            for i in range(0, num_requests, batch_size)
        ]
        for future in as_completed(futures):
            try:
                future.result()  # We use result() to catch exceptions if any
            except Exception as exc:
                print(f"Batch failed with exception: {exc}")

if __name__ == "__main__":
    inject_multiple_messages(num_requests, batch_size, num_threads)