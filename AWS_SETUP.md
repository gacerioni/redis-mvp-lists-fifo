# AWS Ubuntu Setup Guide

## 🚀 Quick Start on AWS Ubuntu

### 1. Setup Redis Cloud
- Go to https://redis.com/try-free/
- Create a free database (30MB free tier)
- Note your connection string: `redis://default:password@host:port`

### 2. Launch EC2 Instance
- **AMI**: Ubuntu 22.04 LTS
- **Instance Type**: t3.medium or larger (2 vCPU, 4GB RAM minimum)
- **Security Group**: Open port 7860 (Gradio UI)
- **Storage**: 20GB minimum

### 3. SSH into Instance
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

### 4. Install Docker & Docker Compose
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker ubuntu

# Log out and back in, or run:
newgrp docker

# Install Docker Compose
sudo apt install docker-compose -y

# Verify installation
docker --version
docker-compose --version
```

### 5. Clone Your Repo (or create files)
```bash
# If you have a repo:
git clone <your-repo-url>
cd <repo-directory>

# Or create files manually:
nano docker-compose.yml
# Paste the docker-compose.yml content
```

### 6. Configure Redis Cloud Connection
```bash
# Create .env file with your Redis Cloud credentials
nano .env
```

Add this line (replace with your Redis Cloud connection string):
```
REDIS_URL=redis://default:your-password@your-redis-cloud-host:12345
```

**Example:**
```
REDIS_URL=redis://default:abc123xyz@redis-12345.c1.us-east-1-2.ec2.cloud.redislabs.com:12345
```

### 7. Start All Services
```bash
docker-compose up -d
```

This will start:
- ✅ PIX Consumer (processing messages)
- ✅ PIX Monitor (TUI)
- ✅ Latency Demo UI (port 7860)

All connecting to your **Redis Cloud** instance!

### 8. Access Services

**Latency Demo UI:**
```
http://your-ec2-public-ip:7860
```

**View PIX Monitor (TUI):**
```bash
docker attach pix-monitor
# Press Ctrl+P, Ctrl+Q to detach without stopping
```

**View Logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f pix-consumer
docker-compose logs -f latency-demo
```

### 9. Send 1M+ Messages (Later)

**Option 1: Run simulator in Docker**
```bash
docker run --rm \
  -e MODE=simulator \
  -e REDIS_URL="redis://default:your-password@your-redis-cloud-host:12345" \
  -e REDIS_STREAM=pix_payments \
  -e BACKEND_ID=bank_001 \
  -e NUM_REQUESTS=1000000 \
  -e BATCH_SIZE=25000 \
  gacerioni/gabs-pix-smasher:0.0.2
```

**Option 2: Run Python script directly**
```bash
# Install Python dependencies
pip3 install redis numpy

# Run the multi-threaded simulator (use your Redis Cloud URL)
REDIS_URL="redis://default:your-password@your-redis-cloud-host:12345" \
NUM_REQUESTS=1000000 \
BATCH_SIZE=25000 \
NUM_THREADS=4 \
python3 utils/util_mult_pix_backend_simulator.py
```

### 10. Useful Commands

**Stop all services:**
```bash
docker-compose down
```

**Restart a service:**
```bash
docker-compose restart pix-consumer
```

**View running containers:**
```bash
docker ps
```

**Test Redis Cloud connection:**
```bash
# Install redis-cli
sudo apt install redis-tools -y

# Test connection (use your Redis Cloud URL)
redis-cli -u "redis://default:your-password@your-redis-cloud-host:12345" PING
# Should return: PONG
```

**Clean Redis data:**
```bash
redis-cli -u "redis://default:your-password@your-redis-cloud-host:12345" FLUSHALL
```

**Rebuild and restart (after code changes):**
```bash
docker-compose pull  # Pull latest images
docker-compose up -d --force-recreate
```

### 11. Security Group Settings (AWS Console)

**Inbound Rules:**
- Port 22 (SSH) - Your IP only
- Port 7860 (Gradio) - 0.0.0.0/0 (or your IP for demo)

**Note:** No need to open port 6379 - using Redis Cloud!

## 📊 What You'll See

1. **Latency Demo UI** (http://your-ip:7860)
   - Send single messages
   - See sub-millisecond latency
   - Compare to AWS SQS (70ms)

2. **PIX Monitor** (TUI)
   - Real-time message processing
   - Throughput metrics
   - Consumer group status

3. **PIX Consumer** (background)
   - Processes messages from stream
   - Sends confirmations to backend response streams

## 🎯 Demo Flow

1. Open Latency Demo UI in browser
2. Click "Send & Measure Latency" a few times
3. See ~1-2ms latency (vs 70ms SQS)
4. Later: Send 1M messages using simulator
5. Watch PIX Monitor TUI show real-time processing
6. Check throughput and latency stats

## 🔧 Troubleshooting

**Services not starting:**
```bash
docker-compose logs
```

**Can't access UI:**
- Check security group allows port 7860
- Check service is running: `docker ps`

**Redis connection issues:**
```bash
docker exec -it redis-pix redis-cli PING
# Should return: PONG
```

