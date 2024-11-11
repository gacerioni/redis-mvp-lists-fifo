import json
from datetime import datetime
import random

# Function to generate a PIX payment JSON string
def generate_pix_payment(transaction_id):
    return json.dumps({
        "transaction_id": f"{transaction_id}",
        "amount": round(random.uniform(1, 1000), 2),
        "timestamp": datetime.now().isoformat()
    })

# Function to generate Redis protocol for LPUSH with batched items
def generate_redis_protocol(batch_size, total_items, file_name):
    with open(file_name, 'w') as f:
        for start_id in range(0, total_items, batch_size):
            batch = [generate_pix_payment(i) for i in range(start_id, start_id + batch_size)]
            # Construct the LPUSH command in Redis protocol format
            f.write(f"*{len(batch) + 2}\r\n$5\r\nLPUSH\r\n$11\r\nsource_list\r\n")
            for item in batch:
                f.write(f"${len(item)}\r\n{item}\r\n")

# Parameters for bulk loading
batch_size = 10000   # Number of items per LPUSH
total_items = 225_000_000  # Total items to generate
file_name = 'bulk_load_pix_data.txt'

generate_redis_protocol(batch_size, total_items, file_name)