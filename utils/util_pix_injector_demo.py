import os
import redis
import json
from datetime import datetime
import random
import time

# Redis configuration from environment
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
num_lists = int(os.getenv("NUM_LISTS", 4))  # Number of lists to distribute across, default to 4
source_queue_base = os.getenv("REDIS_LIST", "source_list")
counter_key = "processed_count"  # This key tracks the number of processed messages
total_amount_key = "total_amount"  # This key tracks the total amount processed
list_size = int(os.getenv("LIST_SIZE", 100000))
batch_size = 25  # Batch size for each LPUSH operation

# Determine if we should use hash tags
use_hashtag = os.getenv("USE_HASHTAG", "false").lower() == "true"

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


# Optimized injector function to distribute PIX payment JSON messages across multiple lists in batches
def inject_messages(list_size):
    print(f"Injecting {list_size} PIX payment messages across {num_lists} lists...")

    # Clear existing items in source queues and counters
    for i in range(num_lists):
        # Conditionally apply hash tags based on use_hashtag
        list_name = f"{source_queue_base}_{i}"
        if use_hashtag:
            list_name = f"{{{list_name}}}"
        redis_client.delete(list_name)

    redis_client.delete(counter_key)
    redis_client.delete(total_amount_key)
    print("Cleaned up existing messages and counters.")

    # Track total amount injected for logging purposes
    total_injected_amount = 0

    # Generate and distribute PIX payment messages across multiple lists in batches
    for list_index in range(num_lists):
        # Conditionally apply hash tags based on use_hashtag
        list_name = f"{source_queue_base}_{list_index}"
        if use_hashtag:
            list_name = f"{{{list_name}}}"

        # Prepare the batches for this list
        batches = [
            [generate_pix_payment(j) for j in range(i, min(i + batch_size, list_size // num_lists))]
            for i in range(0, list_size // num_lists, batch_size)
        ]

        # Inject each batch into the Redis list with a single LPUSH command
        for batch in batches:
            redis_client.lpush(list_name, *batch)
            batch_total = sum(float(json.loads(msg)["amount"]) for msg in batch)
            total_injected_amount += batch_total

            print(f"Injected a batch of {len(batch)} messages into {list_name}")

    # Log the total injected amount
    redis_client.set(total_amount_key, total_injected_amount)
    print(f"Finished injecting {list_size} PIX payment messages across {num_lists} lists.")
    print(f"Total amount injected: BRL {total_injected_amount:.2f}")


# Monitor function to track processed messages
def monitor_processed_count(start_time):
    print("Starting to monitor processed messages...")
    end_time = None  # Initialize end time for last message

    while True:
        # Fetch current count from the counter key
        processed_count = redis_client.get(counter_key)
        processed_count = int(processed_count) if processed_count else 0

        # Fetch current total amount processed
        total_amount = redis_client.get(total_amount_key)
        total_amount = float(total_amount) if total_amount else 0

        print(f"Total messages processed: {processed_count}")
        print(f"Total amount processed: BRL {total_amount:.2f}")

        # Check if all messages are processed
        if processed_count >= list_size:
            end_time = time.time()
            print("All messages processed.")
            break

        time.sleep(0.1)  # Poll more frequently for accurate timing

    # Calculate the total processing time
    if start_time and end_time:
        total_time = end_time - start_time
        print(f"Total time to process all messages: {total_time:.4f} seconds")


if __name__ == "__main__":
    # Start timing
    start_time = time.time()

    # Inject messages
    inject_messages(list_size)

    # Monitor processed messages and calculate total latency
    monitor_processed_count(start_time)