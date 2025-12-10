# Docker Setup

## Quick Start

```bash
# Start the demo (Redis + Consumer + Monitor + Simulator)
docker-compose up

# View monitor in another terminal
docker attach pix-monitor
```

## Files

- **Dockerfile** - Multi-mode image (consumer/monitor/simulator)
- **docker-entrypoint.sh** - Routes to correct Python script based on MODE env var
- **docker-compose.yml** - Demo setup with all components

## Image

```bash
# Build multi-arch
docker buildx build --platform linux/amd64,linux/arm64 \
  -f Dockerfile \
  -t gacerioni/gabs-pix-smasher:0.0.1 \
  --push .
```

## Run Modes

```bash
# Consumer (reader)
docker run -e MODE=consumer -e REDIS_URL=redis://redis:6379 gacerioni/gabs-pix-smasher:0.0.1

# Monitor (TUI)
docker run -it -e MODE=monitor -e REDIS_URL=redis://redis:6379 gacerioni/gabs-pix-smasher:0.0.1

# Simulator (publisher)
docker run -e MODE=simulator -e REDIS_URL=redis://redis:6379 gacerioni/gabs-pix-smasher:0.0.1

# Latency Demo (Gradio UI)
docker run -p 7860:7860 -e MODE=latency-demo -e REDIS_URL=redis://redis:6379 gacerioni/gabs-pix-smasher:0.0.1
# Access at http://localhost:7860
```

