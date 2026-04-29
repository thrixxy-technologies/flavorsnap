#!/bin/bash

# FlavorSnap Deployment Script
# Supports blue-green deployment with automatic rollback

set -e

# Default values
ENVIRONMENT="staging"
TAG="latest"
ZERO_DOWNTIME=true
HEALTH_CHECK_TIMEOUT=300
ROLLBACK_ON_FAILURE=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment|-e)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --tag|-t)
            TAG="$2"
            shift 2
            ;;
        --no-zero-downtime)
            ZERO_DOWNTIME=false
            shift
            ;;
        --health-check-timeout)
            HEALTH_CHECK_TIMEOUT="$2"
            shift 2
            ;;
        --no-rollback)
            ROLLBACK_ON_FAILURE=false
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --environment, -e ENV     Deployment environment (staging|production) [default: staging]"
            echo "  --tag, -t TAG              Docker image tag [default: latest]"
            echo "  --no-zero-downtime         Disable zero-downtime deployment"
            echo "  --health-check-timeout SEC Health check timeout in seconds [default: 300]"
            echo "  --no-rollback              Disable automatic rollback on failure"
            echo "  --help, -h                 Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
    echo "Error: Environment must be 'staging' or 'production'"
    exit 1
fi

echo "🚀 Starting FlavorSnap deployment..."
echo "Environment: $ENVIRONMENT"
echo "Tag: $TAG"
echo "Zero Downtime: $ZERO_DOWNTIME"
echo "Health Check Timeout: ${HEALTH_CHECK_TIMEOUT}s"
echo "Rollback on Failure: $ROLLBACK_ON_FAILURE"

# Set environment-specific variables
if [[ "$ENVIRONMENT" == "production" ]]; then
    COMPOSE_PROFILES="full"
    SERVICE_NAME="flavorsnap-prod"
    NAMESPACE="flavorsnap-prod"
else
    COMPOSE_PROFILES="blue,monitoring"
    SERVICE_NAME="flavorsnap-staging"
    NAMESPACE="flavorsnap-staging"
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "🔍 Checking prerequisites..."

if ! command_exists docker; then
    echo "Error: Docker is not installed"
    exit 1
fi

if ! command_exists docker-compose; then
    echo "Error: Docker Compose is not installed"
    exit 1
fi

if [[ "$ENVIRONMENT" == "production" ]] && ! command_exists kubectl; then
    echo "Error: kubectl is required for production deployment"
    exit 1
fi

# Build and push Docker image
echo "🏗️  Building Docker image..."
docker build -t flavorsnap-api:$TAG ./ml-model-api/

if [[ "$ENVIRONMENT" == "production" ]]; then
    echo "📤 Pushing Docker image to registry..."
    # Add registry push logic here
    # docker push flavorsnap-api:$TAG
fi

# Deploy with Docker Compose for staging
if [[ "$ENVIRONMENT" == "staging" ]]; then
    echo "🐳 Deploying with Docker Compose..."
    
    # Set environment variables
    export DEPLOYMENT_ENV=$ENVIRONMENT
    export DEPLOYMENT_TAG=$TAG
    export DEPLOYMENT_ID="deploy-$(date +%s)"
    
    # Start services
    docker-compose --profile $COMPOSE_PROFILES up -d
    
    # Wait for services to be ready
    echo "⏳ Waiting for services to be ready..."
    sleep 30
    
    # Health checks
    echo "🏥 Running health checks..."
    HEALTH_CHECK_URL="http://localhost:5001/health"
    
    for i in $(seq 1 $((HEALTH_CHECK_TIMEOUT/10))); do
        if curl -f -s "$HEALTH_CHECK_URL" > /dev/null; then
            echo "✅ Health check passed!"
            break
        fi
        
        if [[ $i -eq $((HEALTH_CHECK_TIMEOUT/10)) ]]; then
            echo "❌ Health check failed after ${HEALTH_CHECK_TIMEOUT}s"
            
            if [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then
                echo "🔄 Rolling back..."
                docker-compose --profile $COMPOSE_PROFILES down
            fi
            
            exit 1
        fi
        
        echo "⏳ Health check attempt $i/$((HEALTH_CHECK_TIMEOUT/10))..."
        sleep 10
    done
    
    echo "✅ Staging deployment completed successfully!"
    
else
    # Production deployment with Kubernetes
    echo "☸️  Deploying to Kubernetes..."
    
    # Set kubectl context (ensure you're in the right cluster)
    kubectl config use-context production
    
    # Get current active deployment
    CURRENT_DEPLOYMENT=$(kubectl get service $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.spec.selector.color}' 2>/dev/null || echo "blue")
    
    # Determine target color
    if [[ "$CURRENT_DEPLOYMENT" == "blue" ]]; then
        TARGET_COLOR="green"
    else
        TARGET_COLOR="blue"
    fi
    
    echo "🎯 Deploying to $TARGET_COLOR environment (current: $CURRENT_DEPLOYMENT)"
    
    # Update deployment
    kubectl set image deployment/flavorsnap-$TARGET_COLOR \
        flavorsnap=flavorsnap-api:$TAG \
        -n $NAMESPACE
    
    # Wait for rollout
    echo "⏳ Waiting for rollout to complete..."
    kubectl rollout status deployment/flavorsnap-$TARGET_COLOR -n $NAMESPACE --timeout=${HEALTH_CHECK_TIMEOUT}s
    
    # Run health checks
    echo "🏥 Running health checks on new deployment..."
    
    # Get pod IP
    POD_IP=$(kubectl get pod -l color=$TARGET_COLOR -n $NAMESPACE -o jsonpath='{.items[0].status.podIP}')
    
    for i in {1..10}; do
        if curl -f --max-time 10 "http://$POD_IP:5000/health" > /dev/null; then
            echo "✅ Health check $i passed!"
            sleep 5
        else
            echo "❌ Health check $i failed"
            
            if [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then
                echo "🔄 Rolling back to $CURRENT_DEPLOYMENT..."
                kubectl patch service $SERVICE_NAME -n $NAMESPACE -p '{"spec":{"selector":{"color":"'$CURRENT_DEPLOYMENT'"}}}'
                kubectl scale deployment flavorsnap-$TARGET_COLOR --replicas=0 -n $NAMESPACE
            fi
            
            exit 1
        fi
    done
    
    # Switch traffic
    if [[ "$ZERO_DOWNTIME" == "true" ]]; then
        echo "🔄 Switching traffic to $TARGET_COLOR deployment..."
        kubectl patch service $SERVICE_NAME -n $NAMESPACE -p '{"spec":{"selector":{"color":"'$TARGET_COLOR'"}}}'
        
        # Wait a bit for traffic to switch
        sleep 10
        
        # Final health check through load balancer
        SERVICE_URL=$(kubectl get service $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
        
        if curl -f --max-time 30 "http://$SERVICE_URL/health" > /dev/null; then
            echo "✅ Traffic switch successful!"
        else
            echo "❌ Traffic switch health check failed"
            
            if [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then
                echo "🔄 Rolling back..."
                kubectl patch service $SERVICE_NAME -n $NAMESPACE -p '{"spec":{"selector":{"color":"'$CURRENT_DEPLOYMENT'"}}}'
            fi
            
            exit 1
        fi
    fi
    
    # Scale down old deployment
    echo "📉 Scaling down $CURRENT_DEPLOYMENT deployment..."
    kubectl scale deployment flavorsnap-$CURRENT_DEPLOYMENT --replicas=0 -n $NAMESPACE
    
    echo "✅ Production deployment completed successfully!"
fi

# Show deployment status
echo "📊 Deployment Status:"
if [[ "$ENVIRONMENT" == "staging" ]]; then
    docker-compose ps
else
    kubectl get pods -n $NAMESPACE -l color=$TARGET_COLOR
    kubectl get service $SERVICE_NAME -n $NAMESPACE
fi

echo "🎉 Deployment completed successfully!"
echo "Environment: $ENVIRONMENT"
echo "Tag: $TAG"
echo "Deployment ID: $DEPLOYMENT_ID"
