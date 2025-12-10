#!/bin/bash
set -e

echo "=========================================="
echo "PIX Payment System - Starting in ${MODE} mode"
echo "Redis URL: ${REDIS_URL}"
echo "=========================================="

case "${MODE}" in
  consumer)
    echo "Starting PIX Consumer (pix_smasher_demo.py)..."
    exec python3 pix_smasher_demo.py
    ;;

  monitor)
    echo "Starting PIX Monitor TUI (pix_monitor_tui.py)..."
    exec python3 pix_monitor_tui.py
    ;;

  simulator)
    echo "Starting Backend Simulator (util_mult_pix_backend_simulator.py)..."
    echo "NUM_REQUESTS: ${NUM_REQUESTS}"
    echo "BATCH_SIZE: ${BATCH_SIZE}"
    exec python3 utils/util_mult_pix_backend_simulator.py
    ;;

  latency-demo)
    echo "Starting Latency Demo UI (stream_latency_demo.py)..."
    echo "Access the UI at http://localhost:7860"
    exec python3 stream_latency_demo.py
    ;;

  *)
    echo "ERROR: Invalid MODE '${MODE}'"
    echo "Valid modes: consumer, monitor, simulator, latency-demo"
    exit 1
    ;;
esac

