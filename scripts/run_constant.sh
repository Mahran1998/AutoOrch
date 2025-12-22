#!/usr/bin/env bash
set -euo pipefail

# Usage:
# ./run_constant.sh --rps 100 --concurrency 25 --duration 300 --result-dir /path/to/resultdir --interval 15
# Requires: kubectl access to cluster + Prometheus port-forward running at localhost:9090

RPS=50
CONCURRENCY=25
DURATION=300
INTERVAL=15
RESULT_DIR=""
PROM_HOST="http://localhost:9090"
LOADGEN_SVC="loadgenerator-metrics.default.svc.cluster.local:8080"

while [ $# -gt 0 ]; do
  case "$1" in
    --rps) RPS="$2"; shift 2;;
    --concurrency) CONCURRENCY="$2"; shift 2;;
    --duration) DURATION="$2"; shift 2;;
    --interval) INTERVAL="$2"; shift 2;;
    --result-dir) RESULT_DIR="$2"; shift 2;;
    --prom) PROM_HOST="$2"; shift 2;;
    *) echo "Unknown arg $1"; exit 1;;
  esac
done

if [ -z "$RESULT_DIR" ]; then
  echo "ERROR: --result-dir is required"
  exit 1
fi

mkdir -p "$RESULT_DIR"/{csv,logs,meta}

# record metadata snapshot
cat > "$RESULT_DIR/meta/run_info.txt" <<META
start_time: $(date --iso-8601=seconds)
rps: $RPS
concurrency: $CONCURRENCY
duration: $DURATION
interval: $INTERVAL
prom_host: $PROM_HOST
loadgen_service: $LOADGEN_SVC
pod_snapshot: $(kubectl get pods -o wide --show-labels | head -n 20)
META

# Set load generator to desired RPS & concurrency using in-cluster curl (no port-forward)
echo "Setting loadgen RPS=$RPS concurrency=$CONCURRENCY ..."
kubectl run -n default --rm -it --restart=Never curlctrl --image=radial/busyboxplus:curl --command -- \
  sh -c "curl -sS -X POST -H 'Content-Type: application/json' -d '{\"rps\":$RPS,\"concurrency\":$CONCURRENCY}' http://$LOADGEN_SVC/control" >/dev/null 2>&1 || true
echo "Loadgen updated."

# warm-up short sleep
sleep 3

# CSV header
CSV="$RESULT_DIR/csv/steady.csv"
echo "ts,requested_rps,requested_concurrency,observed_rps,p95_latency_seconds" > "$CSV"

END=$(( $(date +%s) + DURATION ))
while [ $(date +%s) -lt $END ]; do
  ts=$(date +%s)
  # query Prometheus for instant values (rate & p95)
  observed_rps=$(curl -sS --get "$PROM_HOST/api/v1/query" --data-urlencode "query=sum(rate(loadgen_requests_total[1m]))" | jq -r '.data.result[0].value[1] // "0"')
  p95=$(curl -sS --get "$PROM_HOST/api/v1/query" --data-urlencode 'query=histogram_quantile(0.95, sum(rate(loadgen_request_latency_seconds_bucket[1m])) by (le))' | jq -r '.data.result[0].value[1] // "NaN"')
  echo "${ts},${RPS},${CONCURRENCY},${observed_rps},${p95}" >> "$CSV"
  echo "[$(date +%H:%M:%S)] RPS_req=${RPS} RPS_obs=${observed_rps} p95=${p95}"
  sleep "$INTERVAL"
done

# final snapshot
kubectl get pods -o wide --show-labels > "$RESULT_DIR/logs/pods_after.txt"
kubectl describe svc loadgenerator-metrics -n default > "$RESULT_DIR/logs/loadgen_svc.txt" || true
echo "end_time: $(date --iso-8601=seconds)" >> "$RESULT_DIR/meta/run_info.txt"

echo "Done. CSV saved to: $CSV"
