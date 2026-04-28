#!/usr/bin/env bash
# =============================================================================
# FlavorSnap Monitoring Setup Script
# =============================================================================
# Sets up the full monitoring stack:
#   - Prometheus + Alertmanager
#   - Grafana (with pre-provisioned dashboards and datasources)
#   - Elasticsearch + Logstash + Kibana (ELK)
#   - Filebeat (log shipper)
#   - Node Exporter + cAdvisor (system/container metrics)
#
# Usage:
#   bash scripts/setup_monitoring.sh [--dev|--prod] [--skip-elk]
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
MODE="${1:-dev}"
SKIP_ELK=false
COMPOSE_FILE="docker-compose.monitoring.yml"

for arg in "$@"; do
  case $arg in
    --prod)   MODE="prod" ;;
    --dev)    MODE="dev" ;;
    --skip-elk) SKIP_ELK=true ;;
  esac
done

echo "=============================================="
echo " FlavorSnap Monitoring Setup"
echo " Mode: $MODE"
echo " Skip ELK: $SKIP_ELK"
echo "=============================================="

# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker is required but not installed."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || command -v docker compose >/dev/null 2>&1 || {
  echo "ERROR: docker-compose is required but not installed."; exit 1;
}

# ---------------------------------------------------------------------------
# Directory structure
# ---------------------------------------------------------------------------
echo "[1/6] Creating directory structure..."
mkdir -p monitoring/grafana/provisioning/datasources
mkdir -p monitoring/grafana/provisioning/dashboards
mkdir -p monitoring/grafana/dashboards
mkdir -p prometheus
mkdir -p elasticsearch
mkdir -p logs

# ---------------------------------------------------------------------------
# Copy config files into monitoring/ if they don't already exist
# ---------------------------------------------------------------------------
echo "[2/6] Copying configuration files..."

copy_if_missing() {
  local src="$1" dst="$2"
  if [ ! -f "$dst" ]; then
    cp "$src" "$dst"
    echo "  Copied $src -> $dst"
  else
    echo "  Skipped (exists): $dst"
  fi
}

copy_if_missing "prometheus/prometheus.yml"   "monitoring/prometheus.yml"
copy_if_missing "prometheus/alert_rules.yml"  "monitoring/alert_rules.yml"
copy_if_missing "grafana/provisioning/datasources/prometheus.yaml" \
                "monitoring/grafana/provisioning/datasources/prometheus.yaml"
copy_if_missing "grafana/provisioning/dashboards/default.yaml" \
                "monitoring/grafana/provisioning/dashboards/default.yaml"
copy_if_missing "grafana/dashboards/flavorsnap_overview.json" \
                "monitoring/grafana/dashboards/flavorsnap_overview.json"

# ---------------------------------------------------------------------------
# Python dependencies
# ---------------------------------------------------------------------------
echo "[3/6] Installing Python monitoring dependencies..."
if command -v pip >/dev/null 2>&1; then
  pip install --quiet \
    prometheus-client==0.20.0 \
    psutil==5.9.8 \
    pyyaml==6.0.1
  echo "  Python dependencies installed."
else
  echo "  WARNING: pip not found — skipping Python dependency install."
fi

# ---------------------------------------------------------------------------
# Start monitoring stack
# ---------------------------------------------------------------------------
echo "[4/6] Starting monitoring stack..."

COMPOSE_CMD="docker-compose"
if ! command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
fi

if [ "$SKIP_ELK" = true ]; then
  echo "  Starting Prometheus + Grafana + Alertmanager only..."
  $COMPOSE_CMD -f monitoring/docker-compose.monitoring.yml \
    up -d prometheus grafana alertmanager node-exporter
else
  echo "  Starting full stack (including ELK)..."
  $COMPOSE_CMD -f monitoring/docker-compose.monitoring.yml up -d
fi

# ---------------------------------------------------------------------------
# Wait for services
# ---------------------------------------------------------------------------
echo "[5/6] Waiting for services to become healthy..."

wait_for_url() {
  local url="$1" name="$2" retries="${3:-30}"
  local i=0
  while [ $i -lt $retries ]; do
    if curl -sf "$url" >/dev/null 2>&1; then
      echo "  ✓ $name is ready"
      return 0
    fi
    sleep 2
    i=$((i + 1))
  done
  echo "  ✗ $name did not become ready in time (continuing anyway)"
  return 0
}

wait_for_url "http://localhost:9090/-/ready"  "Prometheus"
wait_for_url "http://localhost:3001/api/health" "Grafana"
wait_for_url "http://localhost:9093/-/ready"  "Alertmanager"

if [ "$SKIP_ELK" = false ]; then
  wait_for_url "http://localhost:9200/_cluster/health" "Elasticsearch" 60
  wait_for_url "http://localhost:5601/api/status"      "Kibana"        60
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "[6/6] Setup complete!"
echo ""
echo "  Service         URL"
echo "  --------------- --------------------------------"
echo "  Prometheus      http://localhost:9090"
echo "  Grafana         http://localhost:3001  (admin / admin123)"
echo "  Alertmanager    http://localhost:9093"
echo "  Node Exporter   http://localhost:9100/metrics"
if [ "$SKIP_ELK" = false ]; then
echo "  Elasticsearch   http://localhost:9200"
echo "  Kibana          http://localhost:5601"
fi
echo ""
echo "  FlavorSnap metrics endpoint: http://localhost:8000/metrics"
echo "  FlavorSnap dashboard:        http://localhost:8000/monitoring/dashboard"
echo ""
echo "Next steps:"
echo "  1. Open Grafana and verify the 'FlavorSnap Overview' dashboard is loaded."
echo "  2. Update alertmanager.yml with your SMTP / Slack credentials."
echo "  3. Review alert thresholds in prometheus/alert_rules.yml."
echo "  4. For production, set GF_SECURITY_ADMIN_PASSWORD via environment variable."
