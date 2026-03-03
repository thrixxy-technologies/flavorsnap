#!/bin/bash

echo "Setting up FlavorSnap Monitoring System..."

# Create monitoring directories
mkdir -p monitoring/grafana/provisioning/datasources
mkdir -p monitoring/grafana/provisioning/dashboards
mkdir -p monitoring/grafana/dashboards

# Start monitoring stack
echo "Starting monitoring stack..."
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

echo "Waiting for services to start..."
sleep 30

echo "Monitoring setup complete!"
echo "Access points:"
echo "- Prometheus: http://localhost:9090"
echo "- Grafana: http://localhost:3001 (admin/admin123)"
echo "- AlertManager: http://localhost:9093"
echo ""
echo "Next steps:"
echo "1. Import the FlavorSnap dashboard in Grafana"
echo "2. Configure alert channels in AlertManager"
echo "3. Update alert rules as needed"
