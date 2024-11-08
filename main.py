import os
import redis

# Redis configuration from environment
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
source_queue = os.getenv("REDIS_LIST", "source_list")

# Initialize connection pool
pool = redis.ConnectionPool.from_url(redis_url)
redis_client = redis.Redis(connection_pool=pool)

# Define a counter key for tracking processed messages
counter_key = "processed_count"

def process_items():
    print("Starting consumer...")

    while True:
        # Block until an item is available in source_queue, then pop from the right side
        item = redis_client.brpop(source_queue, timeout=0)

        if item:
            queue_name, message = item
            print(f"Processed message: {message}")

            # Increment the counter by 1
            redis_client.incr(counter_key)
            # Display current counter value (optional)
            #processed_count = redis_client.get(counter_key)
            #print(f"Total messages processed: {processed_count.decode()}")

if __name__ == "__main__":
    process_items()