#!/usr/bin/env bash
set -euo pipefail

########################################
# Experiment 2: controlled AutoRestart data collection
#
# Target: controllable-backend
# Phases:
#   A: healthy baseline       -> no_action
#   B: error + latency fault  -> auto_restart candidates after labeling
#   C: recovery               -> no_action
#
# This script collects real Prometheus-derived metric windows. It does not
# train a model.
########################################

cd "$(dirname "${BASH_SOURCE[0]}")/.."

EXP_NAME="exp2_restart"
RESULT_ROOT="${RESULT_ROOT:-./experiments/restart}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
EXPERIMENT_ID="${EXP_NAME}_${TIMESTAMP}"
RESULT_DIR="${RESULT_ROOT}/${EXPERIMENT_ID}"
FEATURE_WINDOWS="${RESULT_ROOT}/feature_windows_restart.csv"

KUBE_NS="${KUBE_NS:-default}"
RPS="${RPS:-30}"
CONCURRENCY="${CONCURRENCY:-15}"
LATENCY_MS="${LATENCY_MS:-700}"
PHASE_SECONDS="${PHASE_SECONDS:-300}"
PROMETHEUS_STEP="${PROMETHEUS_STEP:-15}"
CPU_LIMIT_CORES="${CPU_LIMIT_CORES:-0.5}"

mkdir -p "${RESULT_DIR}"/{csv,logs,meta} "${RESULT_ROOT}"

META_FILE="${RESULT_DIR}/meta/metadata.yml"
PHASES_CSV="${RESULT_DIR}/meta/phases.csv"
LOCAL_FEATURE_WINDOWS="${RESULT_DIR}/csv/feature_windows_restart.csv"

cat > "${META_FILE}" <<META
experiment_id: ${EXPERIMENT_ID}
name: ${EXP_NAME}
target: controllable-backend
target_url: http://controllable-backend:5000/api/test
start_time_human: $(date --iso-8601=seconds)
rps: ${RPS}
concurrency: ${CONCURRENCY}
latency_ms: ${LATENCY_MS}
phase_seconds: ${PHASE_SECONDS}
cpu_limit_cores_fallback: ${CPU_LIMIT_CORES}
label_rule: http_5xx_rate >= 0.20 AND cpu_sat < 0.70 AND p95 > 0.50
META

echo "phase,expected_label,start_epoch,end_epoch,rps,latency_ms,error_injection" > "${PHASES_CSV}"

PROM_PID=""
LG_PID=""
BACKEND_PID=""

cleanup() {
  for pid in "${PROM_PID}" "${LG_PID}" "${BACKEND_PID}"; do
    if [ -n "${pid}" ]; then
      kill "${pid}" >/dev/null 2>&1 || true
    fi
  done
}
trap cleanup EXIT

wait_for_url() {
  local url="$1"
  local label="$2"
  for _ in $(seq 1 30); do
    if curl -sS "${url}" >/dev/null 2>&1; then
      echo "[+] ${label} ready: ${url}"
      return 0
    fi
    sleep 1
  done
  echo "[!] ${label} did not become ready: ${url}"
  return 1
}

start_port_forwards() {
  echo "[*] Starting Prometheus port-forward..."
  kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-prometheus 9090:9090 \
    >"${RESULT_DIR}/logs/pf_prom.out" 2>&1 &
  PROM_PID=$!
  echo "${PROM_PID}" > "${RESULT_DIR}/meta/pf_prom.pid"
  wait_for_url "http://127.0.0.1:9090/-/ready" "Prometheus"

  echo "[*] Starting loadgenerator port-forward..."
  kubectl port-forward -n "${KUBE_NS}" svc/loadgenerator-metrics 8080:8080 \
    >"${RESULT_DIR}/logs/pf_lg.out" 2>&1 &
  LG_PID=$!
  echo "${LG_PID}" > "${RESULT_DIR}/meta/pf_lg.pid"
  wait_for_url "http://127.0.0.1:8080/health" "loadgenerator"

  echo "[*] Starting controllable-backend port-forward..."
  kubectl port-forward -n "${KUBE_NS}" svc/controllable-backend 5000:5000 \
    >"${RESULT_DIR}/logs/pf_backend.out" 2>&1 &
  BACKEND_PID=$!
  echo "${BACKEND_PID}" > "${RESULT_DIR}/meta/pf_backend.pid"
  wait_for_url "http://127.0.0.1:5000/health" "controllable-backend"
}

set_load() {
  local rps="$1"
  local concurrency="$2"
  echo "[*] Setting loadgenerator to RPS=${rps}, concurrency=${concurrency}"
  curl -sS -X POST "http://127.0.0.1:8080/control" \
    -H "Content-Type: application/json" \
    --data "{\"rps\":${rps},\"concurrency\":${concurrency}}" >/dev/null
}

current_error_state() {
  curl -sS "http://127.0.0.1:5000/" | jq -r '.error_injection_enabled'
}

set_errors() {
  local desired="$1"
  local current
  current="$(current_error_state)"
  if [ "${current}" != "${desired}" ]; then
    echo "[*] Toggling error injection to ${desired}"
    curl -sS -X POST "http://127.0.0.1:5000/inject-errors" >/dev/null
  else
    echo "[*] Error injection already ${desired}"
  fi
}

set_latency() {
  local ms="$1"
  echo "[*] Setting latency injection to ${ms}ms"
  curl -sS -X POST "http://127.0.0.1:5000/inject-latency?ms=${ms}" >/dev/null
}

record_phase() {
  local phase="$1"
  local expected_label="$2"
  local start_epoch="$3"
  local end_epoch="$4"
  local latency_ms="$5"
  local error_injection="$6"
  echo "${phase},${expected_label},${start_epoch},${end_epoch},${RPS},${latency_ms},${error_injection}" >> "${PHASES_CSV}"
}

run_phase() {
  local phase="$1"
  local expected_label="$2"
  local latency_ms="$3"
  local error_state="$4"

  echo "[*] Phase ${phase}: expected=${expected_label}, duration=${PHASE_SECONDS}s"
  set_errors "${error_state}"
  set_latency "${latency_ms}"
  set_load "${RPS}" "${CONCURRENCY}"

  local start_epoch
  local end_epoch
  start_epoch="$(date +%s)"
  sleep "${PHASE_SECONDS}"
  end_epoch="$(date +%s)"
  record_phase "${phase}" "${expected_label}" "${start_epoch}" "${end_epoch}" "${latency_ms}" "${error_state}"
}

query_range() {
  local query="$1"
  local outfile="$2"
  echo "[*] Exporting ${outfile}"
  curl -sG "http://127.0.0.1:9090/api/v1/query_range" \
    --data-urlencode "query=${query}" \
    --data-urlencode "start=${EXP_START}" \
    --data-urlencode "end=${EXP_END}" \
    --data-urlencode "step=${PROMETHEUS_STEP}" \
    | jq . > "${RESULT_DIR}/csv/${outfile}.json"
}

json_to_csv() {
  local infile="$1"
  local outfile="$2"
  if jq -e '.data and (.data.result | length > 0)' "${RESULT_DIR}/csv/${infile}.json" >/dev/null 2>&1; then
    jq -r '.data.result[0].values | (["timestamp","value"]), (.[] | [.[0], .[1]]) | @csv' \
      "${RESULT_DIR}/csv/${infile}.json" > "${RESULT_DIR}/csv/${outfile}.csv"
    echo "[+] Wrote ${RESULT_DIR}/csv/${outfile}.csv"
  else
    echo "[!] No data for ${infile}; ${outfile}.csv not created"
  fi
}

build_feature_windows() {
  .venv/bin/python - "$RESULT_DIR" "$PHASES_CSV" "$LOCAL_FEATURE_WINDOWS" "$FEATURE_WINDOWS" <<'PY'
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

result_dir = Path(sys.argv[1])
phases_csv = Path(sys.argv[2])
local_output = Path(sys.argv[3])
global_output = Path(sys.argv[4])


def to_float(value: object) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


def load_series(name: str, default: float | None = None) -> dict[int, float]:
    path = result_dir / "csv" / f"{name}.json"
    data = json.loads(path.read_text())
    results = data.get("data", {}).get("result", [])
    if not results:
        return {}
    series: dict[int, float] = {}
    for ts, raw in results[0].get("values", []):
        value = to_float(raw)
        if value is None:
            if default is None:
                continue
            value = default
        series[int(float(ts))] = value
    return series


with phases_csv.open() as handle:
    phases = list(csv.DictReader(handle))


def phase_for(timestamp: int) -> str | None:
    for phase in phases:
        start = int(phase["start_epoch"])
        end = int(phase["end_epoch"])
        if start <= timestamp <= end:
            return phase["phase"]
    return None


rps = load_series("requests_rate")
p95 = load_series("p95_latency")
http_5xx = load_series("http_5xx", default=0.0)
cpu_sat = load_series("cpu_saturation")

rows = []
for ts in sorted(rps):
    phase = phase_for(ts)
    if phase is None:
        continue
    values = {
        "rps": rps.get(ts),
        "p95": p95.get(ts),
        "http_5xx_rate": http_5xx.get(ts, 0.0),
        "cpu_sat": cpu_sat.get(ts),
    }
    if any(value is None for value in values.values()):
        continue
    rows.append(
        {
            "window_start": ts - 60,
            "window_end": ts,
            "experiment_id": result_dir.name,
            "phase": phase,
            **values,
        }
    )

fieldnames = ["window_start", "window_end", "experiment_id", "phase", "rps", "p95", "http_5xx_rate", "cpu_sat"]
for output in (local_output, global_output):
    output.parent.mkdir(parents=True, exist_ok=True)
    append = output == global_output and output.exists()
    with output.open("a" if append else "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not append:
            writer.writeheader()
        writer.writerows(rows)

print(f"Wrote {len(rows)} feature windows to {local_output}")
print(f"Updated aggregate feature windows at {global_output}")
PY
}

echo "[*] Verifying deployments..."
kubectl get deployment -n "${KUBE_NS}" controllable-backend >/dev/null
kubectl get deployment -n "${KUBE_NS}" loadgenerator >/dev/null
kubectl set env deployment/loadgenerator \
  TARGET="http://controllable-backend:5000/api/test" \
  --overwrite -n "${KUBE_NS}" >/dev/null
kubectl rollout status deployment/loadgenerator -n "${KUBE_NS}" --timeout=60s >/dev/null

start_port_forwards
set_errors "false"
set_latency "0"

EXP_START="$(date +%s)"
echo "start_epoch: ${EXP_START}" >> "${META_FILE}"

run_phase "healthy_baseline" "no_action" "0" "false"
run_phase "error_latency_fault" "auto_restart" "${LATENCY_MS}" "true"
run_phase "recovery" "no_action" "0" "false"

set_errors "false"
set_latency "0"

EXP_END="$(date +%s)"
echo "end_epoch: ${EXP_END}" >> "${META_FILE}"
echo "end_time_human: $(date --iso-8601=seconds)" >> "${META_FILE}"

query_range 'sum(rate(http_requests_total{exported_endpoint="/api/test"}[1m]))' requests_rate
query_range 'histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[1m])) by (le))' p95_latency
query_range 'sum(rate(http_requests_total{exported_endpoint="/api/test",status=~"5.."}[1m]))' http_5xx
query_range "sum(rate(container_cpu_usage_seconds_total{namespace=\"${KUBE_NS}\",pod=~\"controllable-backend-.*\",container!=\"POD\"}[1m]))" container_cpu
query_range "sum(kube_pod_container_resource_limits{namespace=\"${KUBE_NS}\",pod=~\"controllable-backend-.*\",resource=\"cpu\"})" cpu_limit
query_range "(sum(rate(container_cpu_usage_seconds_total{namespace=\"${KUBE_NS}\",pod=~\"controllable-backend-.*\",container!=\"POD\"}[1m])) / ${CPU_LIMIT_CORES})" cpu_saturation
query_range 'error_injection_enabled' error_injection_state
query_range 'latency_injection_enabled' latency_injection_state

json_to_csv requests_rate requests_rate
json_to_csv p95_latency p95_latency
json_to_csv http_5xx http_5xx
json_to_csv container_cpu container_cpu
json_to_csv cpu_limit cpu_limit
json_to_csv cpu_saturation cpu_saturation
json_to_csv error_injection_state error_injection_state
json_to_csv latency_injection_state latency_injection_state

build_feature_windows

echo "[+] Restart experiment completed. Results: ${RESULT_DIR}"
echo "[+] Intermediate feature windows: ${FEATURE_WINDOWS}"
echo "[i] Next step after review: scripts/build_dataset_restart.py --input ${FEATURE_WINDOWS}"
