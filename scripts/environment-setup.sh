#!/bin/bash

# FlavorSnap Environment Setup Script
# Sets up the deployment environment with all necessary configurations

set -e

# Default values
ENVIRONMENT="staging"
SKIP_DOCKER=false
SKIP_K8S=false
CREATE_SECRETS=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment|-e)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        --skip-k8s)
            SKIP_K8S=true
            shift
            ;;
        --no-secrets)
            CREATE_SECRETS=false
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --environment, -e ENV     Environment to setup (staging|production) [default: staging]"
            echo "  --skip-docker              Skip Docker setup"
            echo "  --skip-k8s                 Skip Kubernetes setup"
            echo "  --no-secrets               Skip secrets creation"
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

echo "🔧 Setting up FlavorSnap environment..."
echo "Environment: $ENVIRONMENT"
echo "Skip Docker: $SKIP_DOCKER"
echo "Skip Kubernetes: $SKIP_K8S"
echo "Create Secrets: $CREATE_SECRETS"

# Set environment-specific variables
if [[ "$ENVIRONMENT" == "production" ]]; then
    NAMESPACE="flavorsnap-prod"
    DOCKER_REGISTRY="ghcr.io"
else
    NAMESPACE="flavorsnap-staging"
    DOCKER_REGISTRY="localhost:5000"
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

if [[ "$ENVIRONMENT" == "production" && "$SKIP_K8S" == false ]] && ! command_exists kubectl; then
    echo "Error: kubectl is required for production environment"
    exit 1
fi

# Create environment file
echo "📝 Creating environment configuration..."
cat > .env.$ENVIRONMENT << EOF
# FlavorSnap $ENVIRONMENT Environment Configuration
COMPOSE_PROJECT_NAME=flavorsnap-$ENVIRONMENT
DEPLOYMENT_ENVIRONMENT=$ENVIRONMENT

# Database Configuration
POSTGRES_PASSWORD=$(openssl rand -base64 32)
DATABASE_URL=postgresql://flavorsnap:\${POSTGRES_PASSWORD}@postgres:5432/flavorsnap

# Redis Configuration
REDIS_PASSWORD=$(openssl rand -base64 24)
REDIS_URL=redis://:\${REDIS_PASSWORD}@redis:6379/0

# Application Configuration
FLASK_ENV=production
SECRET_KEY=$(openssl rand -base64 64)
APP_HOST=0.0.0.0
APP_PORT=5000

# Deployment Configuration
DEPLOYMENT_IMAGE_NAME=flavorsnap-api
DEPLOYMENT_IMAGE_TAG=latest
DEPLOYMENT_ZERO_DOWNTIME=true
DEPLOYMENT_HEALTH_CHECK_INTERVAL=30
DEPLOYMENT_HEALTH_CHECK_TIMEOUT=10
DEPLOYMENT_HEALTH_CHECK_RETRIES=3
DEPLOYMENT_ROLLBACK_THRESHOLD=0.5

# Monitoring Configuration
GRAFANA_USER=admin
GRAFANA_PASSWORD=$(openssl rand -base64 16)
METRICS_ENDPOINT=https://your-metrics-endpoint.com/api/metrics
SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK

# Docker Registry
DOCKER_REGISTRY=$DOCKER_REGISTRY
EOF

echo "✅ Environment file created: .env.$ENVIRONMENT"

# Create Kubernetes namespace and resources
if [[ "$ENVIRONMENT" == "production" && "$SKIP_K8S" == false ]]; then
    echo "☸️  Setting up Kubernetes environment..."
    
    # Create namespace
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # Create secrets
    if [[ "$CREATE_SECRETS" == true ]]; then
        echo "🔐 Creating Kubernetes secrets..."
        
        # Database secret
        kubectl create secret generic postgres-secret \
            --from-literal=postgres-password=$(openssl rand -base64 32) \
            --from-literal=postgres-user=flavorsnap \
            --from-literal=postgres-db=flavorsnap \
            -n $NAMESPACE \
            --dry-run=client -o yaml | kubectl apply -f -
        
        # Redis secret
        kubectl create secret generic redis-secret \
            --from-literal=redis-password=$(openssl rand -base64 24) \
            -n $NAMESPACE \
            --dry-run=client -o yaml | kubectl apply -f -
        
        # Application secret
        kubectl create secret generic app-secret \
            --from-literal=secret-key=$(openssl rand -base64 64) \
            --from-literal=flask-env=production \
            -n $NAMESPACE \
            --dry-run=client -o yaml | kubectl apply -f -
        
        # Grafana secret
        kubectl create secret generic grafana-secret \
            --from-literal=admin-user=admin \
            --from-literal=admin-password=$(openssl rand -base64 16) \
            -n $NAMESPACE \
            --dry-run=client -o yaml | kubectl apply -f -
        
        echo "✅ Kubernetes secrets created"
    fi
    
    # Create ConfigMaps
    echo "📋 Creating Kubernetes ConfigMaps..."
    
    # Application config
    kubectl create configmap app-config \
        --from-file=config.yaml=./config.yaml \
        -n $NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    
    echo "✅ Kubernetes ConfigMaps created"
    
    # Create network policies
    echo "🛡️  Creating network policies..."
    
    cat > network-policy.yaml << EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: flavorsnap-network-policy
  namespace: $NAMESPACE
spec:
  podSelector:
    matchLabels:
      app: flavorsnap
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 5000
  - from:
    - podSelector:
        matchLabels:
          app: flavorsnap
    ports:
    - protocol: TCP
      port: 5000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to: []
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 80
EOF
    
    kubectl apply -f network-policy.yaml
    echo "✅ Network policies created"
fi

# Setup Docker registry (for local development)
if [[ "$SKIP_DOCKER" == false && "$ENVIRONMENT" == "staging" ]]; then
    echo "🐳 Setting up local Docker registry..."
    
    # Check if registry is already running
    if ! docker ps | grep -q "registry:2"; then
        docker run -d -p 5000:5000 --name local-registry registry:2
        echo "✅ Local Docker registry started"
    else
        echo "✅ Local Docker registry already running"
    fi
fi

# Create monitoring configuration
echo "📊 Setting up monitoring configuration..."

# Create Prometheus configuration
mkdir -p monitoring/grafana/datasources monitoring/grafana/dashboards

cat > monitoring/grafana/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF

# Create Grafana dashboard configuration
cat > monitoring/grafana/dashboards/dashboard.yml << EOF
apiVersion: 1

providers:
  - name: 'flavorsnap-dashboards'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

echo "✅ Monitoring configuration created"

# Create startup scripts
echo "📜 Creating startup scripts..."

# Development startup script
cat > start-dev.sh << 'EOF'
#!/bin/bash

# Development startup script
set -e

echo "🚀 Starting FlavorSnap development environment..."

# Load environment
source .env.staging

# Start services with monitoring
docker-compose --profile blue,monitoring up -d

echo "✅ Development environment started!"
echo "API: http://localhost:5001"
echo "Grafana: http://localhost:3000 (admin/admin)"
echo "Prometheus: http://localhost:9090"
EOF

chmod +x start-dev.sh

# Production startup script
cat > start-prod.sh << 'EOF'
#!/bin/bash

# Production startup script
set -e

echo "🚀 Starting FlavorSnap production environment..."

# Load environment
source .env.production

# Start all services
docker-compose --profile full up -d

echo "✅ Production environment started!"
echo "API: http://localhost"
echo "Grafana: http://localhost:3000"
echo "Prometheus: http://localhost:9090"
EOF

chmod +x start-prod.sh

echo "✅ Startup scripts created"

# Create cleanup script
cat > cleanup.sh << 'EOF'
#!/bin/bash

# Cleanup script
set -e

echo "🧹 Cleaning up FlavorSnap environment..."

# Stop and remove containers
docker-compose down --remove-orphans

# Remove volumes (comment out if you want to keep data)
docker-compose down -v

# Remove images
docker rmi $(docker images -q flavorsnap-api) 2>/dev/null || true

echo "✅ Cleanup completed!"
EOF

chmod +x cleanup.sh

echo "✅ Cleanup script created"

# Final setup steps
echo "🎯 Performing final setup steps..."

# Create logs directory
mkdir -p ml-model-api/logs
mkdir -p ml-model-api/uploads
mkdir -p ml-model-api/reports

# Set permissions
chmod 755 ml-model-api/logs
chmod 755 ml-model-api/uploads
chmod 755 ml-model-api/reports

# Create .dockerignore
cat > .dockerignore << EOF
.git
.gitignore
README.md
.env.*
node_modules
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis

# IDE
.vscode
.idea
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Project specific
test_uploads
*.pth
models/
dataset/
EOF

echo "✅ .dockerignore created"

echo ""
echo "🎉 Environment setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Review and update .env.$ENVIRONMENT with your specific values"
echo "2. Run 'source .env.$ENVIRONMENT' to load environment variables"
echo "3. Run './start-dev.sh' (for staging) or './start-prod.sh' (for production)"
echo "4. Access the application at the URLs shown above"
echo ""
echo "For deployment:"
echo "- Use './scripts/deploy.sh' to deploy new versions"
echo "- Use './scripts/rollback.sh' to rollback if needed"
echo ""
echo "Environment: $ENVIRONMENT"
echo "Namespace: $NAMESPACE"
echo "Docker Registry: $DOCKER_REGISTRY"
