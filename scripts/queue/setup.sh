#!/bin/bash
echo "Setting up RabbitMQ with Management Plugin..."
kubectl apply -f k8s/queue/
