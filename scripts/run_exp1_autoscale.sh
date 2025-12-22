#!/usr/bin/env bash
set -euo pipefail

########################################
# Experiment 1: autoscale pattern
#
# Phases:
#  A:  1 min @ 400 RPS              (no_action)
#  B:  2 min @ 500 RPS              (no_action)
#  C:  30 x 10s @ 600..1200 RPS     (auto_scale candidates)
#  D1: 1 min @ 30 RPS               (no_action, recovery)
#  D2: 15 min @ 40 RPS              (no_action, low-load tail)
########################################

# Always run from repo root
cd "$(dirname "${BASH_SOURCE[0]}")/.."

EXP_NAME="exp1_autoscale"
RESULT_ROOT="./experiments"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
RESULT_DIR="${RESULT_ROOT}/${EXP_NAME}_${TIMESTAMP}"

mkdir -p "${RESULT_DIR}"/{csv,logs,meta}

########################################
# Basic metadata
########################################
META_FILE="${RESULT_DIR}/meta/metadata.yml"

{
  echo "experiment_id: $(basename "${RESULT_DIR}")"
  echo "name: ${EXP_NAME}"
  echo "start_time_human: $(date --iso-8601=seconds)"
  echo "description: >-"
  echo "  Experiment 1 autoscale pattern: 400/500 RPS no_action,"
  echo "  then 30 x 10s overload steps from 600 to 1200 RPS,"
  echo "  followed by recovery at 30 RPS and long low-load tail at 40 RPS."
} > "${META_FILE}"

########################################
# Port-forward Prometheus
########################################
echo "[*] Starting Prometheus port-forward..."
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-prometheus 9090:9090 \
  >"${RESULT_DIR}/logs/pf_prom.out" 2>&1 &

PROM_PID=$!
echo "${PROM_PID}" > "${RESULT_DIR}/meta/pf_prom.pid"
sleep 0.8

if ! curl -sS http://127.0.0.1:9090/-/ready >/dev/null 2>&1; then
  echo "[!] Prometheus not ready, first 80 lines of log:"
  sed -n '1,80p' "${RESULT_DIR}/logs/pf_prom.out"
  exit 1
fi
echo "[+] Prometheus ready on localhost:9090"

########################################
# Port-forward loadgenerator control
########################################
echo "[*] Starting loadgenerator port-forward..."
kubectl port-forward -n default svc/loadgenerator-metrics 8080:8080 \
  >"${RESULT_DIR}/logs/pf_lg.out" 2>&1 &

LG_PID=$!
echo "${LG_PID}" > "${RESULT_DIR}/meta/pf_lg.pid"
sleep 0.8

if ! curl -sS http://127.0.0.1:8080/health >/dev/null 2>&1; then
  echo "[!] loadgenerator /health failed, checking pods:"
  kubectl get pod -l app=loadgenerator -n default -o wide
  exit 1
fi
echo "[+] loadgenerator control ready on localhost:8080"

########################################
# Mark experiment start time (epoch)
########################################
EXP_START="$(date +%s)"
echo "start_epoch: ${EXP_START}" >> "${META_FILE}"
echo "[*] Experiment 1 start epoch: ${EXP_START}"

########################################
# Helper: set load and sleep
########################################
set_load() {
  local rps="$1"
  local duration="$2"
  echo "[*] Setting load to ${rps} RPS for ${duration}s..."
  curl -sS -X POST http://127.0.0.1:8080/control \
    -H "Content-Type: application/json" \
    --data "{\"rps\":${rps},\"concurrency\":25}" \
    || { echo "[!] Failed to set load to ${rps}"; exit 1; }
  echo
  sleep "${duration}"
}

########################################
# Phase schedule
########################################

# Phase A: 1 min @ 400 RPS (no_action)
set_load 400 60

# Phase B: 2 min @ 500 RPS (no_action)
set_load 500 120

# Phase C: 30 x 10s overload steps (600..1200 RPS)
C_RPS=(
  600 620 640 660 680
  700 720 740 760 780
  800 820 840 860 880
  900 920 940 960 980
  1000 1020 1040 1060 1080
  1100 1120 1140 1160 1200
)

for rps in "${C_RPS[@]}"; do
  set_load "${rps}" 10
done

# Phase D1: 1 min @ 30 RPS (recovery)
set_load 30 60

# Phase D2: 15 min @ 40 RPS (low-load tail)
set_load 40 900

########################################
# Mark experiment end time (epoch)
########################################
EXP_END="$(date +%s)"
echo "end_epoch: ${EXP_END}" >> "${META_FILE}"
echo "[*] Experiment 1 end epoch: ${EXP_START} .. ${EXP_END}"

########################################
# Export Prometheus metrics (step=5s, range=1m)
########################################
START="${EXP_START}"
END="${EXP_END}"

echo "[*] Exporting Prometheus series to JSON..."

# 1) loadgen RPS (1m window)
curl -sG 'http://127.0.0.1:9090/api/v1/query_range' \
  --data-urlencode "query=rate(loadgen_requests_total[1m])" \
  --data-urlencode "start=${START}" \
  --data-urlencode "end=${END}" \
  --data-urlencode "step=5" \
  | jq . > "${RESULT_DIR}/csv/requests_rate.json"

# 2) p95 latency (1m window)
curl -sG 'http://127.0.0.1:9090/api/v1/query_range' \
  --data-urlencode "query=histogram_quantile(0.95, sum(rate(loadgen_request_latency_seconds_bucket[1m])) by (le))" \
  --data-urlencode "start=${START}" \
  --data-urlencode "end=${END}" \
  --data-urlencode "step=5" \
  | jq . > "${RESULT_DIR}/csv/p95_latency.json"

# 3) HTTP 5xx (1m window)
curl -sG 'http://127.0.0.1:9090/api/v1/query_range' \
  --data-urlencode "query=sum(rate(http_requests_total{code=~\"5..\"}[1m]))" \
  --data-urlencode "start=${START}" \
  --data-urlencode "end=${END}" \
  --data-urlencode "step=5" \
  | jq . > "${RESULT_DIR}/csv/http_5xx.json"

# 4) CPU usage for demo-backend pod(s) (1m window)
curl -sG 'http://127.0.0.1:9090/api/v1/query_range' \
  --data-urlencode "query=sum(rate(container_cpu_usage_seconds_total{pod=~\"demo-backend-.*\",container!=\"POD\"}[1m]))" \
  --data-urlencode "start=${START}" \
  --data-urlencode "end=${END}" \
  --data-urlencode "step=5" \
  | jq . > "${RESULT_DIR}/csv/container_cpu.json"

# 5) CPU saturation (usage / 0.3 cores) (1m window)
curl -sG 'http://127.0.0.1:9090/api/v1/query_range' \
  --data-urlencode "query=(sum(rate(container_cpu_usage_seconds_total{pod=~\"demo-backend-.*\",container!=\"POD\"}[1m])) / 0.3)" \
  --data-urlencode "start=${START}" \
  --data-urlencode "end=${END}" \
  --data-urlencode "step=5" \
  | jq . > "${RESULT_DIR}/csv/cpu_saturation.json"

########################################
# JSON -> CSV with jq
########################################
echo "[*] Converting JSON -> CSV..."
cd "${RESULT_DIR}/csv"

# RPS
jq -r '
  .data.result[0].values
  | (["timestamp","value"], (.[] | [.[0], .[1]]))
  | @csv
' requests_rate.json > requests_rate.csv

# p95 latency
jq -r '
  .data.result[0].values
  | (["timestamp","value"], (.[] | [.[0], .[1]]))
  | @csv
' p95_latency.json > p95_latency.csv

# 5xx (may fail if no data)
jq -r '
  .data.result[0].values
  | (["timestamp","value"], (.[] | [.[0], .[1]]))
  | @csv
' http_5xx.json > http_5xx.csv || echo "[*] No 5xx data; http_5xx.csv not created"

# container CPU (cores)
jq -r '
  .data.result[0].values
  | (["timestamp","value"], (.[] | [.[0], .[1]]))
  | @csv
' container_cpu.json > container_cpu.csv

# CPU saturation (fraction of limit)
jq -r '
  .data.result[0].values
  | (["timestamp","value"], (.[] | [.[0], .[1]]))
  | @csv
' cpu_saturation.json > cpu_saturation.csv

########################################
# Done
########################################
cd - >/dev/null 2>&1 || true

echo "[+] Experiment 1 completed."
echo "[+] Results directory: ${RESULT_DIR}"
echo "[i] Prometheus PF PID: ${PROM_PID}, loadgenerator PF PID: ${LG_PID}"
echo "[i] To stop port-forwards later, you can run:"
echo "    kill \$(cat ${RESULT_DIR}/meta/pf_prom.pid) \$(cat ${RESULT_DIR}/meta/pf_lg.pid)"
