#!/bin/bash

# Advanced Configuration Management Deployment Script
# Deploys comprehensive configuration management with secrets management and environment control

set -e

# Configuration
NAMESPACE="flavorsnap-config"
CONFIG_DIR="config"
SECRETS_DIR="config/secrets"
SCRIPT_DIR="scripts/config"

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
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check helm
    if ! command -v helm &> /dev/null; then
        log_error "helm is not installed or not in PATH"
        exit 1
    fi
    
    # Check yq
    if ! command -v yq &> /dev/null; then
        log_warn "yq is not installed. Some features may not work properly"
    fi
    
    # Check cluster access
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot access Kubernetes cluster"
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

# Create namespace
create_namespace() {
    log_info "Creating namespace: $NAMESPACE"
    
    if kubectl get namespace $NAMESPACE &> /dev/null; then
        log_warn "Namespace $NAMESPACE already exists"
    else
        kubectl create namespace $NAMESPACE
        log_info "Namespace $NAMESPACE created"
    fi
}

# Deploy configuration manager
deploy_config_manager() {
    log_info "Deploying configuration manager..."
    
    # Create ConfigMap for configuration
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-manager-config
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-config
    component: config-manager
data:
  config.yaml: |
    # Configuration Manager Settings
    version: "1.0"
    
    environments:
      - development
      - staging
      - production
    
    validation:
      enabled: true
      strict_mode: false
      auto_fix: true
      validate_on_load: true
    
    hot_reload:
      enabled: true
      watch_interval: "5s"
      debounce_delay: "1s"
    
    version_control:
      enabled: true
      track_changes: true
      backup_configs: true
      max_versions: 50
    
    security:
      encryption_enabled: true
      access_control: true
      audit_logging: true
    
    monitoring:
      enabled: true
      metrics_port: 9093
      health_check_interval: "30s"
EOF
    
    # Deploy configuration manager
    cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: config-manager
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-config
    component: config-manager
spec:
  replicas: 2
  selector:
    matchLabels:
      app: flavorsnap-config
      component: config-manager
  template:
    metadata:
      labels:
        app: flavorsnap-config
        component: config-manager
    spec:
      serviceAccountName: config-manager
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: config-manager
        image: flavorsnap/config-manager:latest
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 9093
          name: metrics
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: CONFIG_DIR
          value: "/app/config"
        - name: SECRETS_DIR
          value: "/app/secrets"
        - name: REDIS_HOST
          value: "redis.config.svc.cluster.local"
        - name: REDIS_PORT
          value: "6379"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        volumeMounts:
        - name: config-storage
          mountPath: /app/config
          readOnly: true
        - name: secrets-storage
          mountPath: /app/secrets
          readOnly: true
        - name: config-volume
          mountPath: /app/config-data
          readOnly: true
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
      volumes:
      - name: config-storage
        persistentVolumeClaim:
          claimName: config-storage-pvc
      - name: secrets-storage
        persistentVolumeClaim:
          claimName: secrets-storage-pvc
      - name: config-volume
        configMap:
          name: config-manager-config
      nodeSelector:
        node-role.kubernetes.io/worker: "true"
EOF
    
    # Create service
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: config-manager
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-config
    component: config-manager
spec:
  selector:
    app: flavorsnap-config
    component: config-manager
  ports:
  - name: http
    port: 8080
    targetPort: 8080
    protocol: TCP
  - name: metrics
    port: 9093
    targetPort: 9093
    protocol: TCP
  type: ClusterIP
EOF
    
    log_info "Configuration manager deployed"
}

# Deploy Redis for caching
deploy_redis() {
    log_info "Deploying Redis for configuration caching..."
    
    # Deploy Redis
    cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-config
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-config
    component: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: flavorsnap-config
      component: redis
  template:
    metadata:
      labels:
        app: flavorsnap-config
        component: redis
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 999
        fsGroup: 999
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
          name: redis
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: redis-config-password
              key: password
        command:
        - redis-server
        - --requirepass
        - \$(REDIS_PASSWORD)
        - --appendonly
        - "yes"
        - --maxmemory
        - "256mb"
        - --maxmemory-policy
        - "allkeys-lru"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
        volumeMounts:
        - name: redis-data
          mountPath: /data
        livenessProbe:
          exec:
            command:
            - redis-cli
            - -a
            - \$(REDIS_PASSWORD)
            - ping
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - redis-cli
            - -a
            - \$(REDIS_PASSWORD)
            - ping
          initialDelaySeconds: 5
          periodSeconds: 5
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: false
          capabilities:
            drop:
            - ALL
      volumes:
      - name: redis-data
        persistentVolumeClaim:
          claimName: redis-config-data-pvc
EOF
    
    # Create Redis service
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: redis-config
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-config
    component: redis
spec:
  selector:
    app: flavorsnap-config
    component: redis
  ports:
  - name: redis
    port: 6379
    targetPort: 6379
    protocol: TCP
  type: ClusterIP
EOF
    
    log_info "Redis deployed for configuration caching"
}

# Create secrets
create_secrets() {
    log_info "Creating configuration secrets..."
    
    # Create Redis password
    REDIS_PASSWORD=$(openssl rand -base64 32)
    
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: redis-config-password
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-config
    component: redis
type: Opaque
data:
  password: $(echo -n "$REDIS_PASSWORD" | base64)
EOF
    
    # Create master encryption key
    MASTER_KEY=$(openssl rand -base64 32)
    
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: master-encryption-key
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-config
    component: encryption
type: Opaque
data:
  key: $(echo -n "$MASTER_KEY" | base64)
EOF
    
    # Create application secrets
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: app-config-secrets
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-config
    component: application
type: Opaque
data:
  jwt-secret: $(echo -n "production-jwt-secret-key-$(date +%s)" | base64)
  database-password: $(echo -n "secure-db-password-$(date +%s)" | base64)
  api-key: $(echo -n "secure-api-key-$(date +%s)" | base64)
  encryption-key: $(echo -n "app-encryption-key-$(date +%s)" | base64)
EOF
    
    log_info "Configuration secrets created"
}

# Create persistent volumes
create_persistent_volumes() {
    log_info "Creating persistent volumes..."
    
    # Config storage PVC
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: config-storage-pvc
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-config
    component: storage
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
  storageClassName: standard
EOF
    
    # Secrets storage PVC
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: secrets-storage-pvc
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-config
    component: storage
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard
EOF
    
    # Redis data PVC
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-config-data-pvc
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-config
    component: redis
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 2Gi
  storageClassName: standard
EOF
    
    log_info "Persistent volumes created"
}

# Setup RBAC
setup_rbac() {
    log_info "Setting up RBAC..."
    
    # ServiceAccount
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: config-manager
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-config
    component: rbac
EOF
    
    # Role
    cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: config-manager-role
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-config
    component: rbac
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "create", "update", "patch"]
- apiGroups: ["batch"]
  resources: ["jobs", "cronjobs"]
  verbs: ["get", "list", "create", "update", "patch", "delete"]
EOF
    
    # RoleBinding
    cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: config-manager-binding
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-config
    component: rbac
subjects:
- kind: ServiceAccount
  name: config-manager
  namespace: $NAMESPACE
roleRef:
  kind: Role
  name: config-manager-role
  apiGroup: rbac.authorization.k8s.io
EOF
    
    log_info "RBAC setup completed"
}

# Setup monitoring
setup_monitoring() {
    log_info "Setting up monitoring..."
    
    # ServiceMonitor
    cat <<EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: config-manager-metrics
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-config
    component: monitoring
spec:
  selector:
    matchLabels:
      app: flavorsnap-config
      component: config-manager
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
    scrapeTimeout: 10s
EOF
    
    # PrometheusRules
    cat <<EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: config-alerts
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-config
    component: monitoring
spec:
  groups:
  - name: config.rules
    rules:
  - alert: ConfigManagerDown
    expr: up{job="config-manager"} == 0
    for: 1m
    labels:
      severity: critical
      service: config-manager
    annotations:
      summary: "Configuration manager is down"
      description: "Configuration manager has been down for more than 1 minute"
  
  - alert: ConfigValidationFailed
    expr: rate(config_validation_errors_total[5m]) > 0
    for: 2m
    labels:
      severity: warning
      service: config-manager
    annotations:
      summary: "Configuration validation failures"
      description: "Configuration validation failures detected: {{ $value }} errors per minute"
  
  - alert: ConfigReloadFailed
    expr: rate(config_reloads_total{success="false"}[5m]) > 0
    for: 1m
    labels:
      severity: warning
      service: config-manager
    annotations:
      summary: "Configuration reload failures"
      description: "Configuration reload failures detected: {{ $value }} failures per minute"
EOF
    
    log_info "Monitoring setup completed"
}

# Setup network policies
setup_network_policies() {
    log_info "Setting up network policies..."
    
    cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: config-network-policy
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-config
    component: security
spec:
  podSelector:
    matchLabels:
      app: flavorsnap-config
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
      port: 8080
    - protocol: TCP
      port: 9093
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
      port: 6379
    - protocol: TCP
      port: 443
    - protocol: UDP
      port: 53
EOF
    
    log_info "Network policies setup completed"
}

# Deploy configuration utilities
deploy_utilities() {
    log_info "Deploying configuration utilities..."
    
    # Config validator CronJob
    cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: CronJob
metadata:
  name: config-validator
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-config
    component: validator
spec:
  schedule: "0 */6 * * *"  # Every 6 hours
  jobTemplate:
    spec:
      template:
        metadata:
          labels:
            app: flavorsnap-config
            component: validator
        spec:
          serviceAccountName: config-manager
          restartPolicy: OnFailure
          containers:
          - name: validator
            image: flavorsnap/config-manager:latest
            command:
            - python
            - -c
            - |
              from config_manager import config_manager
              import logging
              
              logging.basicConfig(level=logging.INFO)
              logger = logging.getLogger(__name__)
              
              # Validate all configurations
              try:
                  health = config_manager.health_check()
                  if health['healthy']:
                      logger.info("Configuration validation passed")
                  else:
                      logger.error(f"Configuration validation failed: {health['issues']}")
              except Exception as e:
                  logger.error(f"Configuration validation error: {e}")
            env:
            - name: ENVIRONMENT
              value: "production"
            - name: MASTER_ENCRYPTION_KEY
              valueFrom:
                secretKeyRef:
                  name: master-encryption-key
                  key: key
            resources:
              requests:
                memory: "128Mi"
                cpu: "100m"
              limits:
                memory: "256Mi"
                cpu: "200m"
            securityContext:
              allowPrivilegeEscalation: false
              readOnlyRootFilesystem: true
              capabilities:
                drop:
                - ALL
EOF
    
    # Config backup CronJob
    cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: CronJob
metadata:
  name: config-backup
  namespace: $NAMESPACE
  labels:
    app: flavorsnap-config
    component: backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        metadata:
          labels:
            app: flavorsnap-config
            component: backup
        spec:
          serviceAccountName: config-manager
          restartPolicy: OnFailure
          containers:
          - name: backup
            image: flavorsnap/config-manager:latest
            command:
            - python
            - -c
            - |
              from config_manager import config_manager
              import json
              import os
              from datetime import datetime
              from pathlib import Path
              import logging
              
              logging.basicConfig(level=logging.INFO)
              logger = logging.getLogger(__name__)
              
              # Export configuration
              config_data = config_manager.export_config(format='yaml', include_secrets=False)
              versions = config_manager.get_versions()
              changes = config_manager.get_change_history()
              
              # Create backup
              backup_data = {
                  'timestamp': datetime.utcnow().isoformat(),
                  'environment': os.getenv('ENVIRONMENT'),
                  'config': config_data,
                  'versions': [v.__dict__ for v in versions],
                  'recent_changes': [c.__dict__ for c in changes[-50:]]
              }
              
              # Save backup
              backup_dir = Path('/app/backups')
              backup_dir.mkdir(exist_ok=True)
              
              backup_file = backup_dir / f'config_backup_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json'
              
              with open(backup_file, 'w') as f:
                  json.dump(backup_data, f, indent=2, default=str)
              
              logger.info(f"Configuration backup created: {backup_file}")
            env:
            - name: ENVIRONMENT
              value: "production"
            - name: MASTER_ENCRYPTION_KEY
              valueFrom:
                secretKeyRef:
                  name: master-encryption-key
                  key: key
            volumeMounts:
            - name: backup-storage
              mountPath: /app/backups
            resources:
              requests:
                memory: "128Mi"
                cpu: "100m"
              limits:
                memory: "256Mi"
                cpu: "200m"
            securityContext:
              allowPrivilegeEscalation: false
              readOnlyRootFilesystem: true
              capabilities:
                drop:
                - ALL
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: config-storage-pvc
EOF
    
    log_info "Configuration utilities deployed"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying configuration management deployment..."
    
    # Wait for pods to be ready
    log_info "Waiting for pods to be ready..."
    kubectl wait --for=condition=available pod -l app=flavorsnap-config,component=config-manager -n $NAMESPACE --timeout=300s
    kubectl wait --for=condition=ready pod -l app=flavorsnap-config,component=config-manager -n $NAMESPACE --timeout=300s
    kubectl wait --for=condition=available pod -l app=flavorsnap-config,component=redis -n $NAMESPACE --timeout=300s
    kubectl wait --for=condition=ready pod -l app=flavorsnap-config,component=redis -n $NAMESPACE --timeout=300s
    
    # Check services
    log_info "Checking services..."
    kubectl get services -n $NAMESPACE -l app=flavorsnap-config
    
    # Check persistent volumes
    log_info "Checking persistent volumes..."
    kubectl get pvc -n $NAMESPACE
    
    # Test configuration manager API
    log_info "Testing configuration manager API..."
    CONFIG_MANAGER_POD=$(kubectl get pods -l app=flavorsnap-config,component=config-manager -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}')
    
    if [ -n "$CONFIG_MANAGER_POD" ]; then
        kubectl exec -n $NAMESPACE $CONFIG_MANAGER_POD -- curl -s http://localhost:8080/health || true
        log_info "Configuration manager health check completed"
    else
        log_warn "Configuration manager pod not found"
    fi
    
    log_info "Deployment verification completed"
}

# Show deployment status
show_status() {
    log_info "Configuration Management Deployment Status:"
    echo "=========================================="
    
    echo "Namespace: $NAMESPACE"
    echo "Configuration Manager:"
    kubectl get pods -l component=config-manager -n $NAMESPACE -o wide
    echo ""
    echo "Redis:"
    kubectl get pods -l component=redis -n $NAMESPACE -o wide
    echo ""
    echo "Services:"
    kubectl get services -n $NAMESPACE -l app=flavorsnap-config
    echo ""
    echo "Persistent Volumes:"
    kubectl get pvc -n $NAMESPACE
    echo ""
    
    # Get service URLs
    CONFIG_MANAGER_SERVICE=$(kubectl get service config-manager -n $NAMESPACE -o jsonpath='{.spec.clusterIP}')
    
    echo "Service URLs:"
    if [ -n "$CONFIG_MANAGER_SERVICE" ]; then
        echo "  Configuration Manager: http://$CONFIG_MANAGER_SERVICE:8080"
        echo "  Metrics: http://$CONFIG_MANAGER_SERVICE:9093/metrics"
    fi
    echo ""
}

# Cleanup function
cleanup() {
    log_warn "Cleaning up configuration management deployment..."
    
    kubectl delete namespace $NAMESPACE --ignore-not-found=true
    kubectl delete clusterrole config-manager-cluster-role --ignore-not-found=true
    kubectl delete clusterrolebinding config-manager-cluster-binding --ignore-not-found=true
    kubectl delete serviceaccount config-manager --ignore-not-found=true
    
    log_info "Cleanup completed"
}

# Scale components
scale_components() {
    local component=$1
    local replicas=$2
    
    log_info "Scaling $component to $replicas replicas..."
    
    case $component in
        config-manager)
            kubectl scale deployment config-manager -n $NAMESPACE --replicas=$replicas
            ;;
        redis)
            kubectl scale deployment redis-config -n $NAMESPACE --replicas=$replicas
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
            create_persistent_volumes
            create_secrets
            setup_rbac
            deploy_redis
            deploy_config_manager
            deploy_utilities
            setup_monitoring
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
        "scale")
            if [ -z "$2" ] || [ -z "$3" ]; then
                echo "Usage: $0 scale <component> <replicas>"
                echo "Components: config-manager, redis"
                exit 1
            fi
            scale_components "$2" "$3"
            ;;
        "verify")
            verify_deployment
            ;;
        *)
            echo "Usage: $0 {deploy|cleanup|status|scale|verify}"
            echo ""
            echo "Commands:"
            echo "  deploy   - Deploy complete configuration management system"
            echo "  cleanup  - Remove all configuration management components"
            echo "  status   - Show deployment status"
            echo "  scale    - Scale components"
            echo "  verify   - Verify deployment is working"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
