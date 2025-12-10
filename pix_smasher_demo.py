import os
import random
import redis
import time
import socket
from datetime import datetime
from collections import deque

# Redis configuration from environment
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
stream_name = os.getenv("REDIS_STREAM", "pix_payments")  # Stream name for PIX payments
group_name = os.getenv("GROUP_NAME", "pix_consumers")  # Consumer group name
consumer_name = f"consumer_{socket.gethostname()}_{random.randint(1000, 9999)}"
idle_threshold_ms = int(os.getenv("IDLE_THRESHOLD_MS", 5000))  # Idle threshold for claiming messages (default 5s)
backend_response_prefix = os.getenv("BACKEND_RESPONSE_PREFIX",
                                    "backend_bacen_response_")  # Prefix for backend response streams

# Initialize Redis connection
redis_client = redis.from_url(redis_url)

# Latency tracking - keep last 1000 read latencies for statistics
latency_buffer = deque(maxlen=1000)
latency_update_counter = 0
LATENCY_UPDATE_INTERVAL = 10  # Update Redis stats every N reads


# Function to initialize the consumer group
def initialize_consumer_group():
    while True:
        try:
            redis_client.xgroup_create(stream_name, group_name, id='0', mkstream=True)
            print(f"Created consumer group '{group_name}' on stream '{stream_name}'")
            break
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP Consumer Group name already exists" in str(e):
                print(f"Consumer group '{group_name}' already exists on stream '{stream_name}'")
                break
            elif "NOGROUP" in str(e) or "NO such key" in str(e):
                print(f"Waiting for stream '{stream_name}' to be created by the producer...")
                time.sleep(2)
            else:
                raise e


def update_latency_stats():
    """Update Redis with latency statistics from the buffer"""
    global latency_update_counter

    if not latency_buffer:
        return

    latencies = sorted(latency_buffer)
    count = len(latencies)

    # Calculate statistics
    avg_latency = sum(latencies) / count
    min_latency = latencies[0]
    max_latency = latencies[-1]
    p50_latency = latencies[int(count * 0.50)]
    p95_latency = latencies[int(count * 0.95)]
    p99_latency = latencies[int(count * 0.99)]

    # Store in Redis with millisecond precision
    pipeline = redis_client.pipeline()
    pipeline.set("read_latency_avg_ms", f"{avg_latency:.3f}")
    pipeline.set("read_latency_min_ms", f"{min_latency:.3f}")
    pipeline.set("read_latency_max_ms", f"{max_latency:.3f}")
    pipeline.set("read_latency_p50_ms", f"{p50_latency:.3f}")
    pipeline.set("read_latency_p95_ms", f"{p95_latency:.3f}")
    pipeline.set("read_latency_p99_ms", f"{p99_latency:.3f}")
    pipeline.set("read_latency_sample_count", count)
    pipeline.execute()


# Process messages from the stream
def process_messages():
    print(f"Starting consumer {consumer_name} for stream: {stream_name}...")
    initialize_consumer_group()

    # Progress tracking
    messages_processed = 0
    last_report_time = time.time()
    report_interval = 5  # Report every 5 seconds

    while True:
        global latency_update_counter

        try:
            # Measure XREADGROUP latency
            start_time = time.perf_counter()
            messages = redis_client.xreadgroup(
                groupname=group_name,
                consumername=consumer_name,
                streams={stream_name: '>'},
                count=100,  # Read up to 100 messages at once for better throughput
                block=5000  # Block for 5 seconds if no new messages
            )
            end_time = time.perf_counter()

            # Only track latency for non-blocking reads (when messages were available)
            if messages:
                read_latency_ms = (end_time - start_time) * 1000  # Convert to milliseconds
                latency_buffer.append(read_latency_ms)

                # Periodically update Redis with statistics
                latency_update_counter += 1
                if latency_update_counter >= LATENCY_UPDATE_INTERVAL:
                    update_latency_stats()
                    latency_update_counter = 0

        except redis.exceptions.ResponseError as e:
            if "NOGROUP" in str(e):
                print("Consumer group or stream was deleted, reinitializing consumer group...")
                initialize_consumer_group()
                continue
            else:
                raise e

        if not messages:
            review_pending()  # Check for stalled messages if no new messages are available
            continue

        # Use pipeline for batching Redis operations
        pipeline = redis_client.pipeline()
        message_ids_to_ack = []

        for stream, message_entries in messages:
            for message_id, message_data in message_entries:
                try:
                    # Extract and process message data
                    amount = float(message_data.get(b"amount", 0))
                    transaction_id = message_data.get(b"transaction_id", b"").decode("utf-8")
                    backend_id = message_data.get(b"backend_id", b"").decode("utf-8")

                    # Batch increment counters
                    pipeline.incr("processed_count")
                    pipeline.incrbyfloat("total_amount", amount)

                    # Batch send confirmation to the specific backend's response stream
                    response_stream_name = f"{backend_response_prefix}{backend_id}"
                    confirmation_message = {
                        "transaction_id": transaction_id,
                        "status": "confirmed",
                        "processed_amount": amount,
                        "backend_id": backend_id,
                        "timestamp": datetime.now().isoformat()
                    }
                    pipeline.xadd(response_stream_name, confirmation_message)

                    # Collect message IDs for batch acknowledgment
                    message_ids_to_ack.append(message_id)

                except (ValueError, KeyError) as e:
                    print(f"Error processing message ID {message_id}: {e}")

        # Execute all batched operations at once
        if message_ids_to_ack:
            pipeline.execute()
            # Batch acknowledge all messages
            for msg_id in message_ids_to_ack:
                redis_client.xack(stream_name, group_name, msg_id)

            # Update progress counter
            messages_processed += len(message_ids_to_ack)

            # Report progress every N seconds
            current_time = time.time()
            if current_time - last_report_time >= report_interval:
                elapsed = current_time - last_report_time
                rate = messages_processed / elapsed
                print(f"[{consumer_name}] Processed {messages_processed} messages in {elapsed:.1f}s ({rate:.1f} msg/sec)")
                messages_processed = 0
                last_report_time = current_time


# Function to review and claim pending messages if they've been idle too long
def review_pending(batch_size=100):
    print(f"Reviewing pending messages for consumer group '{group_name}'...")

    start_id = "0-0"  # Start from the beginning of the stream
    while True:
        # Attempt to claim messages using XAUTOCLAIM
        response = redis_client.xautoclaim(
            name=stream_name,
            groupname=group_name,
            consumername=consumer_name,
            min_idle_time=idle_threshold_ms,
            start_id=start_id,  # Use start_id instead of start
            count=batch_size
        )

        next_start_id, claimed_messages, deleted_ids = response

        if not claimed_messages:
            print("No more pending messages to claim.")
            break

        for msg_id, msg_data in claimed_messages:
            try:
                # Extract message data
                amount = float(msg_data.get(b"amount", 0))
                transaction_id = msg_data.get(b"transaction_id", b"").decode("utf-8")
                backend_id = msg_data.get(b"backend_id", b"").decode("utf-8")

                # Process the message
                redis_client.incr("processed_count")
                redis_client.incrbyfloat("total_amount", amount)
                redis_client.xack(stream_name, group_name, msg_id)

                # Send confirmation to the specific backend's response stream
                response_stream_name = f"{backend_response_prefix}{backend_id}"
                confirmation_message = {
                    "transaction_id": transaction_id,
                    "status": "confirmed",
                    "processed_amount": amount,
                    "backend_id": backend_id,
                    "timestamp": datetime.now().isoformat(),
                }
                redis_client.xadd(response_stream_name, confirmation_message)

                print(
                    f"Claimed and processed message ID: {msg_id}, Amount: {amount}, "
                    f"Backend ID: {backend_id}, Transaction ID: {transaction_id}"
                )

            except (ValueError, KeyError) as e:
                print(f"Error processing claimed message ID {msg_id}: {e}")
            except Exception as e:
                print(f"Unhandled exception for claimed message ID {msg_id}: {e}")

        # Move to the next batch using the next_start_id
        if next_start_id == "0-0":
            print("Completed iterating over all pending messages.")
            break


if __name__ == "__main__":
    process_messages()