import os
import redis
import json
from datetime import datetime
import random
import time

# Redis configuration from environment
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
stream_name = os.getenv("REDIS_STREAM", "pix_payments")  # Stream name for PIX payments
counter_key = "processed_count"  # This key tracks the number of processed messages
total_amount_key = "total_amount"  # This key tracks the total amount processed
stream_size = int(os.getenv("STREAM_SIZE", 500000))
batch_size = 1000  # Batch size for each pipelined XADD operation

# Initialize Redis connection
redis_client = redis.from_url(redis_url)


# Function to generate a PIX payment message in a hash-like structure
def generate_pix_payment(transaction_id):
    return {
        "transaction_id": f"{transaction_id}",
        "amount": round(random.uniform(1, 1000), 2),  # Random amount between 1 and 1000 BRL
        "timestamp": datetime.now().isoformat()  # Current timestamp
    }


# Optimized injector function to push PIX payment messages into the Redis stream using pipelining
def inject_messages_with_pipeline(stream_size):
    print(f"Injecting {stream_size} PIX payment messages into stream: {stream_name}...")

    # Clear existing items in the stream and counters
    redis_client.delete(stream_name)
    redis_client.delete(counter_key)
    redis_client.delete(total_amount_key)
    print("Cleaned up existing messages and counters.")

    # Track total amount injected for logging purposes
    total_injected_amount = 0

    # Generate and push PIX payment messages to the stream in batches with pipelining
    for i in range(0, stream_size, batch_size):
        batch = [generate_pix_payment(j) for j in range(i, min(i + batch_size, stream_size))]

        # Pipeline for batch injection
        with redis_client.pipeline() as pipe:
            for msg in batch:
                pipe.xadd(stream_name, msg)
                total_injected_amount += msg["amount"]
            # Execute all XADD operations in the pipeline
            pipe.execute()

        print(f"Injected a batch of {len(batch)} messages into {stream_name}")

    # Log the total injected amount
    redis_client.set(total_amount_key, total_injected_amount)
    print(f"Finished injecting {stream_size} PIX payment messages into the stream.")
    print(f"Total amount injected: BRL {total_injected_amount:.2f}")


# Monitor function to track processed messages
def monitor_processed_count(start_time):
    print("Starting to monitor processed messages...")
    end_time = None  # Initialize end time for last message

    while True:
        # Fetch current count from the counter key
        try:
            processed_count = redis_client.get(counter_key)
            processed_count = int(processed_count) if processed_count else 0
        except (ValueError, TypeError) as e:
            print(f"Error reading processed_count: {e}")
            processed_count = 0

        # Fetch current total amount processed
        try:
            total_amount = redis_client.get(total_amount_key)
            total_amount = float(total_amount) if total_amount else 0
        except (ValueError, TypeError) as e:
            print(f"Error reading total_amount: {e}")
            total_amount = 0

        print(f"Total messages processed: {processed_count}")
        print(f"Total amount processed: BRL {total_amount:.2f}")

        # Check if all messages are processed
        if processed_count >= stream_size:
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

    # Inject messages with pipelining
    inject_messages_with_pipeline(stream_size)

    # Monitor processed messages and calculate total latency
    monitor_processed_count(start_time)