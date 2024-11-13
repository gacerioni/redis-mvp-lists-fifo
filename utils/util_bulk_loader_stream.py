import json
import random
from datetime import datetime

# Function to generate a PIX payment message
def generate_pix_payment(transaction_id):
    return {
        "transaction_id": f"{transaction_id}",
        "amount": round(random.uniform(1, 1000), 2),  # Random amount between 1 and 1000 BRL
        "timestamp": datetime.now().isoformat()  # Current timestamp
    }

# Function to generate Redis protocol for XADD with batched items for a stream
def generate_redis_protocol_for_stream(batch_size, total_items, file_name, stream_name="pix_payments"):
    with open(file_name, 'w') as f:
        for start_id in range(0, total_items, batch_size):
            batch = [generate_pix_payment(i) for i in range(start_id, start_id + batch_size)]
            for item in batch:
                # Construct the XADD command in Redis protocol format
                f.write(f"*{4 + len(item)}\r\n$4\r\nXADD\r\n${len(stream_name)}\r\n{stream_name}\r\n$1\r\n*\r\n")
                for key, value in item.items():
                    value_str = str(value)
                    f.write(f"${len(key)}\r\n{key}\r\n${len(value_str)}\r\n{value_str}\r\n")
    print(f"Bulk load file '{file_name}' generated with {total_items} items for stream '{stream_name}'.")

# Parameters for bulk loading
batch_size = 10000    # Number of items per batch
total_items = 100_000  # Total items to generate for the stream
file_name = 'bulk_load_pix_stream_data.txt'

generate_redis_protocol_for_stream(batch_size, total_items, file_name)