import random
from datetime import datetime

# Configuration
output_file = "pix_bulk_load.resp3"
stream_name = "pix_payments"  # Redis stream name
backend_id = "1"  # Example backend ID
total_messages = 1  # Total PIX messages to generate

# Function to generate a single PIX payment message
def generate_pix_payment(transaction_id, backend_id):
    return {
        "transaction_id": transaction_id,
        "backend_id": backend_id,
        "amount": round(random.uniform(1, 1000), 2),  # Random amount between 1 and 1000 BRL
        "timestamp": datetime.now().isoformat()  # Current timestamp
    }

# Function to create RESP3-compatible XADD command
def generate_resp3_xadd(stream_name, message):
    proto = f"*5\r\n"  # Number of elements in XADD command
    proto += f"$4\r\nXADD\r\n"  # XADD command
    proto += f"${len(stream_name)}\r\n{stream_name}\r\n"  # Stream name
    proto += f"$1\r\n*\r\n"  # Auto-generated ID
    for key, value in message.items():
        value_str = str(value)  # Convert value to string
        proto += f"${len(key)}\r\n{key}\r\n"  # Key
        proto += f"${len(value_str)}\r\n{value_str}\r\n"  # Value
    return proto

# Generate RESP3 file for bulk loading
with open(output_file, "w") as file:
    for i in range(total_messages):
        transaction_id = f"txn_{random.randint(100000, 999999)}"
        pix_message = generate_pix_payment(transaction_id, backend_id)
        resp3_command = generate_resp3_xadd(stream_name, pix_message)
        file.write(resp3_command)

print(f"RESP3 bulk load file generated: {output_file}")