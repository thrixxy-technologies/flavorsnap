#!/bin/bash

# Advanced Logging System Deployment Script
# Deploys comprehensive logging infrastructure with structured logs, aggregation, and analysis

set -e

# Configuration
NAMESPACE="flavorsnap-logging"
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

# Deploy logging infrastructure
deploy_logging_infrastructure() {
    log_info "Deploying logging infrastructure..."
    
    # Apply logging infrastructure from YAML file
    if [ -f "k8s/logging/logging-infrastructure.yaml" ]; then
        $KUBECTL apply -f k8s/logging/logging-infrastructure.yaml -n $NAMESPACE
        log_info "Logging infrastructure deployed from YAML"
    else
        log_error "logging-infrastructure.yaml not found"
        exit 1
    fi
}

# Deploy Elasticsearch
deploy_elasticsearch() {
    log_info "Deploying Elasticsearch..."
    
    # Wait for Elasticsearch to be ready
    log_info "Waiting for Elasticsearch to be ready..."
    $KUBECTL wait --for=condition=available pod -l app=flavorsnap-logging,component=elasticsearch -n $NAMESPACE --timeout=300s
    $KUBECTL wait --for=condition=ready pod -l app=flavorsnap-logging,component=elasticsearch -n $NAMESPACE --timeout=300s
    
    # Check Elasticsearch health
    log_info "Checking Elasticsearch health..."
    ES_POD=$($KUBECTL get pods -l app=flavorsnap-logging,component=elasticsearch -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}')
    
    if [ -n "$ES_POD" ]; then
        $KUBECTL exec -n $NAMESPACE $ES_POD -- curl -s http://localhost:9200/_cluster/health || true
        log_info "Elasticsearch health check completed"
    else
        log_warn "Elasticsearch pod not found"
    fi
}

# Deploy Logstash
deploy_logstash() {
    log_info "Deploying Logstash..."
    
    # Wait for Logstash to be ready
    log_info "Waiting for Logstash to be ready..."
    $KUBECTL wait --for=condition=available pod -l app=flavorsnap-logging,component=logstash -n $NAMESPACE --timeout=300s
    $KUBECTL wait --for=condition=ready pod -l app=flavorsnap-logging,component=logstash -n $NAMESPACE --timeout=300s
    
    # Check Logstash configuration
    log_info "Checking Logstash configuration..."
    LOGSTASH_POD=$($KUBECTL get pods -l app=flavorsnap-logging,component=logstash -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}')
    
    if [ -n "$LOGSTASH_POD" ]; then
        $KUBECTL exec -n $NAMESPACE $LOGSTASH_POD -- curl -s http://localhost:9600/_node/stats || true
        log_info "Logstash status check completed"
    else
        log_warn "Logstash pod not found"
    fi
}

# Deploy Kibana
deploy_kibana() {
    log_info "Deploying Kibana..."
    
    # Wait for Kibana to be ready
    log_info "Waiting for Kibana to be ready..."
    $KUBECTL wait --for=condition=available pod -l app=flavorsnap-logging,component=kibana -n $NAMESPACE --timeout=300s
    $KUBECTL wait --for=condition=ready pod -l app=flavorsnap-logging,component=kibana -n $NAMESPACE --timeout=300s
    
    # Check Kibana health
    log_info "Checking Kibana health..."
    KIBANA_POD=$($KUBECTL get pods -l app=flavorsnap-logging,component=kibana -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}')
    
    if [ -n "$KIBANA_POD" ]; then
        $KUBECTL exec -n $NAMESPACE $KIBANA_POD -- curl -s http://localhost:5601/api/status || true
        log_info "Kibana health check completed"
    else
        log_warn "Kibana pod not found"
    fi
}

# Deploy Filebeat
deploy_filebeat() {
    log_info "Deploying Filebeat..."
    
    # Wait for Filebeat to be ready
    log_info "Waiting for Filebeat to be ready..."
    $KUBECTL wait --for=condition=available pod -l app=flavorsnap-logging,component=filebeat -n $NAMESPACE --timeout=300s
    $KUBECTL wait --for=condition=ready pod -l app=flavorsnap-logging,component=filebeat -n $NAMESPACE --timeout=300s
    
    # Check Filebeat status
    log_info "Checking Filebeat status..."
    FILEBEAT_POD=$($KUBECTL get pods -l app=flavorsnap-logging,component=filebeat -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}')
    
    if [ -n "$FILEBEAT_POD" ]; then
        $KUBECTL exec -n $NAMESPACE $FILEBEAT_POD -- curl -s http://localhost:5066/stats || true
        log_info "Filebeat status check completed"
    else
        log_warn "Filebeat pod not found"
    fi
}

# Deploy Fluentd (alternative to Filebeat)
deploy_fluentd() {
    log_info "Deploying Fluentd..."
    
    # Wait for Fluentd to be ready
    log_info "Waiting for Fluentd to be ready..."
    $KUBECTL wait --for=condition=available pod -l app=flavorsnap-logging,component=fluentd -n $NAMESPACE --timeout=300s
    $KUBECTL wait --for=condition=ready pod -l app=flavorsnap-logging,component=fluentd -n $NAMESPACE --timeout=300s
    
    # Check Fluentd status
    log_info "Checking Fluentd status..."
    FLUENTD_POD=$($KUBECTL get pods -l app=flavorsnap-logging,component=fluentd -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}')
    
    if [ -n "$FLUENTD_POD" ]; then
        $KUBECTL exec -n $NAMESPACE $FLUENTD_POD -- curl -s http://localhost:24231/api/plugins.json || true
        log_info "Fluentd status check completed"
    else
        log_warn "Fluentd pod not found"
    fi
}

# Deploy Loki (alternative to Elasticsearch)
deploy_loki() {
    log_info "Deploying Loki..."
    
    # Wait for Loki to be ready
    log_info "Waiting for Loki to be ready..."
    $KUBECTL wait --for=condition=available pod -l app=flavorsnap-logging,component=loki -n $NAMESPACE --timeout=300s
    $KUBECTL wait --for=condition=ready pod -l app=flavorsnap-logging,component=loki -n $NAMESPACE --timeout=300s
    
    # Check Loki health
    log_info "Checking Loki health..."
    LOKI_POD=$($KUBECTL get pods -l app=flavorsnap-logging,component=loki -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}')
    
    if [ -n "$LOKI_POD" ]; then
        $KUBECTL exec -n $NAMESPACE $LOKI_POD -- curl -s http://localhost:3100/ready || true
        log_info "Loki health check completed"
    else
        log_warn "Loki pod not found"
    fi
}

# Deploy Grafana
deploy_grafana() {
    log_info "Deploying Grafana..."
    
    # Wait for Grafana to be ready
    log_info "Waiting for Grafana to be ready..."
    $KUBECTL wait --for=condition=available pod -l app=flavorsnap-logging,component=grafana -n $NAMESPACE --timeout=300s
    $KUBECTL wait --for=condition=ready pod -l app=flavorsnap-logging,component=grafana -n $NAMESPACE --timeout=300s
    
    # Check Grafana health
    log_info "Checking Grafana health..."
    GRAFANA_POD=$($KUBECTL get pods -l app=flavorsnap-logging,component=grafana -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}')
    
    if [ -n "$GRAFANA_POD" ]; then
        $KUBECTL exec -n $NAMESPACE $GRAFANA_POD -- curl -s http://localhost:3000/api/health || true
        log_info "Grafana health check completed"
    else
        log_warn "Grafana pod not found"
    fi
}

# Setup log collection
setup_log_collection() {
    log_info "Setting up log collection..."
    
    # Create log directories on nodes
    log_info "Creating log directories..."
    $KUBECTL create configmap log-dirs -n $NAMESPACE --from-literal=log-dir="/var/log/flavorsnap" --dry-run=client -o yaml | $KUBECTL apply -f -
    
    # Deploy DaemonSet for log collection
    if [ -f "k8s/logging/logging-infrastructure.yaml" ]; then
        # Extract and apply Filebeat DaemonSet
        $KUBECTL apply -f <(sed -n '/^---/,/^---/p' k8s/logging/logging-infrastructure.yaml | sed -n '/^apiVersion.*DaemonSet/,/^---/p') -n $NAMESPACE
        log_info "Log collection DaemonSet deployed"
    fi
}

# Configure log routing
configure_log_routing() {
    log_info "Configuring log routing..."
    
    # Create routing rules
    cat <<EOF | $KUBECTL apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: log-routing-rules
  namespace: $NAMESPACE
data:
  routing.yaml: |
    # Log routing rules
    routes:
      - source: flavorsnap-app
        destination: elasticsearch
        conditions:
          - level: ERROR
          - level: CRITICAL
      - source: flavorsnap-app
        destination: elasticsearch
        conditions:
          - level: INFO
          - level: WARNING
      - source: flavorsnap-security
        destination: elasticsearch
        conditions:
          - event_type: security_event
      - source: flavorsnap-audit
        destination: elasticsearch
        conditions:
          - event_type: audit_event
      - source: flavorsnap-performance
        destination: elasticsearch
        conditions:
          - event_type: performance_event
EOF
    
    log_info "Log routing rules configured"
}

# Setup log retention
setup_log_retention() {
    log_info "Setting up log retention policies..."
    
    # Create retention policy for Elasticsearch
    cat <<EOF | $KUBECTL apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: log-retention-policies
  namespace: $NAMESPACE
data:
  retention.yaml: |
    # Elasticsearch retention policies
    policies:
      - pattern: "flavorsnap-logs-*"
        time_based:
          unit: "days"
          value: 30
        actions:
          - delete
      - pattern: "flavorsnap-audit-*"
        time_based:
          unit: "days"
          value: 2555  # 7 years for audit logs
        actions:
          - delete
      - pattern: "flavorsnap-security-*"
        time_based:
          unit: "days"
          value: 365  # 1 year for security logs
        actions:
          - delete
EOF
    
    log_info "Log retention policies configured"
}

# Setup monitoring
setup_monitoring() {
    log_info "Setting up monitoring for logging infrastructure..."
    
    # Deploy monitoring for logging components
    cat <<EOF | $KUBECTL apply -f -
apiVersion: v1
kind: ServiceMonitor
metadata:
  name: logging-components
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-logging
    component: monitoring
spec:
  selector:
    matchLabels:
      app: flavorsnap-logging
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
EOF
    
    # Deploy Prometheus rules for logging
    cat <<EOF | $KUBECTL apply -f -
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: logging-alerts
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-logging
    component: alerting
spec:
  groups:
  - name: logging.rules
    rules:
    - alert: ElasticsearchDown
      expr: up{job="elasticsearch"} == 0
      for: 1m
      labels:
        severity: critical
        service: elasticsearch
      annotations:
        summary: "Elasticsearch is down"
        description: "Elasticsearch has been down for more than 1 minute"
    
    - alert: LogstashDown
      expr: up{job="logstash"} == 0
      for: 1m
      labels:
        severity: critical
        service: logstash
      annotations:
        summary: "Logstash is down"
        description: "Logstash has been down for more than 1 minute"
    
    - alert: HighErrorRate
      expr: rate(elasticsearch_logs_total{level="ERROR"}[5m]) > 10
      for: 2m
      labels:
        severity: warning
        service: elasticsearch
      annotations:
        summary: "High error rate detected"
        description: "Error rate is {{ $value }} errors per second"
    
    - alert: DiskSpaceLow
      expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100 < 10
      for: 5m
      labels:
        severity: warning
        service: node
      annotations:
        summary: "Low disk space"
        description: "Disk space is below 10%"
EOF
    
    log_info "Monitoring for logging infrastructure configured"
}

# Setup security
setup_security() {
    log_info "Setting up security for logging infrastructure..."
    
    # Create network policies
    cat <<EOF | $KUBECTL apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: logging-security
  namespace: $NAMESPACE
spec:
  podSelector:
    matchLabels:
      app: flavorsnap-logging
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: flavorsnap
    - namespaceSelector:
        matchLabels:
          name: monitoring
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: TCP
      port: 9200
    - protocol: TCP
      port: 5044
    - protocol: TCP
      port: 5601
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: flavorsnap
    - namespaceSelector:
        matchLabels:
          name: monitoring
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: TCP
      port: 9200
    - protocol: TCP
      port: 5044
    - protocol: TCP
      port: 5601
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 443
EOF
    
    # Create RBAC
    cat <<EOF | $KUBECTL apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: logging-service-account
  namespace: $NAMESPACE
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: logging-role
rules:
- apiGroups: [""]
  resources: ["pods", "services", "endpoints"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets", "daemonsets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["extensions"]
  resources: ["ingresses"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: logging-role-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: logging-role
subjects:
- kind: ServiceAccount
  name: logging-service-account
  namespace: $NAMESPACE
EOF
    
    log_info "Security for logging infrastructure configured"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying logging deployment..."
    
    # Check all pods
    log_info "Checking all logging pods..."
    $KUBECTL get pods -n $NAMESPACE -l app=flavorsnap-logging
    
    # Check services
    log_info "Checking logging services..."
    $KUBECTL get services -n $NAMESPACE -l app=flavorsnap-logging
    
    # Check persistent volumes
    log_info "Checking persistent volumes..."
    $KUBECTL get pvc -n $NAMESPACE
    
    # Test Elasticsearch connectivity
    log_info "Testing Elasticsearch connectivity..."
    ES_SERVICE=$($KUBECTL get service elasticsearch -n $NAMESPACE -o jsonpath='{.spec.clusterIP}')
    if [ -n "$ES_SERVICE" ]; then
        curl -s "http://$ES_SERVICE:9200/_cluster/health" | jq '.' || echo "Health check failed"
    fi
    
    # Test Kibana connectivity
    log_info "Testing Kibana connectivity..."
    KIBANA_SERVICE=$($KUBECTL get service kibana -n $NAMESPACE -o jsonpath='{.spec.clusterIP}')
    if [ -n "$KIBANA_SERVICE" ]; then
        curl -s "http://$KIBANA_SERVICE:5601/api/status" | jq '.' || echo "Status check failed"
    fi
    
    # Test Grafana connectivity
    log_info "Testing Grafana connectivity..."
    GRAFANA_SERVICE=$($KUBECTL get service grafana -n $NAMESPACE -o jsonpath='{.spec.clusterIP}')
    if [ -n "$GRAFANA_SERVICE" ]; then
        curl -s "http://$GRAFANA_SERVICE:3000/api/health" | jq '.' || echo "Health check failed"
    fi
    
    log_info "Deployment verification completed"
}

# Show deployment status
show_status() {
    log_info "Logging System Deployment Status:"
    echo "=============================="
    
    echo "Namespace: $NAMESPACE"
    echo "Elasticsearch:"
    $KUBECTL get pods -l component=elasticsearch -n $NAMESPACE -o wide
    echo ""
    echo "Logstash:"
    $KUBECTL get pods -l component=logstash -n $NAMESPACE -o wide
    echo ""
    echo "Kibana:"
    $KUBECTL get pods -l component=kibana -n $NAMESPACE -o wide
    echo ""
    echo "Grafana:"
    $KUBECTL get pods -l component=grafana -n $NAMESPACE -o wide
    echo ""
    echo "Filebeat:"
    $KUBECTL get pods -l component=filebeat -n $NAMESPACE -o wide
    echo ""
    echo "Services:"
    $KUBECTL get services -n $NAMESPACE -l app=flavorsnap-logging
    echo ""
    
    # Get service URLs
    ES_SERVICE=$($KUBECTL get service elasticsearch -n $NAMESPACE -o jsonpath='{.spec.clusterIP}')
    KIBANA_SERVICE=$($KUBECTL get service kibana -n $NAMESPACE -o jsonpath='{.spec.clusterIP}')
    GRAFANA_SERVICE=$($KUBECTL get service grafana -n $NAMESPACE -o jsonpath='{.spec.clusterIP}')
    
    echo "Service URLs:"
    if [ -n "$ES_SERVICE" ]; then
        echo "  Elasticsearch: http://$ES_SERVICE:9200"
        echo "  Elasticsearch API: http://$ES_SERVICE:9200/api"
    fi
    if [ -n "$KIBANA_SERVICE" ]; then
        echo "  Kibana: http://$KIBANA_SERVICE:5601"
        echo "  Kibana API: http://$KIBANA_SERVICE:5601/api"
    fi
    if [ -n "$GRAFANA_SERVICE" ]; then
        echo "  Grafana: http://$GRAFANA_SERVICE:3000"
        echo "  Grafana API: http://$GRAFANA_SERVICE:3000/api"
        echo "  Grafana Login: admin/adminadmin"
    fi
    echo ""
}

# Cleanup function
cleanup() {
    log_warn "Cleaning up logging deployment..."
    
    $KUBECTL delete namespace $NAMESPACE --ignore-not-found=true
    $KUBECTL delete clusterrole logging-role --ignore-not-found=true
    $KUBECTL delete clusterrolebinding logging-role-binding --ignore-not-found=true
    $KUBECTL delete serviceaccount logging-service-account --ignore-not-found=true
    
    log_info "Cleanup completed"
}

# Scale logging components
scale_logging() {
    local component=$1
    local replicas=$2
    
    log_info "Scaling $component to $replicas replicas..."
    
    case $component in
        elasticsearch)
            $KUBECTL scale statefulset elasticsearch -n $NAMESPACE --replicas=$replicas
            ;;
        logstash)
            $KUBECTL scale deployment logstash -n $NAMESPACE --replicas=$replicas
            ;;
        kibana)
            $KUBECTL scale deployment kibana -n $NAMESPACE --replicas=$replicas
            ;;
        grafana)
            $KUBECTL scale deployment grafana -n $NAMESPACE --replicas=$replicas
            ;;
        filebeat)
            $KUBECTL scale daemonset filebeat -n $NAMESPACE --replicas=$replicas
            ;;
        *)
            log_error "Unknown component: $component"
            return 1
            ;;
    esac
    
    log_info "Scaling $component completed"
}

# Main function
main() {
    case "${1:-deploy}" in
        "deploy")
            check_prerequisites
            create_namespace
            deploy_logging_infrastructure
            setup_log_collection
            configure_log_routing
            setup_log_retention
            setup_monitoring
            setup_security
            verify_deployment
            show_status
            ;;
        "cleanup")
            cleanup
            ;;
        "status")
            show_status
            ;;
        "scale")
            if [ -z "$2" ] || [ -z "$3" ]; then
                echo "Usage: $0 scale <component> <replicas>"
                echo "Components: elasticsearch, logstash, kibana, grafana, filebeat"
                exit 1
            fi
            scale_logging "$2" "$3"
            ;;
        "verify")
            verify_deployment
            ;;
        *)
            echo "Usage: $0 {deploy|cleanup|status|scale|verify}"
            echo ""
            echo "Commands:"
            echo "  deploy   - Deploy complete logging infrastructure"
            echo "  cleanup  - Remove all logging components"
            echo "  status   - Show deployment status"
            echo "  scale    - Scale logging components"
            echo "  verify   - Verify deployment is working"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
