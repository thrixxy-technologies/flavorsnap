#!/bin/bash

# Advanced Load Balancer Deployment Script
# This script deploys the complete advanced load balancing infrastructure

set -e

# Configuration
NAMESPACE="flavorsnap"
KUBECTL="kubectl"
HELM="helm"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v $KUBECTL &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check helm
    if ! command -v $HELM &> /dev/null; then
        log_error "helm is not installed or not in PATH"
        exit 1
    fi
    
    # Check cluster access
    if ! $KUBECTL cluster-info &> /dev/null; then
        log_error "Cannot access Kubernetes cluster"
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

# Create namespace
create_namespace() {
    log_info "Creating namespace: $NAMESPACE"
    
    if $KUBECTL get namespace $NAMESPACE &> /dev/null; then
        log_warn "Namespace $NAMESPACE already exists"
    else
        $KUBECTL create namespace $NAMESPACE
        log_info "Namespace $NAMESPACE created"
    fi
}

# Deploy advanced load balancer
deploy_load_balancer() {
    log_info "Deploying advanced load balancer..."
    
    # Apply ConfigMaps and Secrets
    log_info "Applying ConfigMaps..."
    $KUBECTL apply -f k8s/load-balancer/nginx-config.yaml -n $NAMESPACE
    
    # Deploy the load balancer
    log_info "Deploying load balancer deployment..."
    $KUBECTL apply -f k8s/load-balancer/advanced-load-balancer.yaml -n $NAMESPACE
    
    # Wait for deployment to be ready
    log_info "Waiting for load balancer to be ready..."
    $KUBECTL wait --for=condition=available --timeout=300s deployment/advanced-load-balancer -n $NAMESPACE
    
    log_info "Load balancer deployed successfully"
}

# Deploy monitoring
deploy_monitoring() {
    log_info "Deploying monitoring..."
    
    # Apply ServiceMonitor and PrometheusRules
    $KUBECTL apply -f k8s/load-balancer/service-monitor.yaml -n $NAMESPACE
    
    log_info "Monitoring deployed successfully"
}

# Deploy Ingress with advanced features
deploy_ingress() {
    log_info "Deploying advanced Ingress..."
    
    cat <<EOF | $KUBECTL apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: advanced-flavorsnap-ingress
  namespace: $NAMESPACE
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
    nginx.ingress.kubernetes.io/upstream-hash-by: "\$remote_addr"
    nginx.ingress.kubernetes.io/load-balance: "least_conn"
    nginx.ingress.kubernetes.io/connection-proxy-header: "keep-alive"
    nginx.ingress.kubernetes.io/proxy-connect-timeout: "30"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "600"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-origin: "*"
    nginx.ingress.kubernetes.io/cors-allow-methods: "GET, POST, PUT, DELETE, OPTIONS"
    nginx.ingress.kubernetes.io/cors-allow-headers: "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization"
spec:
  tls:
  - hosts:
    - flavorsnap.example.com
    secretName: advanced-flavorsnap-tls
  rules:
  - host: flavorsnap.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: advanced-load-balancer-service
            port:
              number: 80
      - path: /predict
        pathType: Prefix
        backend:
          service:
            name: advanced-load-balancer-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: advanced-load-balancer-service
            port:
              number: 80
EOF
    
    log_info "Advanced Ingress deployed successfully"
}

# Deploy NetworkPolicies for security
deploy_network_policies() {
    log_info "Deploying NetworkPolicies..."
    
    cat <<EOF | $KUBECTL apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: load-balancer-netpol
  namespace: $NAMESPACE
spec:
  podSelector:
    matchLabels:
      app: advanced-load-balancer
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
      port: 80
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 9113
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: backend
    ports:
    - protocol: TCP
      port: 5000
  - to:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 3000
  - to: []
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 443
EOF
    
    log_info "NetworkPolicies deployed successfully"
}

# Setup autoscaling
setup_autoscaling() {
    log_info "Setting up autoscaling..."
    
    # Vertical Pod Autoscaler (if available)
    cat <<EOF | $KUBECTL apply -f -
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: advanced-lb-vpa
  namespace: $NAMESPACE
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: advanced-load-balancer
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: nginx-lb
      maxAllowed:
        cpu: 1
        memory: 1Gi
      minAllowed:
        cpu: 100m
        memory: 128Mi
EOF
    
    log_info "Autoscaling configured"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check pods
    log_info "Checking pod status..."
    $KUBECTL get pods -l app=advanced-load-balancer -n $NAMESPACE
    
    # Check services
    log_info "Checking services..."
    $KUBECTL get services -n $NAMESPACE | grep load-balancer
    
    # Check ingress
    log_info "Checking ingress..."
    $KUBECTL get ingress -n $NAMESPACE
    
    # Test health endpoint
    log_info "Testing health endpoint..."
    LB_IP=$($KUBECTL get service advanced-load-balancer-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    if [ -n "$LB_IP" ]; then
        if curl -f -s "http://$LB_IP/health" > /dev/null; then
            log_info "Health check passed"
        else
            log_error "Health check failed"
            exit 1
        fi
    else
        log_warn "Load balancer IP not available yet"
    fi
    
    log_info "Deployment verification completed"
}

# Show deployment status
show_status() {
    log_info "Deployment Status:"
    echo "===================="
    
    echo "Namespace: $NAMESPACE"
    echo "Load Balancer Service:"
    $KUBECTL get service advanced-load-balancer-service -n $NAMESPACE -o wide
    echo ""
    echo "Ingress:"
    $KUBECTL get ingress -n $NAMESPACE
    echo ""
    echo "Pods:"
    $KUBECTL get pods -l app=advanced-load-balancer -n $NAMESPACE
    echo ""
    echo "HPA Status:"
    $KUBECTL get hpa -n $NAMESPACE
    echo ""
    
    # Get load balancer URL
    LB_IP=$($KUBECTL get service advanced-load-balancer-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    if [ -n "$LB_IP" ]; then
        echo "Load Balancer URL: http://$LB_IP"
        echo "Health Check URL: http://$LB_IP/health"
        echo "Metrics URL: http://$LB_IP/metrics"
    fi
}

# Cleanup function
cleanup() {
    log_warn "Cleaning up deployment..."
    
    $KUBECTL delete -f k8s/load-balancer/advanced-load-balancer.yaml -n $NAMESPACE --ignore-not-found=true
    $KUBECTL delete -f k8s/load-balancer/nginx-config.yaml -n $NAMESPACE --ignore-not-found=true
    $KUBECTL delete -f k8s/load-balancer/service-monitor.yaml -n $NAMESPACE --ignore-not-found=true
    $KUBECTL delete networkpolicy load-balancer-netpol -n $NAMESPACE --ignore-not-found=true
    $KUBECTL delete vpa advanced-lb-vpa -n $NAMESPACE --ignore-not-found=true
    $KUBECTL delete ingress advanced-flavorsnap-ingress -n $NAMESPACE --ignore-not-found=true
    
    log_info "Cleanup completed"
}

# Main function
main() {
    case "${1:-deploy}" in
        "deploy")
            check_prerequisites
            create_namespace
            deploy_load_balancer
            deploy_monitoring
            deploy_ingress
            deploy_network_policies
            setup_autoscaling
            verify_deployment
            show_status
            ;;
        "cleanup")
            cleanup
            ;;
        "status")
            show_status
            ;;
        "verify")
            verify_deployment
            ;;
        *)
            echo "Usage: $0 {deploy|cleanup|status|verify}"
            echo ""
            echo "Commands:"
            echo "  deploy   - Deploy the complete advanced load balancing infrastructure"
            echo "  cleanup  - Remove all deployed resources"
            echo "  status   - Show current deployment status"
            echo "  verify   - Verify the deployment is working correctly"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
