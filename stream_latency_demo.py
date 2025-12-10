import os
import time
import redis
import gradio as gr
import numpy as np
import pandas as pd
from datetime import datetime
from collections import deque
from typing import Dict, List, Tuple

# Redis configuration
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
test_stream = os.getenv("LATENCY_TEST_STREAM", "latency_test_stream")
test_group = os.getenv("LATENCY_TEST_GROUP", "latency_test_group")
test_consumer = "latency_demo_consumer"
sqs_baseline_ms = float(os.getenv("SQS_BASELINE_MS", "70.0"))

# Initialize Redis
redis_client = redis.from_url(redis_url)

# Store test results (last 100 tests)
test_history = deque(maxlen=100)

# Auto-repeat state
auto_repeat_active = False


def initialize_consumer_group():
    """Initialize the consumer group for latency testing"""
    try:
        redis_client.xgroup_create(test_stream, test_group, id='0', mkstream=True)
        print(f"Created consumer group '{test_group}' on stream '{test_stream}'")
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" in str(e):
            print(f"Consumer group '{test_group}' already exists")
        else:
            raise e


def send_and_measure_latency(message_content: str) -> Dict:
    """
    Send a message to Redis Stream and measure end-to-end latency using consumer group
    This simulates real-world usage with blocking consumer
    """
    if not message_content.strip():
        message_content = f"Test message {len(test_history) + 1}"

    # 1. Record send time and add message to stream
    send_time_ms = time.perf_counter() * 1000
    message = {
        "content": message_content,
        "timestamp_ms": str(send_time_ms),
        "test_id": str(len(test_history) + 1)
    }

    msg_id = redis_client.xadd(test_stream, message)
    write_complete_ms = time.perf_counter() * 1000

    # 2. Read using consumer group with blocking (real-world pattern)
    # Longer block keeps connection alive and waiting = lower latency!
    # This is how real consumers work - they block for long periods
    read_start_ms = time.perf_counter() * 1000
    messages = redis_client.xreadgroup(
        groupname=test_group,
        consumername=test_consumer,
        streams={test_stream: '>'},
        count=1,
        block=60000  # 60 seconds - keeps connection alive, shows true streaming latency
    )
    read_complete_ms = time.perf_counter() * 1000

    # 3. Acknowledge the message
    if messages and len(messages) > 0:
        stream_name, message_list = messages[0]
        if message_list:
            msg_id_received, msg_data = message_list[0]
            redis_client.xack(test_stream, test_group, msg_id_received)

    # 4. Calculate latencies
    write_latency = write_complete_ms - send_time_ms
    read_latency = read_complete_ms - read_start_ms
    total_latency = write_latency + read_latency

    speedup = sqs_baseline_ms / total_latency if total_latency > 0 else 0

    result = {
        "test_id": len(test_history) + 1,
        "latency_ms": total_latency,
        "write_latency_ms": write_latency,
        "read_latency_ms": read_latency,
        "speedup": speedup,
        "send_time": send_time_ms,
        "receive_time": read_complete_ms,
        "message": message_content,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    }

    test_history.append(result)
    return result


def format_result_display(result: Dict) -> str:
    """Format the latest test result for display"""
    if result["latency_ms"] < 0:
        return "❌ **Error**: No message received (timeout)"

    latency = result["latency_ms"]
    write_latency = result.get("write_latency_ms", 0)
    read_latency = result.get("read_latency_ms", 0)
    speedup = result["speedup"]

    # Color coding based on latency
    if latency < 5:
        emoji = "🚀"
        status = "EXCELLENT"
    elif latency < 20:
        emoji = "⚡"
        status = "GREAT"
    elif latency < 70:
        emoji = "✓"
        status = "GOOD"
    else:
        emoji = "⚠️"
        status = "SLOW"

    output = f"""
## {emoji} Latest Test Result - {status}

**Message:** {result['message']}

**Timestamps:**
- 📤 Sent at: `{result['timestamp']}`
- 📥 Received: `{datetime.fromtimestamp(result['receive_time']/1000).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]}`

---

### ⚡ Total Latency: **{latency:.3f} ms**

**Breakdown:**
- ✍️ **Write (XADD):** {write_latency:.3f} ms
- 📖 **Read (XREADGROUP blocking):** {read_latency:.3f} ms

### 📊 Comparison:
- **AWS SQS Baseline:** {sqs_baseline_ms:.1f} ms
- **Redis Streams:** {latency:.3f} ms
- **🚀 Speedup:** **{speedup:.1f}x FASTER!**

---
"""
    return output


def get_statistics_display() -> str:
    """Generate statistics from test history"""
    if not test_history:
        return "No tests run yet. Click 'Send & Measure' to start!"

    latencies = [t["latency_ms"] for t in test_history if t["latency_ms"] > 0]
    write_latencies = [t.get("write_latency_ms", 0) for t in test_history if t["latency_ms"] > 0]
    read_latencies = [t.get("read_latency_ms", 0) for t in test_history if t["latency_ms"] > 0]

    if not latencies:
        return "No valid test results yet."

    avg_latency = np.mean(latencies)
    avg_write = np.mean(write_latencies)
    avg_read = np.mean(read_latencies)
    min_latency = np.min(latencies)
    max_latency = np.max(latencies)
    p50_latency = np.percentile(latencies, 50)
    p95_latency = np.percentile(latencies, 95)
    p99_latency = np.percentile(latencies, 99)
    avg_speedup = sqs_baseline_ms / avg_latency

    stats = f"""
## 📈 Statistics ({len(latencies)} tests)

### Total Latency (Write + Read)

| Metric | Latency (ms) | vs SQS |
|--------|--------------|--------|
| **Average** | {avg_latency:.3f} | {avg_speedup:.1f}x faster |
| **Median (P50)** | {p50_latency:.3f} | {sqs_baseline_ms/p50_latency:.1f}x faster |
| **P95** | {p95_latency:.3f} | {sqs_baseline_ms/p95_latency:.1f}x faster |
| **P99** | {p99_latency:.3f} | {sqs_baseline_ms/p99_latency:.1f}x faster |
| **Min** | {min_latency:.3f} | {sqs_baseline_ms/min_latency:.1f}x faster |
| **Max** | {max_latency:.3f} | {sqs_baseline_ms/max_latency:.1f}x faster |

### Breakdown (Average)
- ✍️ **Write (XADD):** {avg_write:.3f} ms
- 📖 **Read (XREADGROUP blocking):** {avg_read:.3f} ms

**AWS SQS Baseline:** {sqs_baseline_ms:.1f} ms
"""
    return stats


def get_history_table() -> List[List]:
    """Get test history as a table"""
    if not test_history:
        return []
    
    # Return last 20 tests in reverse order (newest first)
    recent_tests = list(test_history)[-20:][::-1]
    
    table_data = []
    for test in recent_tests:
        if test["latency_ms"] > 0:
            table_data.append([
                f"#{test['test_id']}",
                test['timestamp'],
                f"{test['latency_ms']:.3f} ms",
                f"{test['speedup']:.1f}x",
                test['message'][:30] + "..." if len(test['message']) > 30 else test['message']
            ])
    
    return table_data


def get_latency_chart_data():
    """Get data for latency chart as pandas DataFrame"""
    if not test_history:
        return None

    valid_tests = [t for t in test_history if t["latency_ms"] > 0]
    if not valid_tests:
        return None

    df = pd.DataFrame({
        "Test ID": [t["test_id"] for t in valid_tests],
        "Latency (ms)": [t["latency_ms"] for t in valid_tests]
    })

    return df


def clean_stream() -> str:
    """Delete the test stream and recreate consumer group"""
    try:
        # Delete the stream
        redis_client.delete(test_stream)
        
        # Clear history
        test_history.clear()
        
        # Recreate consumer group
        initialize_consumer_group()
        
        return "✅ Stream cleaned successfully! All test data removed."
    except Exception as e:
        return f"❌ Error cleaning stream: {str(e)}"


def run_single_test(message_content: str):
    """Run a single latency test"""
    result = send_and_measure_latency(message_content)
    result_display = format_result_display(result)
    stats_display = get_statistics_display()
    history_table = get_history_table()

    return result_display, stats_display, history_table


def clean_stream_action():
    """Clean stream and update UI"""
    message = clean_stream()
    stats_display = get_statistics_display()
    history_table = get_history_table()
    return message, stats_display, history_table


# Initialize consumer group on startup
initialize_consumer_group()

# Create Gradio interface
with gr.Blocks(title="Redis Streams Latency Demo", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 🚀 Redis Streams vs AWS SQS - End-to-End Latency Demo
    
    This demo measures the **complete journey**: sending a message to Redis Streams and immediately consuming it.
    Compare Redis Streams performance against AWS SQS's ~70ms baseline latency.
    """)
    
    with gr.Row():
        with gr.Column(scale=2):
            message_input = gr.Textbox(
                label="Message Content",
                placeholder="Enter message (or leave empty for auto-generated)",
                value="Hello Redis Streams!"
            )
            
            with gr.Row():
                send_btn = gr.Button("🚀 Send & Measure Latency", variant="primary", scale=2)
                clean_btn = gr.Button("🗑️ Clean Stream", variant="secondary", scale=1)
        
        with gr.Column(scale=1):
            gr.Markdown("### Quick Stats")
            stats_box = gr.Markdown(get_statistics_display())
    
    with gr.Row():
        result_display = gr.Markdown("Click 'Send & Measure' to start testing!")

    with gr.Row():
        history_table = gr.Dataframe(
            headers=["Test", "Timestamp", "Latency", "Speedup", "Message"],
            datatype=["str", "str", "str", "str", "str"],
            label="Recent Tests (Last 20)",
            wrap=True
        )

    # Event handlers
    send_btn.click(
        fn=run_single_test,
        inputs=[message_input],
        outputs=[result_display, stats_box, history_table]
    )

    clean_btn.click(
        fn=clean_stream_action,
        inputs=[],
        outputs=[result_display, stats_box, history_table]
    )

if __name__ == "__main__":
    print(f"Starting Redis Streams Latency Demo")
    print(f"Redis URL: {redis_url}")
    print(f"Test Stream: {test_stream}")
    print(f"SQS Baseline: {sqs_baseline_ms} ms")
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)

