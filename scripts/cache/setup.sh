#!/bin/bash
echo "Setting up Redis Cluster for Caching..."
kubectl apply -f k8s/cache/
