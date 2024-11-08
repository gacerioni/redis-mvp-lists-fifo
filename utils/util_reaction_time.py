import os
import redis
import time
from multiprocessing import Process, Queue
import numpy as np

# Redis configuration from environment
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
source_queue = os.getenv("REDIS_LIST", "source_list")
num_measurements = 100  # Number of reaction times to measure

# Initialize Redis client with connection pooling
pool = redis.ConnectionPool.from_url(redis_url)
redis_client = redis.Redis(connection_pool=pool)

def producer(inject_queue):
    print("Starting producer...")
    for _ in range(num_measurements):
        # Sleep briefly to allow consumer to be ready
        time.sleep(1)

        # Record start time, inject message
        start_time = time.time()
        redis_client.lpush(source_queue, "Test message")

        # Send the start time to consumer
        inject_queue.put(start_time)
        print(f"Injected message at {start_time:.2f}")

def consumer(inject_queue, reaction_times):
    print("Starting consumer...")
    for _ in range(num_measurements):
        # Wait to receive the start time from producer
        start_time = inject_queue.get()

        # Blocking on BRPOP to detect message
        redis_client.brpop(source_queue, timeout=0)

        # Calculate reaction time and store it in milliseconds
        reaction_time_ms = (time.time() - start_time) * 1000  # Convert to milliseconds
        reaction_times.put(reaction_time_ms)
        print(f"Reaction time: {reaction_time_ms:.2f} ms")

def main():
    # Queues to communicate between producer and consumer
    inject_queue = Queue()
    reaction_times = Queue()

    # Start producer and consumer processes
    producer_process = Process(target=producer, args=(inject_queue,))
    consumer_process = Process(target=consumer, args=(inject_queue, reaction_times))
    producer_process.start()
    consumer_process.start()

    # Wait for both to finish
    producer_process.join()
    consumer_process.join()

    # Collect reaction times from the queue
    times = []
    while not reaction_times.empty():
        times.append(reaction_times.get())

    # Use percentiles to filter out outliers (10th to 90th percentile)
    filtered_times = [t for t in times if np.percentile(times, 10) <= t <= np.percentile(times, 90)]

    # Calculate and display statistics
    avg_reaction_time = sum(filtered_times) / len(filtered_times)
    print(f"\nAverage Reaction Time (filtered) over {len(filtered_times)} measurements: {avg_reaction_time:.2f} ms")

if __name__ == "__main__":
    main()