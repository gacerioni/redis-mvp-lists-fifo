# 🚀 Redis Streams Latency Demo (Gradio UI)

Interactive web UI to measure **end-to-end latency** from writing to Redis Streams to consuming the message.

## Features

- ✅ **Single-click testing** - Send message and measure latency instantly
- 📊 **Live statistics** - Average, P50, P95, P99, Min, Max
- 📈 **Reactive chart** - Visual latency trends over time
- 🗑️ **Clean stream** - Reset test data with one click
- ⚡ **Real-time comparison** - Shows speedup vs AWS SQS (70ms baseline)
- 🎨 **Color-coded results** - Visual feedback on performance

## Quick Start

### Local (Python)
```bash
# Install dependencies
pip install -r requirements.txt

# Run the demo
python3 stream_latency_demo.py

# Access at http://localhost:7860
```

### Docker (Recommended)
```bash
# Using host Redis
docker run -p 7860:7860 \
  -e MODE=latency-demo \
  -e REDIS_URL='redis://host.docker.internal:6379' \
  gacerioni/gabs-pix-smasher:0.0.1

# Access at http://localhost:7860
```

## How It Works

1. **User enters message** (or uses auto-generated)
2. **Click "Send & Measure"**
3. **System:**
   - Records timestamp
   - Sends message to Redis Stream (`latency_test_stream`)
   - Immediately reads it using XREADGROUP
   - Calculates end-to-end latency
4. **UI displays:**
   - Exact latency in milliseconds
   - Comparison to AWS SQS (70ms)
   - Speedup multiplier (e.g., "299x faster!")
   - Statistics from all tests
   - Chart showing latency trends

## Expected Results

- **End-to-end latency**: 1-3ms (typical)
- **AWS SQS baseline**: ~70ms
- **Speedup**: **23-70x faster!** 🚀

## Environment Variables

- `REDIS_URL` - Redis connection (default: `redis://localhost:6379`)
- `LATENCY_TEST_STREAM` - Stream name (default: `latency_test_stream`)
- `LATENCY_TEST_GROUP` - Consumer group (default: `latency_test_group`)
- `SQS_BASELINE_MS` - AWS SQS baseline for comparison (default: `70.0`)

## UI Components

### Input Section
- Message text field
- "Send & Measure" button
- "Clean Stream" button

### Results Display
- Latest test result with timestamps
- End-to-end latency
- Speedup vs AWS SQS
- Color-coded performance indicator

### Statistics Panel
- Average, Median (P50), P95, P99
- Min/Max latencies
- Number of tests run

### Chart
- Line plot showing latency over time
- X-axis: Test number
- Y-axis: Latency (ms)

### History Table
- Last 20 tests
- Test ID, timestamp, latency, speedup, message

## Demo Flow

1. Open http://localhost:7860
2. Enter a message (or use default)
3. Click "Send & Measure Latency"
4. See instant results showing sub-millisecond to low-millisecond latency
5. Run multiple tests to build statistics
6. Watch the chart update in real-time
7. Click "Clean Stream" to reset when needed

## Perfect For

- **Live demos** - Visual, interactive, impressive
- **Benchmarking** - Compare Redis vs SQS performance
- **Proof of concept** - Show real-world latency metrics
- **Customer presentations** - Easy to understand UI

