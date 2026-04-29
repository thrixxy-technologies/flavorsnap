#!/bin/bash

# Container Image Security Scanning Script
# Uses Trivy for vulnerability scanning

IMAGE_NAME=$1

if [ -z "$IMAGE_NAME" ]; then
    echo "Usage: $0 <image-name>"
    exit 1
fi

echo "Starting security scan for image: $IMAGE_NAME"

# Check if trivy is installed
if ! command -v trivy &> /dev/null; then
    echo "Trivy not found. Installing..."
    curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
fi

# Run vulnerability scan
trivy image --severity HIGH,CRITICAL --exit-code 1 "$IMAGE_NAME"

if [ $? -eq 0 ]; then
    echo "Security scan passed!"
else
    echo "Security scan failed! High or Critical vulnerabilities found."
    exit 1
fi

# Run configuration scan
trivy config .

# Compliance checking
trivy image --compliance docker-bench "$IMAGE_NAME"
