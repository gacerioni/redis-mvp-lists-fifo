# Multi-purpose Dockerfile for PIX Payment System
# Can run: consumer, monitor, or backend simulator
# Usage: docker run -e MODE=consumer|monitor|simulator ...

FROM python:3.12-slim
LABEL authors="gabriel.cerioni@redis.com"
LABEL description="Redis PIX Payment System - Multi-mode container"

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all necessary Python files
COPY pix_smasher_demo.py .
COPY pix_monitor_tui.py .
COPY stream_latency_demo.py .
COPY utils/ ./utils/

# Set default environment variables
ENV PYTHONUNBUFFERED=1
ENV REDIS_URL=redis://localhost:6379
ENV REDIS_STREAM=pix_payments
ENV GROUP_NAME=pix_consumers
ENV IDLE_THRESHOLD_MS=5000
ENV BACKEND_RESPONSE_PREFIX=backend_bacen_response_
ENV BACKEND_ID=default_backend

# Simulator-specific defaults
ENV NUM_REQUESTS=1000000
ENV BATCH_SIZE=25000

# MODE can be: consumer, monitor, or simulator
ENV MODE=consumer

# Entrypoint script to run the appropriate component
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]

