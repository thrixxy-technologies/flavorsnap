#!/bin/bash

# FlavorSnap Docker Deployment Script
# This script handles the complete Docker deployment process

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-production}
COMPOSE_FILE="docker-compose.yml"
DEV_COMPOSE_FILE="docker-compose.dev.yml"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if model file exists
    if [ ! -f "model.pth" ]; then
        log_warn "Model file 'model.pth' not found. Please ensure it's in the project root."
    fi
    
    log_info "Prerequisites check completed."
}

setup_environment() {
    log_info "Setting up environment for $ENVIRONMENT..."
    
    # Copy environment file
    if [ ! -f ".env" ]; then
        if [ -f ".env.docker" ]; then
            cp .env.docker .env
            log_info "Created .env from .env.docker"
        else
            log_warn "No .env file found. Creating default configuration."
            cat > .env << EOF
BUILD_ENV=production
FRONTEND_PORT=3000
BACKEND_PORT=5000
NEXT_PUBLIC_API_URL=http://backend:5000
NEXT_PUBLIC_MODEL_ENDPOINT=/predict
MODEL_PATH=/app/models/model.pth
UPLOAD_FOLDER=/app/uploads
LOG_LEVEL=INFO
EOF
        fi
    fi
    
    # Create necessary directories
    mkdir -p logs/nginx
    mkdir -p ml-model-api/uploads
    mkdir -p ml-model-api/logs
    mkdir -p nginx/ssl
    
    log_info "Environment setup completed."
}

build_images() {
    log_info "Building Docker images..."
    
    if [ "$ENVIRONMENT" = "development" ]; then
        docker-compose -f $DEV_COMPOSE_FILE build
    else
        docker-compose -f $COMPOSE_FILE build
    fi
    
    log_info "Docker images built successfully."
}

start_services() {
    log_info "Starting services..."
    
    if [ "$ENVIRONMENT" = "development" ]; then
        docker-compose -f $DEV_COMPOSE_FILE up -d
    else
        docker-compose -f $COMPOSE_FILE up -d
    fi
    
    log_info "Services started successfully."
}

health_check() {
    log_info "Performing health checks..."
    
    # Wait for services to start
    sleep 10
    
    # Check frontend
    if curl -f http://localhost:${FRONTEND_PORT:-3000}/ > /dev/null 2>&1; then
        log_info "Frontend is healthy"
    else
        log_error "Frontend health check failed"
    fi
    
    # Check backend
    if curl -f http://localhost:${BACKEND_PORT:-5000}/health > /dev/null 2>&1; then
        log_info "Backend is healthy"
    else
        log_error "Backend health check failed"
    fi
}

show_status() {
    log_info "Service status:"
    
    if [ "$ENVIRONMENT" = "development" ]; then
        docker-compose -f $DEV_COMPOSE_FILE ps
    else
        docker-compose -f $COMPOSE_FILE ps
    fi
}

show_logs() {
    log_info "Recent logs:"
    
    if [ "$ENVIRONMENT" = "development" ]; then
        docker-compose -f $DEV_COMPOSE_FILE logs --tail=50
    else
        docker-compose -f $COMPOSE_FILE logs --tail=50
    fi
}

cleanup() {
    log_info "Cleaning up old containers and images..."
    
    # Stop and remove containers
    if [ "$ENVIRONMENT" = "development" ]; then
        docker-compose -f $DEV_COMPOSE_FILE down -v
    else
        docker-compose -f $COMPOSE_FILE down -v
    fi
    
    # Remove unused images
    docker image prune -f
    
    log_info "Cleanup completed."
}

# Main execution
main() {
    case "$2" in
        "build")
            check_prerequisites
            setup_environment
            build_images
            ;;
        "start")
            check_prerequisites
            setup_environment
            start_services
            health_check
            show_status
            ;;
        "stop")
            if [ "$ENVIRONMENT" = "development" ]; then
                docker-compose -f $DEV_COMPOSE_FILE down
            else
                docker-compose -f $COMPOSE_FILE down
            fi
            log_info "Services stopped."
            ;;
        "restart")
            main "$1" "stop"
            main "$1" "start"
            ;;
        "logs")
            show_logs
            ;;
        "status")
            show_status
            ;;
        "cleanup")
            cleanup
            ;;
        "full")
            main "$1" "cleanup"
            main "$1" "build"
            main "$1" "start"
            ;;
        *)
            echo "Usage: $0 <environment> <command>"
            echo ""
            echo "Environments:"
            echo "  production    Production deployment with Nginx"
            echo "  development   Development deployment"
            echo ""
            echo "Commands:"
            echo "  build         Build Docker images"
            echo "  start         Start services"
            echo "  stop          Stop services"
            echo "  restart       Restart services"
            echo "  logs          Show logs"
            echo "  status        Show service status"
            echo "  cleanup       Clean up containers and images"
            echo "  full          Full deployment (cleanup + build + start)"
            echo ""
            echo "Examples:"
            echo "  $0 production full"
            echo "  $0 development start"
            echo "  $0 production logs"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
