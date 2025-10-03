# Redis PIX Payment Processing System

A Redis-based PIX (instant payment system) processing demonstration showcasing high-throughput financial transaction handling with real-time monitoring capabilities.

## Overview

This system demonstrates two architectural patterns for handling PIX payments:

1. **Stream-based processing** (`pix_smasher_demo.py`) - Production-ready Redis Streams with consumer groups
2. **List-based FIFO processing** (`alternative_demos/pix_mvp.py`) - Simple Redis lists with BRPOP

## Quick Start

### Prerequisites

- Python 3.8+
- Redis server running on localhost:6379 (or configure `REDIS_URL`)
- Required dependencies: `pip install redis rich numpy`

### Running the System

1. **Start the PIX payment consumer:**
   ```bash
   python3 pix_smasher_demo.py
   ```

2. **Start the real-time monitoring TUI:**
   ```bash
   python3 pix_monitor_tui.py
   ```

3. **Send test PIX payments:**
   ```bash
   # Single payment
   python3 utils/util_pix_backend_simulator.py
   
   # High-volume batch testing
   REDIS_URL="redis://localhost:6379" NUM_REQUESTS=4000 BATCH_SIZE=250 python3 utils/util_mult_pix_backend_simulator.py
   ```

## PIX Monitoring TUI

The Terminal User Interface (`pix_monitor_tui.py`) provides comprehensive real-time monitoring of the PIX payment system:

### Features

- **Stream Monitoring**: Real-time view of the `pix_payments` stream length, entry IDs, and metadata
- **Consumer Group Tracking**: Detailed monitoring of all consumer groups including:
  - Pending messages per group
  - Active consumers and their idle times
  - Group lag and processing statistics
- **Backend Response Streams**: Dynamic discovery and monitoring of all `backend_bacen_response_*` streams
- **Processing Statistics**: 
  - Total messages processed (`processed_count`)
  - Total amount in BRL (`total_amount`)
  - Processing rate (messages/second)
  - System uptime and Redis metrics

### TUI Layout

```
┌─────────────────────────────────────────────────────────────┐
│                PIX Payment System Monitor                   │
│           Redis: redis://localhost:6379 | Stream: pix_payments            │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────┬─────────────────────────────────────┐
│   PIX Processor Status  │      Consumer Groups Detail        │
│  ┌─────────────────────┐│  ┌─────────────────────────────────┐│
│  │ Messages Processed  ││  │ Group     Pending  Consumers    ││
│  │ Total Amount (BRL)  ││  │ pix_consumers  0       2        ││
│  │ Processing Rate     ││  │   └─ consumer_host_1234  0      ││
│  │ Uptime             ││  │   └─ consumer_host_5678  0      ││
│  │ Pending Messages    ││  └─────────────────────────────────┘│
│  │ Active Consumers    │├─────────────────────────────────────┤
│  │ Group Lag          ││      Backend Response Streams       │
│  └─────────────────────┘│  ┌─────────────────────────────────┐│
├─────────────────────────┤  │ Backend   Messages  Last ID     ││
│     Stream Info         │  │ 1         245       1734-123    ││
│  ┌─────────────────────┐│  │ 2         198       1734-456    ││
│  │ Stream Length       ││  │ 3         312       1734-789    ││
│  │ Last Generated ID   ││  └─────────────────────────────────┘│
│  │ First Entry ID      ││                                     │
│  │ Last Entry ID       ││                                     │
│  └─────────────────────┘│                                     │
└─────────────────────────┴─────────────────────────────────────┘
```

### Environment Variables

The TUI respects the same environment variables as the PIX system:

- `REDIS_URL`: Redis connection string (default: `redis://localhost:6379`)
- `REDIS_STREAM`: Main stream name (default: `pix_payments`)
- `GROUP_NAME`: Consumer group name (default: `pix_consumers`)
- `BACKEND_RESPONSE_PREFIX`: Backend response stream prefix (default: `backend_bacen_response_`)

### Usage Tips

- Press `Ctrl+C` to exit the monitoring interface
- The interface updates every 0.5 seconds with live data
- Error states are displayed when Redis is unavailable or streams don't exist
- Consumer idle times help identify stalled or inactive consumers

## Architecture Details

### Message Flow

1. **Injection**: Backend simulators inject PIX payment messages into the `pix_payments` stream
2. **Processing**: Consumer processes messages using consumer groups with XAUTOCLAIM for fault tolerance
3. **Confirmation**: Processed messages trigger confirmations sent to backend-specific response streams
4. **Monitoring**: TUI provides real-time visibility into all system components

### Redis Patterns Used

- **Redis Streams**: High-throughput message queuing with consumer groups
- **Consumer Groups**: Load balancing and fault tolerance across multiple consumers
- **XAUTOCLAIM**: Automatic reclaim of stalled messages from failed consumers
- **Stream-per-Backend**: Isolated response channels for each backend system
- **Atomic Counters**: `INCR` and `INCRBYFLOAT` for processing statistics

### Key Benefits

- **High Throughput**: Handles thousands of messages per second
- **Fault Tolerance**: Automatic message recovery via consumer groups
- **Scalability**: Horizontal scaling through multiple consumer instances
- **Observability**: Comprehensive monitoring and real-time metrics
- **Isolation**: Backend-specific response streams prevent cross-contamination

## Testing

Run the complete system test:

```bash
# Terminal 1: Start consumer
python3 pix_smasher_demo.py

# Terminal 2: Start monitoring
python3 pix_monitor_tui.py

# Terminal 3: Generate test load
REDIS_URL="redis://localhost:6379" NUM_REQUESTS=1000 BATCH_SIZE=100 python3 utils/util_mult_pix_backend_simulator.py
```

## Dependencies

- `redis==5.2.0`: Redis client library
- `rich`: Terminal UI framework for the monitoring interface
- `numpy==2.1.3`: Numerical operations

## Alternative Implementations

- `alternative_demos/pix_mvp.py`: Simple list-based FIFO processing
- `alternative_demos/pix_streams_mvp.py`: Basic stream consumer without backend response handling
