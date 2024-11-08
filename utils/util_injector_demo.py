import os
import redis
import time

# Redis configuration from environment
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
source_queue = os.getenv("REDIS_LIST", "source_list")
counter_key = "processed_count"  # This key tracks the number of processed messages
list_size = int(os.getenv("LIST_SIZE", 1000000))

# Initialize Redis connection
pool = redis.ConnectionPool.from_url(redis_url)
redis_client = redis.Redis(connection_pool=pool)


# Injector function to fill the list with a range of values
def inject_messages(list_size):
    print(f"Injecting {list_size} messages into {source_queue}...")

    # Clear existing items in source queue and counter
    redis_client.delete(source_queue)
    redis_client.delete(counter_key)

    # Push a range of items into the list
    for i in range(list_size):
        redis_client.lpush(source_queue, i)

    print(f"Injected {list_size} messages into {source_queue}")


# Monitor function to track processed messages
def monitor_processed_count():
    print("Starting to monitor processed messages...")
    while True:
        # Fetch current count from the counter key
        processed_count = redis_client.get(counter_key)
        processed_count = int(processed_count) if processed_count else 0
        print(f"Total messages processed: {processed_count}")

        # Exit if all messages have been processed
        if processed_count >= list_size:
            print("All messages processed.")
            break

        time.sleep(1)  # Poll every second


if __name__ == "__main__":
    # Configurable list size
    # Inject messages and start monitoring
    inject_messages(list_size)
    monitor_processed_count()