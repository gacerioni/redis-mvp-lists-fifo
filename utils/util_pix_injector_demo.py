import os
import redis
import time
import json
from datetime import datetime
import random

# Redis configuration from environment
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
source_queue = os.getenv("REDIS_LIST", "source_list")
counter_key = "processed_count"  # This key tracks the number of processed messages
list_size = int(os.getenv("LIST_SIZE", 100000))

# Initialize Redis connection
pool = redis.ConnectionPool.from_url(redis_url)
redis_client = redis.Redis(connection_pool=pool)

# Function to generate a PIX payment JSON string
def generate_pix_payment(transaction_id):
    return json.dumps({
        "transaction_id": f"{transaction_id}",
        "amount": round(random.uniform(1, 1000), 2),  # Random amount between 1 and 1000 BRL
        "timestamp": datetime.now().isoformat()  # Current timestamp
    })

# Injector function to fill the list with PIX payment JSON messages
def inject_messages(list_size):
    print(f"Injecting {list_size} PIX payment messages into {source_queue}...")

    # Clear existing items in source queue and counter
    redis_client.delete(source_queue)
    redis_client.delete(counter_key)
    print("Cleaned up existing messages and counter.")

    # Generate PIX payment messages and push them in a single LPUSH command
    items = [generate_pix_payment(i) for i in range(list_size)]
    redis_client.lpush(source_queue, *items)

    print(f"Injected {list_size} PIX payment messages into {source_queue} in a single LPUSH.")

# Monitor function to track processed messages
def monitor_processed_count():
    print("Starting to monitor processed messages...")
    start_time = None  # Initialize start time for first message
    end_time = None    # Initialize end time for last message

    while True:
        # Fetch current count from the counter key
        processed_count = redis_client.get(counter_key)
        processed_count = int(processed_count) if processed_count else 0
        print(f"Total messages processed: {processed_count}")

        # Record the start time when the first message is processed
        if processed_count > 0 and start_time is None:
            start_time = time.time()
            print("Processing started...")

        # Record the end time when the last message is processed
        if processed_count >= list_size:
            end_time = time.time()
            print("All messages processed.")
            break

        time.sleep(1)  # Poll every second

    # Calculate the total processing time
    if start_time and end_time:
        total_time = end_time - start_time
        print(f"Total time to process all messages: {total_time:.2f} seconds")

if __name__ == "__main__":
    # Inject messages and start monitoring
    inject_messages(list_size)
    monitor_processed_count()