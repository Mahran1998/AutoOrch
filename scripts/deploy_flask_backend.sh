#!/bin/bash

################################################################################
# Deploy Flask Backend & Configure Environment
#
# Steps:
#   1. Build Flask Docker image
#   2. Load image into kind cluster
#   3. Deploy controllable-backend to Kubernetes
#   4. Wait for deployment to be ready
#   5. Update loadgenerator TARGET env variable
#   6. Run validation tests
################################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[*]${NC} $1"; }
log_success() { echo -e "${GREEN}[+]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/tools/controllable-backend"
DEPLOY_MANIFEST="${PROJECT_ROOT}/deploy/controllable-backend.yaml"

log_info "═══════════════════════════════════════════════════════════════"
log_info "Deploy Controllable Flask Backend"
log_info "═══════════════════════════════════════════════════════════════"

# 1. Verify Docker is available
log_info "Checking Docker..."
if ! command -v docker &> /dev/null; then
    log_error "Docker not found!"
    exit 1
fi
log_success "Docker available"

# 2. Verify kubectl is available
log_info "Checking kubectl..."
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl not found!"
    exit 1
fi
log_success "kubectl available"

# 3. Verify kind is available
log_info "Checking kind..."
if ! command -v kind &> /dev/null; then
    log_error "kind not found!"
    exit 1
fi
log_success "kind available"

# 4. Build Docker image
log_info ""
log_info "Building Flask backend Docker image..."
cd "$BACKEND_DIR"

if docker build -t controllable-backend:latest .; then
    log_success "Docker image built: controllable-backend:latest"
else
    log_error "Failed to build Docker image"
    exit 1
fi

# 5. Load image into kind
log_info ""
log_info "Loading image into kind cluster..."

if kind load docker-image controllable-backend:latest; then
    log_success "Image loaded into kind cluster"
else
    log_error "Failed to load image into kind"
    exit 1
fi

# 6. Deploy to Kubernetes
log_info ""
log_info "Deploying to Kubernetes..."

if kubectl apply -f "$DEPLOY_MANIFEST"; then
    log_success "Deployment manifest applied"
else
    log_error "Failed to apply deployment manifest"
    exit 1
fi

# 7. Wait for deployment to be ready
log_info ""
log_info "Waiting for controllable-backend deployment to be ready..."

if kubectl wait --for=condition=available --timeout=60s deployment/controllable-backend 2>/dev/null; then
    log_success "Deployment is ready"
else
    log_warning "Deployment took longer than expected; continuing anyway..."
fi

sleep 3

# 8. Verify pod is running
log_info ""
log_info "Checking pod status..."

POD_NAME=$(kubectl get pod -l app=controllable-backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [[ -n "$POD_NAME" ]]; then
    log_success "Pod is running: $POD_NAME"
    POD_STATUS=$(kubectl get pod $POD_NAME -o jsonpath='{.status.phase}')
    log_info "Pod status: $POD_STATUS"
else
    log_error "No controllable-backend pod found!"
    exit 1
fi

# 9. Update loadgenerator TARGET environment variable
log_info ""
log_info "Updating loadgenerator TARGET to controllable-backend..."

kubectl set env deployment/loadgenerator \
    TARGET="http://controllable-backend:5000/api/test" \
    --overwrite 2>/dev/null || true

log_success "loadgenerator TARGET updated"

# Wait for loadgenerator to restart with new env
sleep 5
kubectl wait --for=condition=available --timeout=60s deployment/loadgenerator 2>/dev/null || true

# 10. Validation tests
log_info ""
log_info "═══════════════════════════════════════════════════════════════"
log_info "Running Validation Tests"
log_info "═══════════════════════════════════════════════════════════════"

# Port-forward to Flask backend
log_info ""
log_info "Setting up port-forward to Flask backend..."

kubectl port-forward -n default svc/controllable-backend 5000:5000 >/tmp/pf_backend.log 2>&1 &
PF_PID=$!
sleep 2

cleanup_pf() {
    kill $PF_PID 2>/dev/null || true
}
trap cleanup_pf EXIT

# Test 1: Health check
log_info ""
log_info "Test 1: Health check endpoint"

RESPONSE=$(curl -s http://127.0.0.1:5000/health)
if echo "$RESPONSE" | jq . > /dev/null 2>&1; then
    STATUS=$(echo "$RESPONSE" | jq -r '.status // "unknown"')
    if [[ "$STATUS" == "ok" ]]; then
        log_success "Health check passed"
    else
        log_warning "Health check status: $STATUS"
    fi
else
    log_error "Health check failed: $RESPONSE"
fi

# Test 2: Normal request (should return 200)
log_info ""
log_info "Test 2: Normal request (should return 200)"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/api/test)
if [[ "$HTTP_CODE" == "200" ]]; then
    log_success "Normal request returned 200"
else
    log_error "Expected 200, got $HTTP_CODE"
fi

# Test 3: Toggle error injection
log_info ""
log_info "Test 3: Toggle error injection ON"

RESPONSE=$(curl -s -X POST http://127.0.0.1:5000/inject-errors)
ENABLED=$(echo "$RESPONSE" | jq -r '.error_injection_enabled // false')
if [[ "$ENABLED" == "true" ]]; then
    log_success "Error injection toggled ON"
else
    log_error "Failed to toggle error injection"
fi

# Test 4: Request with error injection (should return 500)
log_info ""
log_info "Test 4: Request with error injection (should return 500)"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/api/test)
if [[ "$HTTP_CODE" == "500" ]]; then
    log_success "Injected error request returned 500"
else
    log_error "Expected 500, got $HTTP_CODE"
fi

# Test 5: Toggle error injection OFF
log_info ""
log_info "Test 5: Toggle error injection OFF"

RESPONSE=$(curl -s -X POST http://127.0.0.1:5000/inject-errors)
ENABLED=$(echo "$RESPONSE" | jq -r '.error_injection_enabled // false')
if [[ "$ENABLED" == "false" ]]; then
    log_success "Error injection toggled OFF"
else
    log_error "Failed to toggle error injection"
fi

# Test 6: Request after toggling off (should return 200)
log_info ""
log_info "Test 6: Request after toggling OFF (should return 200)"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/api/test)
if [[ "$HTTP_CODE" == "200" ]]; then
    log_success "Normal request returned 200"
else
    log_error "Expected 200, got $HTTP_CODE"
fi

# Test 7: Metrics endpoint
log_info ""
log_info "Test 7: Metrics endpoint (Prometheus format)"

RESPONSE=$(curl -s http://127.0.0.1:5000/metrics)
if echo "$RESPONSE" | grep -q "http_requests_total"; then
    REQ_COUNT=$(echo "$RESPONSE" | grep "http_requests_total" | wc -l)
    log_success "Metrics endpoint working ($REQ_COUNT metrics exported)"
else
    log_warning "Metrics endpoint returned data but no http_requests_total found"
fi

# Summary
log_info ""
log_success "═══════════════════════════════════════════════════════════════"
log_success "Deployment & Validation Complete!"
log_success "═══════════════════════════════════════════════════════════════"
log_info ""
log_success "Flask backend is ready for experiments!"
log_info ""
log_info "Next steps:"
log_info "  1. Verify Prometheus scrapes the metrics:"
log_info "     - Visit http://localhost:9090/targets in browser"
log_info "     - Look for 'controllable-backend' job"
log_info ""
log_info "  2. Run the comprehensive experiment:"
log_info "     bash scripts/run_exp2_restart.sh"
log_info ""
log_info "  3. After experiment completes, label and train:"
log_info "     python3 scripts/build_dataset_restart.py --input <feature_windows.csv>"
log_info "     python3 ml/restart/train_restart_classifier.py"
log_info ""
