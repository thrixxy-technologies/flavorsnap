#!/bin/bash
echo "Initializing Istio Service Mesh..."
istioctl install --set profile=demo -y
kubectl label namespace default istio-injection=enabled
kubectl apply -f k8s/istio/
