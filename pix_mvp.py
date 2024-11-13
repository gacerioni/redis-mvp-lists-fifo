import os
import redis
import json

# Redis configuration from environment
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
source_queue_base = os.getenv("REDIS_LIST", "source_list")  # Base name for lists
list_index = int(os.getenv("LIST_INDEX", 0))  # Unique list index assigned per consumer
use_hashtag = os.getenv("USE_HASHTAG", "false").lower() == "true"  # Determine if we should use hash tags

# Apply hash tags if USE_HASHTAG is enabled
if use_hashtag:
    source_queue = f"{{{source_queue_base}_{list_index}}}"
else:
    source_queue = f"{source_queue_base}_{list_index}"

# Initialize Redis connection≠
pool = redis.ConnectionPool.from_url(redis_url)
redis_client = redis.Redis(connection_pool=pool)

# Define keys for tracking
counter_key = "processed_count"
total_amount_key = "total_amount"

def process_items():
    print(f"Starting consumer for list: {source_queue}...")

    while True:
        # Block until an item is available in the specified source_queue
        item = redis_client.brpop(source_queue, timeout=0)
        if item:
            queue_name, message = item
            try:
                # Parse JSON message
                transaction = json.loads(message)

                # Extract the amount value
                amount = float(transaction.get("amount", 0))

                # Increment the processed count and total amount
                redis_client.incr(counter_key)
                redis_client.incrbyfloat(total_amount_key, amount)

                # Optional logging
                # print(f"Processed transaction {transaction['transaction_id']}: BRL {amount}")
                # print(f"Total messages processed: {redis_client.get(counter_key).decode()}")
                # print(f"Total amount processed: BRL {redis_client.get(total_amount_key).decode()}")

            except (ValueError, KeyError) as e:
                print(f"Error processing message: {e}")

if __name__ == "__main__":
    process_items()