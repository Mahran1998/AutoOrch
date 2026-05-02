# M8A Plan: AutoScale Decision Proof in Stub Mode

## Scope

M8A proves the AutoScale decision path without changing Kubernetes replicas.

Expected path:

```text
high-load condition
-> PrometheusRule AutoOrchScalePressure
-> Alertmanager
-> AutoOrch POST /alert
-> Prometheus feature extraction
-> P(auto_scale) >= 0.90
-> candidate_action=auto_scale
-> final_action=auto_scale
-> reason=autoscale_confident
-> action_result.status=simulated
```

## Boundaries

- Keep `ACTION_MODE=stub`.
- Do not scale replicas.
- Do not broaden RBAC.
- Do not retrain models.
- Do not change architecture.
- Do not start M8B.
- Do not inject errors.
- Do not inject latency.

## Final Safeguards Added

1. Reset AutoOrch in-memory decision history before the test by rolling the AutoOrch pod while keeping `ACTION_MODE=stub`.
2. Delete the temporary `AutoOrchScalePressure` PrometheusRule immediately after the first clean AutoScale decision is captured. This avoids repeated Alertmanager posts turning a later decision into `notify_human`.
3. Treat high p95 as non-required. M8A targets high CPU saturation and low 5xx, not artificial latency.
4. If the calibrated load point does not reproduce `P(auto_scale) >= 0.90`, stop and tune one load parameter. Do not force evidence.

## Calibrated Load Point

Use the successful M8-Calibrate point:

```text
RPS=500
CONCURRENCY=75
errors OFF
latency OFF
ACTION_MODE=stub
```

Calibration evidence:

```text
measured_rps=132.0316
p95=0.000950
http_5xx_rate=0.0
cpu_sat=1.8840
p_auto_scale=0.9311
```

## Temporary Alert Rule

Use a CPU-focused alert. Do not require high p95.

Acceptance alert condition:

```promql
(
  sum(rate(container_cpu_usage_seconds_total{namespace="default",pod=~"controllable-backend-.*",container!="POD"}[1m])) / 0.5 >= 0.70
)
and
(
  sum(rate(http_requests_total{exported_endpoint="/api/test"}[1m])) >= 100
)
and
(
  (sum(rate(http_requests_total{exported_endpoint="/api/test",status=~"5.."}[1m])) or vector(0)) < 0.20
)
```

The `or vector(0)` clause is intentional: when no 5xx series exists, Prometheus returns an empty vector, which should be interpreted as zero 5xx.

## Proposed Files

```text
evidence/M8_autoscale/decision_stub/
  PLAN.md
  commands.md
  manifests/
    alertmanagerconfig-autoscale.yaml
    prometheusrule-autoscale.yaml
  outputs/
  logs/
  code_snippets/
  screenshots/README.md
```

## Commands to Run After Approval

### 1. Preflight

```bash
git status --short
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
kubectl get deploy -n default autoorch-webhook \
  -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="ACTION_MODE")].value}{"\n"}'
kubectl get deploy -n default controllable-backend \
  -o jsonpath='{.spec.replicas}{"\n"}{.status.readyReplicas}{"\n"}{.status.availableReplicas}{"\n"}'
kubectl get prometheusrule -n default
```

Expected:

```text
ACTION_MODE=stub
controllable-backend replicas=1
no M8 temporary PrometheusRule exists
```

### 2. Reset AutoOrch Memory While Staying in Stub Mode

```bash
kubectl rollout restart deployment/autoorch-webhook -n default
kubectl rollout status deployment/autoorch-webhook -n default --timeout=90s
kubectl get deploy -n default autoorch-webhook \
  -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="ACTION_MODE")].value}{"\n"}'
```

Expected:

```text
stub
```

### 3. Open Temporary Port-Forwards

```bash
kubectl port-forward -n default svc/controllable-backend 5000:5000
kubectl port-forward -n default svc/autoorch-webhook 18080:8080
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-prometheus 9090:9090
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-alertmanager 9093:9093
```

### 4. Verify Fault Toggles Are Off

```bash
curl -s http://127.0.0.1:5000/metrics | grep -E "error_injection_enabled|latency_injection_enabled"
```

Expected:

```text
error_injection_enabled 0.0
latency_injection_enabled 0.0
```

If not, reset before continuing:

```bash
curl -s -X POST http://127.0.0.1:5000/inject-latency?ms=0
```

### 5. Apply M8A Routing Manifests

```bash
kubectl apply -f evidence/M8_autoscale/decision_stub/manifests/alertmanagerconfig-autoscale.yaml
kubectl apply -f evidence/M8_autoscale/decision_stub/manifests/prometheusrule-autoscale.yaml
```

### 6. Start Calibrated Load

```bash
kubectl set env deployment/loadgenerator \
  TARGET=http://controllable-backend:5000/api/test \
  RPS=500 \
  CONCURRENCY=75 \
  --overwrite -n default

kubectl rollout status deployment/loadgenerator -n default --timeout=90s
```

Wait at least 120 seconds before judging the result.

### 7. Capture Decision Evidence

Prometheus values:

```bash
curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=sum(rate(http_requests_total{exported_endpoint="/api/test"}[1m]))'

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[1m])) by (le))'

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=(sum(rate(http_requests_total{exported_endpoint="/api/test",status=~"5.."}[1m])) or vector(0))'

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=sum(rate(container_cpu_usage_seconds_total{namespace="default",pod=~"controllable-backend-.*",container!="POD"}[1m])) / 0.5'

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=ALERTS{alertname="AutoOrchScalePressure"}'
```

Alertmanager:

```bash
curl -s http://127.0.0.1:9093/api/v2/alerts
```

AutoOrch:

```bash
curl -s http://127.0.0.1:18080/health
curl -s http://127.0.0.1:18080/metrics | grep autoorch
kubectl logs -n default deploy/autoorch-webhook --tail=400
```

Replica safety:

```bash
kubectl get deploy -n default controllable-backend -o wide
kubectl get pods -n default -o wide | grep controllable-backend
```

### 8. Stop Repeated Alert Posts Quickly

After the first clean AutoScale decision is captured:

```bash
kubectl delete prometheusrule -n default autoorch-autoscale-pressure --ignore-not-found
```

### 9. Cleanup

```bash
kubectl set env deployment/loadgenerator \
  TARGET=http://controllable-backend:5000/api/test \
  RPS=0 \
  CONCURRENCY=1 \
  --overwrite -n default

kubectl rollout status deployment/loadgenerator -n default --timeout=90s

kubectl delete prometheusrule -n default autoorch-autoscale-pressure --ignore-not-found
kubectl delete alertmanagerconfig -n default autoorch-m8-autoscale-route --ignore-not-found

curl -s http://127.0.0.1:5000/metrics | grep -E "error_injection_enabled|latency_injection_enabled"

kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
kubectl get deploy -n default loadgenerator \
  -o jsonpath='{.spec.template.spec.containers[0].env}{"\n"}'
kubectl get deploy -n default autoorch-webhook \
  -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="ACTION_MODE")].value}{"\n"}'
pgrep -af 'kubectl port-forward' || true
```

## Acceptance Criteria

M8A passes only if:

- `ACTION_MODE=stub`
- errors OFF
- latency OFF
- `AutoOrchScalePressure` fires
- Alertmanager routes the alert to AutoOrch
- AutoOrch logs show `POST /alert`
- AutoOrch logs show `p_autoscale >= 0.90`
- AutoOrch logs show `candidate_action=auto_scale`
- AutoOrch logs show `final_action=auto_scale`
- AutoOrch logs show `reason=autoscale_confident`
- `action_result.status=simulated`
- controllable-backend remains at 1 replica
- no real scaling happens

## Contingency

If `P(auto_scale) < 0.90` but 5xx remains zero, try one load-only adjustment:

```text
RPS=700
CONCURRENCY=100
```

Stop if:

- `http_5xx_rate >= 0.20`
- backend becomes unstable
- AutoOrch selects `auto_restart` or `notify_human`

Do not proceed to M8B unless M8A passes.

