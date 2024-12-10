#!/bin/bash

# Path to your SSH key
SSH_KEY="/Users/gabriel.cerioni/.ssh/gabs-se-sales-ssh-keypair.pem"

# EC2 IP addresses
EC2_IPS=(
    "54.196.152.24"  # Latency Box A
    "54.144.245.164" # Latency Box B
    "34.234.16.221"  # Latency Box C
    "34.230.254.47"  # Latency Box D
)

# Redis URL (to be provided on the day of execution)
if [ -z "$1" ]; then
    echo "Usage: $0 <REDIS_URL>"
    exit 1
fi
REDIS_URL="$1"

# Path to the docker-compose template
LOCAL_COMPOSE_TEMPLATE="../kubernetes_and_dockerization/docker-compose-example.yml"

# Check if the template exists
if [ ! -f "$LOCAL_COMPOSE_TEMPLATE" ]; then
    echo "Docker-compose template file not found at $LOCAL_COMPOSE_TEMPLATE"
    exit 1
fi

# Read the docker-compose template and replace the placeholder, properly escaping special characters
COMPOSE_CONTENT=$(sed "s|REDIS_URL: .*|REDIS_URL: \"$REDIS_URL\"|" "$LOCAL_COMPOSE_TEMPLATE" | sed 's/"/\\"/g')

# Function to deploy to a single instance
deploy_to_instance() {
    local IP=$1
    echo "Deploying to $IP..."

    # Upload and execute the commands remotely
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "ubuntu@$IP" bash <<EOF
        sudo mkdir -p /PIX_BENCH/
        echo -e "$COMPOSE_CONTENT" | sudo tee /PIX_BENCH/docker-compose.yml > /dev/null

        # Navigate to the deployment directory
        cd /PIX_BENCH/ || exit 1

        # Restart the services
        sudo docker-compose down || true
        sudo docker network prune -f || true
        sudo docker-compose up -d || true
EOF

    if [ $? -ne 0 ]; then
        echo "Deployment failed for $IP. Check the remote instance."
    else
        echo "Deployment successful for $IP."
    fi
}

# Main deployment logic
echo "Starting deployment to EC2 instances..."
for IP in "${EC2_IPS[@]}"; do
    deploy_to_instance "$IP" &
done

# Wait for all background processes to complete
wait

echo "Deployment completed."