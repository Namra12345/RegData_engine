#!/bin/bash

# Get the private IP of this EC2 instance automatically
INTERNAL_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)

# Get the public IP of this EC2 instance automatically
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

echo "Private IP: $INTERNAL_IP"
echo "Public IP:  $PUBLIC_IP"

# Replace the placeholders in docker-compose.yml with real IPs
sed -i "s/INTERNAL_IP/$INTERNAL_IP/g" docker-compose.yml
sed -i "s/PUBLIC_IP/$PUBLIC_IP/g" docker-compose.yml

# Create data folder and set permissions for Kafka
mkdir -p ./data
sudo chown -R 1000:1000 ./data

# Start Kafka
docker compose up -d

echo ""
echo "Kafka is starting... wait 10 seconds then run:"
echo "docker logs kafka --tail 30"
