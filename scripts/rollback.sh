#!/bin/bash

# FlavorSnap Rollback Script
# Supports rolling back to previous deployment

set -e

# Default values
ENVIRONMENT="staging"
DEPLOYMENT_ID=""
REASON="Manual rollback"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment|-e)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --deployment-id|-d)
            DEPLOYMENT_ID="$2"
            shift 2
            ;;
        --reason|-r)
            REASON="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --environment, -e ENV     Deployment environment (staging|production) [default: staging]"
            echo "  --deployment-id, -d ID     Specific deployment ID to rollback (optional for production)"
            echo "  --reason, -r REASON        Rollback reason [default: 'Manual rollback']"
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

echo "🔄 Starting FlavorSnap rollback..."
echo "Environment: $ENVIRONMENT"
echo "Deployment ID: ${DEPLOYMENT_ID:-'latest'}"
echo "Reason: $REASON"

# Set environment-specific variables
if [[ "$ENVIRONMENT" == "production" ]]; then
    NAMESPACE="flavorsnap-prod"
    SERVICE_NAME="flavorsnap-prod"
else
    NAMESPACE="flavorsnap-staging"
    SERVICE_NAME="flavorsnap-staging"
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "🔍 Checking prerequisites..."

if [[ "$ENVIRONMENT" == "production" ]] && ! command_exists kubectl; then
    echo "Error: kubectl is required for production rollback"
    exit 1
fi

# Rollback for staging (Docker Compose)
if [[ "$ENVIRONMENT" == "staging" ]]; then
    echo "🐳 Rolling back Docker Compose deployment..."
    
    # Stop current services
    echo "⏹️  Stopping current services..."
    docker-compose --profile blue,monitoring down
    
    # Restart with previous image (you would need to track this)
    echo "🔄 Restarting with previous configuration..."
    docker-compose --profile blue,monitoring up -d
    
    # Wait for services to be ready
    echo "⏳ Waiting for services to be ready..."
    sleep 30
    
    # Health checks
    echo "🏥 Running health checks..."
    HEALTH_CHECK_URL="http://localhost:5001/health"
    
    for i in {1..30}; do
        if curl -f -s "$HEALTH_CHECK_URL" > /dev/null; then
            echo "✅ Rollback health check passed!"
            break
        fi
        
        if [[ $i -eq 30 ]]; then
            echo "❌ Rollback health check failed"
            exit 1
        fi
        
        echo "⏳ Health check attempt $i/30..."
        sleep 10
    done
    
    echo "✅ Staging rollback completed successfully!"
    
else
    # Production rollback with Kubernetes
    echo "☸️  Rolling back Kubernetes deployment..."
    
    # Get current active deployment
    CURRENT_DEPLOYMENT=$(kubectl get service $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.spec.selector.color}')
    
    # Determine rollback target
    if [[ "$CURRENT_DEPLOYMENT" == "blue" ]]; then
        ROLLBACK_COLOR="green"
    else
        ROLLBACK_COLOR="blue"
    fi
    
    echo "🎯 Rolling back to $ROLLBACK_COLOR deployment (current: $CURRENT_DEPLOYMENT)"
    
    # Scale up rollback deployment
    echo "📈 Scaling up $ROLLBACK_COLOR deployment..."
    kubectl scale deployment flavorsnap-$ROLLBACK_COLOR --replicas=3 -n $NAMESPACE
    
    # Wait for rollout
    echo "⏳ Waiting for rollout to complete..."
    kubectl rollout status deployment/flavorsnap-$ROLLBACK_COLOR -n $NAMESPACE --timeout=300s
    
    # Switch traffic
    echo "🔄 Switching traffic to $ROLLBACK_COLOR deployment..."
    kubectl patch service $SERVICE_NAME -n $NAMESPACE -p '{"spec":{"selector":{"color":"'$ROLLBACK_COLOR'"}}}'
    
    # Wait for traffic to switch
    sleep 10
    
    # Health checks
    echo "🏥 Running health checks on rollback deployment..."
    SERVICE_URL=$(kubectl get service $SERVICE_NAME -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    
    for i in {1..10}; do
        if curl -f --max-time 30 "http://$SERVICE_URL/health" > /dev/null; then
            echo "✅ Rollback health check $i passed!"
            sleep 5
        else
            echo "❌ Rollback health check $i failed"
            exit 1
        fi
    done
    
    # Scale down failed deployment
    echo "📉 Scaling down $CURRENT_DEPLOYMENT deployment..."
    kubectl scale deployment flavorsnap-$CURRENT_DEPLOYMENT --replicas=0 -n $NAMESPACE
    
    echo "✅ Production rollback completed successfully!"
fi

# Show rollback status
echo "📊 Rollback Status:"
if [[ "$ENVIRONMENT" == "staging" ]]; then
    docker-compose ps
else
    kubectl get pods -n $NAMESPACE -l color=$ROLLBACK_COLOR
    kubectl get service $SERVICE_NAME -n $NAMESPACE
fi

echo "🎉 Rollback completed successfully!"
echo "Environment: $ENVIRONMENT"
echo "Rollback to: $ROLLBACK_COLOR"
echo "Reason: $REASON"
