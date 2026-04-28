#!/bin/bash

# Intelligent Auto-Scaling Deployment Script
# Deploys comprehensive auto-scaling with predictive capabilities and cost optimization

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

# Deploy custom metrics server
deploy_metrics_server() {
    log_info "Deploying custom metrics server..."
    
    # Create metrics server config
    cat <<EOF | $KUBECTL apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: metrics-server-config
  namespace: kube-system
data:
  Nginx: |
    server {
      listen 8080;
      location /metrics {
        access_log off;
        return 200 "OK";
      }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: custom-metrics-server
  namespace: kube-system
  labels:
    app: custom-metrics-server
spec:
  replicas: 2
  selector:
    matchLabels:
      app: custom-metrics-server
  template:
    metadata:
      labels:
        app: custom-metrics-server
    spec:
      containers:
      - name: metrics-server
        image: nginx:1.25-alpine
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "128Mi"
            cpu: "100m"
        volumeMounts:
        - name: config
          mountPath: /etc/nginx/conf.d/default.conf
          subPath: default.conf
      volumes:
      - name: config
        configMap:
          name: metrics-server-config
---
apiVersion: v1
kind: Service
metadata:
  name: custom-metrics-server
  namespace: kube-system
  labels:
    app: custom-metrics-server
spec:
  selector:
    app: custom-metrics-server
  ports:
  - port: 8080
    targetPort: 8080
    name: metrics
  type: ClusterIP
EOF
    
    log_info "Custom metrics server deployed"
}

# Deploy auto-scaling components
deploy_autoscaling() {
    log_info "Deploying auto-scaling components..."
    
    # Deploy Horizontal Pod Autoscalers
    log_info "Deploying Horizontal Pod Autoscalers..."
    $KUBECTL apply -f k8s/autoscaling/horizontal-pod-autoscaler.yaml -n $NAMESPACE
    
    # Deploy Vertical Pod Autoscalers
    log_info "Deploying Vertical Pod Autoscalers..."
    $KUBECTL apply -f k8s/autoscaling/vertical-pod-autoscaler.yaml -n $NAMESPACE
    
    # Deploy Cluster Autoscaler
    log_info "Deploying Cluster Autoscaler..."
    $KUBECTL apply -f k8s/autoscaling/cluster-autoscaler.yaml -n kube-system
    
    log_info "Auto-scaling components deployed successfully"
}

# Deploy monitoring for scaling
deploy_monitoring() {
    log_info "Deploying monitoring for auto-scaling..."
    
    # Deploy scaling metrics and alerts
    $KUBECTL apply -f monitoring/scaling/scaling-metrics.yaml -n $NAMESPACE
    
    log_info "Monitoring deployed successfully"
}

# Deploy intelligent autoscaler
deploy_intelligent_autoscaler() {
    log_info "Deploying intelligent autoscaler..."
    
    cat <<EOF | $KUBECTL apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: autoscaler-config
  namespace: $NAMESPACE
data:
  config.yaml: |
    namespace: "$NAMESPACE"
    prometheus_url: "http://prometheus-service:9090"
    model_path: "/models/scaling_model.pkl"
    model_type: "random_forest"
    cost_optimization_strategy: "balanced"
    optimization_interval: "300"
    predictive_enabled: "true"
    cost:
      cost_per_cpu_hour: "0.05"
      cost_per_gb_memory_hour: "0.01"
      cost_per_node_hour: "0.10"
      spot_instance_discount: "0.7"
    thresholds:
      min_savings_percentage: "10"
      max_spot_ratio: "0.5"
      min_efficiency_score: "0.7"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: intelligent-autoscaler
  namespace: $NAMESPACE
  labels:
    app: intelligent-autoscaler
    component: autoscaling
spec:
  replicas: 2
  selector:
    matchLabels:
      app: intelligent-autoscaler
  template:
    metadata:
      labels:
        app: intelligent-autoscaler
        component: autoscaling
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: autoscaler-service-account
      containers:
      - name: autoscaler
        image: flavorsnap/intelligent-autoscaler:latest
        ports:
        - containerPort: 8000
          name: metrics
        envFrom:
        - configMapRef:
            name: autoscaler-config
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        volumeMounts:
        - name: models
          mountPath: /models
          readOnly: true
        - name: config
          mountPath: /config
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: models-pvc
      - name: config
        configMap:
          name: autoscaler-config
      livenessProbe:
        httpGet:
          path: /health
          port: 8000
        initialDelaySeconds: 30
        periodSeconds: 10
      readinessProbe:
        httpGet:
          path: /health
          port: 8000
        initialDelaySeconds: 5
        periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: intelligent-autoscaler-service
  namespace: $NAMESPACE
  labels:
    app: intelligent-autoscaler
spec:
  selector:
    app: intelligent-autoscaler
  ports:
  - port: 8000
    targetPort: 8000
    name: metrics
  type: ClusterIP
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: models-pvc
  namespace: $NAMESPACE
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
  storageClassName: standard
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: autoscaler-service-account
  namespace: $NAMESPACE
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: autoscaler-role
rules:
- apiGroups: [""]
  resources: ["pods", "services", "endpoints"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch", "update", "patch"]
- apiGroups: ["autoscaling"]
  resources: ["horizontalpodautoscalers", "verticalpodautoscalers"]
  verbs: ["get", "list", "watch", "update", "patch"]
- apiGroups: ["metrics.k8s.io"]
  resources: ["pods", "nodes"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: autoscaler-role-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: autoscaler-role
subjects:
- kind: ServiceAccount
  name: autoscaler-service-account
  namespace: $NAMESPACE
EOF
    
    log_info "Intelligent autoscaler deployed successfully"
}

# Deploy cost optimizer
deploy_cost_optimizer() {
    log_info "Deploying cost optimizer..."
    
    cat <<EOF | $KUBECTL apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cost-optimizer
  namespace: $NAMESPACE
  labels:
    app: cost-optimizer
    component: cost-optimization
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cost-optimizer
  template:
    metadata:
      labels:
        app: cost-optimizer
        component: cost-optimization
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8001"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: autoscaler-service-account
      containers:
      - name: cost-optimizer
        image: flavorsnap/cost-optimizer:latest
        ports:
        - containerPort: 8001
          name: metrics
        env:
        - name: PROMETHEUS_URL
          value: "http://prometheus-service:9090"
        - name: COST_OPTIMIZATION_INTERVAL
          value: "300"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: cost-optimizer-service
  namespace: $NAMESPACE
  labels:
    app: cost-optimizer
spec:
  selector:
    app: cost-optimizer
  ports:
  - port: 8001
    targetPort: 8001
    name: metrics
  type: ClusterIP
EOF
    
    log_info "Cost optimizer deployed successfully"
}

# Deploy scaling policies manager
deploy_scaling_policies() {
    log_info "Deploying scaling policies manager..."
    
    cat <<EOF | $KUBECTL apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scaling-policies-manager
  namespace: $NAMESPACE
  labels:
    app: scaling-policies-manager
    component: policy-management
spec:
  replicas: 1
  selector:
    matchLabels:
      app: scaling-policies-manager
  template:
    metadata:
      labels:
        app: scaling-policies-manager
        component: policy-management
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8002"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: autoscaler-service-account
      containers:
      - name: policies-manager
        image: flavorsnap/scaling-policies-manager:latest
        ports:
        - containerPort: 8002
          name: metrics
        env:
        - name: POLICIES_CONFIG_PATH
          value: "/config/policies.yaml"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
        volumeMounts:
        - name: policies-config
          mountPath: /config
        livenessProbe:
          httpGet:
            path: /health
            port: 8002
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8002
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: policies-config
        configMap:
          name: scaling-policies-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: scaling-policies-config
  namespace: $NAMESPACE
data:
  policies.yaml: |
    policies:
      frontend-critical:
        component: frontend
        policy_type: threshold_based
        min_replicas: 2
        max_replicas: 20
        default_replicas: 3
        resource_priority: high
        thresholds:
          - metric: cpu_utilization
            operator: ">"
            value: 80.0
            duration: 60
            cooldown: 120
          - metric: memory_utilization
            operator: ">"
            value: 85.0
            duration: 60
            cooldown: 180
        enabled: true
      backend-ml:
        component: backend
        policy_type: predictive
        min_replicas: 2
        max_replicas: 10
        default_replicas: 3
        resource_priority: critical
        thresholds:
          - metric: cpu_utilization
            operator: ">"
            value: 75.0
            duration: 45
            cooldown: 90
          - metric: ml_queue_length
            operator: ">"
            value: 100.0
            duration: 30
            cooldown: 60
        enabled: true
---
apiVersion: v1
kind: Service
metadata:
  name: scaling-policies-manager-service
  namespace: $NAMESPACE
  labels:
    app: scaling-policies-manager
spec:
  selector:
    app: scaling-policies-manager
  ports:
  - port: 8002
    targetPort: 8002
    name: metrics
  type: ClusterIP
EOF
    
    log_info "Scaling policies manager deployed successfully"
}

# Setup network policies
setup_network_policies() {
    log_info "Setting up network policies..."
    
    cat <<EOF | $KUBECTL apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: autoscaler-netpol
  namespace: $NAMESPACE
spec:
  podSelector:
    matchLabels:
      component: autoscaling
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: TCP
      port: 8080
    - protocol: TCP
      port: 9090
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: TCP
      port: 8080
    - protocol: TCP
      port: 9090
    - protocol: TCP
      port: 443
    - protocol: UDP
      port: 53
EOF
    
    log_info "Network policies configured"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying auto-scaling deployment..."
    
    # Check pods
    log_info "Checking pod status..."
    $KUBECTL get pods -l component=autoscaling -n $NAMESPACE
    
    # Check services
    log_info "Checking services..."
    $KUBECTL get services -l component=autoscaling -n $NAMESPACE
    
    # Check HPAs
    log_info "Checking Horizontal Pod Autoscalers..."
    $KUBECTL get hpa -n $NAMESPACE
    
    # Check VPAs
    log_info "Checking Vertical Pod Autoscalers..."
    $KUBECTL get vpa -n $NAMESPACE
    
    # Test autoscaler endpoints
    log_info "Testing autoscaler endpoints..."
    
    # Get service IPs
    AUTOSCALER_IP=$($KUBECTL get service intelligent-autoscaler-service -n $NAMESPACE -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "")
    COST_OPTIMIZER_IP=$($KUBECTL get service cost-optimizer-service -n $NAMESPACE -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "")
    POLICIES_IP=$($KUBECTL get service scaling-policies-manager-service -n $NAMESPACE -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "")
    
    if [ -n "$AUTOSCALER_IP" ]; then
        if curl -f -s "http://$AUTOSCALER_IP:8000/health" > /dev/null; then
            log_info "Intelligent autoscaler health check passed"
        else
            log_warn "Intelligent autoscaler health check failed"
        fi
    fi
    
    if [ -n "$COST_OPTIMIZER_IP" ]; then
        if curl -f -s "http://$COST_OPTIMIZER_IP:8001/health" > /dev/null; then
            log_info "Cost optimizer health check passed"
        else
            log_warn "Cost optimizer health check failed"
        fi
    fi
    
    if [ -n "$POLICIES_IP" ]; then
        if curl -f -s "http://$POLICIES_IP:8002/health" > /dev/null; then
            log_info "Scaling policies manager health check passed"
        else
            log_warn "Scaling policies manager health check failed"
        fi
    fi
    
    log_info "Deployment verification completed"
}

# Show deployment status
show_status() {
    log_info "Auto-Scaling Deployment Status:"
    echo "=============================="
    
    echo "Namespace: $NAMESPACE"
    echo "Intelligent Autoscaler:"
    $KUBECTL get deployment intelligent-autoscaler -n $NAMESPACE -o wide
    echo ""
    echo "Cost Optimizer:"
    $KUBECTL get deployment cost-optimizer -n $NAMESPACE -o wide
    echo ""
    echo "Scaling Policies Manager:"
    $KUBECTL get deployment scaling-policies-manager -n $NAMESPACE -o wide
    echo ""
    echo "Horizontal Pod Autoscalers:"
    $KUBECTL get hpa -n $NAMESPACE
    echo ""
    echo "Vertical Pod Autoscalers:"
    $KUBECTL get vpa -n $NAMESPACE
    echo ""
    echo "Services:"
    $KUBECTL get services -l component=autoscaling -n $NAMESPACE
    echo ""
    
    # Get service URLs
    AUTOSCALER_IP=$($KUBECTL get service intelligent-autoscaler-service -n $NAMESPACE -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "")
    COST_OPTIMIZER_IP=$($KUBECTL get service cost-optimizer-service -n $NAMESPACE -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "")
    POLICIES_IP=$($KUBECTL get service scaling-policies-manager-service -n $NAMESPACE -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "")
    
    echo "Service URLs:"
    if [ -n "$AUTOSCALER_IP" ]; then
        echo "  Intelligent Autoscaler: http://$AUTOSCALER_IP:8000"
        echo "  Autoscaler Metrics: http://$AUTOSCALER_IP:8000/metrics"
    fi
    if [ -n "$COST_OPTIMIZER_IP" ]; then
        echo "  Cost Optimizer: http://$COST_OPTIMIZER_IP:8001"
        echo "  Cost Metrics: http://$COST_OPTIMIZER_IP:8001/metrics"
    fi
    if [ -n "$POLICIES_IP" ]; then
        echo "  Policies Manager: http://$POLICIES_IP:8002"
        echo "  Policies API: http://$POLICIES_IP:8002/policies"
    fi
}

# Cleanup function
cleanup() {
    log_warn "Cleaning up auto-scaling deployment..."
    
    $KUBECTL delete -f k8s/autoscaling/horizontal-pod-autoscaler.yaml -n $NAMESPACE --ignore-not-found=true
    $KUBECTL delete -f k8s/autoscaling/vertical-pod-autoscaler.yaml -n $NAMESPACE --ignore-not-found=true
    $KUBECTL delete -f k8s/autoscaling/cluster-autoscaler.yaml -n kube-system --ignore-not-found=true
    $KUBECTL delete -f monitoring/scaling/scaling-metrics.yaml -n $NAMESPACE --ignore-not-found=true
    
    # Delete deployed components
    $KUBECTL delete deployment intelligent-autoscaler -n $NAMESPACE --ignore-not-found=true
    $KUBECTL delete deployment cost-optimizer -n $NAMESPACE --ignore-not-found=true
    $KUBECTL delete deployment scaling-policies-manager -n $NAMESPACE --ignore-not-found=true
    $KUBECTL delete service intelligent-autoscaler-service -n $NAMESPACE --ignore-not-found=true
    $KUBECTL delete service cost-optimizer-service -n $NAMESPACE --ignore-not-found=true
    $KUBECTL delete service scaling-policies-manager-service -n $NAMESPACE --ignore-not-found=true
    $KUBECTL delete configmap autoscaler-config -n $NAMESPACE --ignore-not-found=true
    $KUBECTL delete configmap scaling-policies-config -n $NAMESPACE --ignore-not-found=true
    $KUBECTL delete pvc models-pvc -n $NAMESPACE --ignore-not-found=true
    $KUBECTL delete serviceaccount autoscaler-service-account -n $NAMESPACE --ignore-not-found=true
    $KUBECTL delete clusterrole autoscaler-role --ignore-not-found=true
    $KUBECTL delete clusterrolebinding autoscaler-role-binding --ignore-not-found=true
    $KUBECTL delete networkpolicy autoscaler-netpol -n $NAMESPACE --ignore-not-found=true
    
    log_info "Cleanup completed"
}

# Main function
main() {
    case "${1:-deploy}" in
        "deploy")
            check_prerequisites
            create_namespace
            deploy_metrics_server
            deploy_autoscaling
            deploy_monitoring
            deploy_intelligent_autoscaler
            deploy_cost_optimizer
            deploy_scaling_policies
            setup_network_policies
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
            echo "  deploy   - Deploy complete intelligent auto-scaling infrastructure"
            echo "  cleanup  - Remove all deployed auto-scaling resources"
            echo "  status   - Show current deployment status"
            echo "  verify   - Verify deployment is working correctly"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
