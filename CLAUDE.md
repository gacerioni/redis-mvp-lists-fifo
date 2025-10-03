# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Redis-based PIX (instant payment system) processing demonstration that showcases two architectural patterns for handling high-throughput financial transactions:

1. **List-based FIFO processing** (`alternative_demos/pix_mvp.py`) - Uses Redis lists with BRPOP for simple message queuing
2. **Stream-based processing** (`pix_smasher_demo.py`) - Uses Redis Streams with consumer groups for more robust message processing

## Architecture

### Core Components

- **Main Consumer (`pix_smasher_demo.py`)**: Redis Streams consumer with XAUTOCLAIM for processing PIX payments and sending confirmations to backend-specific response streams
- **Backend Simulators**: Generate PIX payment messages and wait for confirmations
  - `utils/util_pix_backend_simulator.py` - Single backend simulator
  - `utils/util_mult_pix_backend_simulator.py` - Multi-threaded batch message injector
- **Alternative Implementations**: 
  - `alternative_demos/pix_mvp.py` - List-based consumer
  - `alternative_demos/pix_streams_mvp.py` - Basic stream consumer without backend response handling

### Message Flow

1. Backend simulators inject PIX payment messages into the `pix_payments` stream
2. Consumer processes messages using consumer groups with automatic failover via XAUTOCLAIM
3. For each processed message, a confirmation is sent to a backend-specific response stream (`backend_bacen_response_{backend_id}`)
4. Backend simulators listen for confirmations on their dedicated response streams

### Key Redis Patterns

- **Consumer Groups**: Ensures load balancing and fault tolerance across multiple consumers
- **XAUTOCLAIM**: Automatically reclaims stalled messages from failed consumers
- **Stream-per-Backend**: Each backend gets its own response stream for confirmations
- **Pipeline Operations**: Batch message injection for high throughput

## Development Commands

Run the main consumer:
```bash
python3 pix_smasher_demo.py
```

Run backend simulator (single message):
```bash
python3 utils/util_pix_backend_simulator.py
```

Run high-volume message injection:
```bash
REDIS_URL="redis://localhost:6379" NUM_REQUESTS=4000 BATCH_SIZE=250 python3 utils/util_mult_pix_backend_simulator.py
```

## Environment Variables

- `REDIS_URL`: Redis connection string (default: `redis://localhost:6379`)
- `REDIS_STREAM`: Main stream name (default: `pix_payments`)
- `GROUP_NAME`: Consumer group name (default: `pix_consumers`)
- `BACKEND_ID`: Backend identifier for response streams
- `BACKEND_RESPONSE_PREFIX`: Prefix for backend response streams (default: `backend_bacen_response_`)
- `IDLE_THRESHOLD_MS`: Idle time before claiming stalled messages (default: 5000ms)
- `NUM_REQUESTS`: Number of messages to inject in batch mode
- `BATCH_SIZE`: Batch size for message injection
- `NUM_THREADS`: Number of parallel threads for injection

## Dependencies

- `redis==5.2.0`: Redis client library
- `numpy==2.1.3`: Numerical operations

## Docker Deployment

The project includes Kubernetes manifests in `kubernetes_and_dockerization/redis-fast-pix/` for deploying the Redis PIX processing system with Helm charts.