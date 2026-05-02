# M10 Plan: NotifyHuman Safety Escalation Proof

Execution note: this plan was later executed successfully; see `summary.md` for the final result.

Status: plan only. Do not execute until explicitly approved.

## Goal

Prove that AutoOrch escalates to `notify_human` instead of repeatedly accepting the same automation candidate.

Expected path:

```text
restart-like fault metrics
-> first Alertmanager alert
-> AutoOrch candidate_action=auto_restart
-> ACTION_MODE=stub simulates auto_restart
-> second restart-like alert/candidate within memory window
-> AutoOrch candidate_action=auto_restart
-> final_action=notify_human
-> reason=repeated_action
-> no real restart or scale
```

## Why This Proves NotifyHuman

The implementation tracks repeated automation candidates using:

```text
namespace/workload:candidate_action
```

Therefore, two restart-like candidates for:

```text
default/controllable-backend:auto_restart
```

within `CONSECUTIVE_MEMORY_SECONDS=300` should trigger `final_action=notify_human` when `CONSECUTIVE_ESCALATION_COUNT=2`.

This proves AutoOrch is a safe orchestration layer, not blind automation.

## Boundaries

- Keep `ACTION_MODE=stub`.
- Do not run real restart.
- Do not run real scale.
- Do not retrain models.
- Do not change architecture.
- Do not broaden RBAC.
- Use only temporary M10 rules.
- Delete temporary rules after proof.
- Reset loadgenerator and fault toggles during cleanup.

## Strategy

Use real restart-like Prometheus features, but stub the action.

To avoid depending on Alertmanager repeat timing, M10 uses two sequential temporary alerts with different alert names but the same target labels and same restart-like feature condition.

Both alerts route through the same M10 AlertmanagerConfig:

```text
m10_test=true
service=controllable-backend
deployment=controllable-backend
```

The first alert should produce:

```text
candidate_action=auto_restart
final_action=auto_restart
reason=restart_confident
action_result.status=simulated
```

The second alert should produce:

```text
candidate_action=auto_restart
final_action=notify_human
reason=repeated_action
action_result.status=simulated
```

## Expected Runtime Values

Use the proven M7 restart-like load/fault pattern:

```text
RPS=20
CONCURRENCY=15
LATENCY_MS=700
errors ON
ACTION_MODE=stub
```

This intentionally uses the M7-proven restart pattern. Earlier tuning showed `RPS=30` could produce a restart probability below the `0.90` threshold, while `RPS=20`, `CONCURRENCY=15`, `LATENCY_MS=700`, and errors enabled produced a reliable `auto_restart` candidate.

Expected feature shape:

```text
http_5xx_rate >= 0.20
p95 > 0.50
cpu_sat < 0.70
p_restart >= 0.90
```

## Proposed Files

```text
evidence/M10_notifyhuman/
  PLAN.md
  summary.md
  commands.md
  manifests/
    alertmanagerconfig-notifyhuman.yaml
    prometheusrule-notifyhuman-first.yaml
    prometheusrule-notifyhuman-second.yaml
  outputs/
    pod_identity_before.txt
    pod_identity_after.txt
    replicas_before_after.txt
  logs/
  code_snippets/
  screenshots/README.md
```

## Execution Steps After Approval

### 1. Preflight

```bash
git status --short
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
kubectl get deploy -n default autoorch-webhook \
  -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="ACTION_MODE")].value}{"\n"}{.spec.template.spec.containers[0].env[?(@.name=="CONSECUTIVE_ESCALATION_COUNT")].value}{"\n"}{.spec.template.spec.containers[0].env[?(@.name=="CONSECUTIVE_MEMORY_SECONDS")].value}{"\n"}'
kubectl get deployment controllable-backend -n default \
  -o jsonpath='{.spec.replicas}{"\n"}{.status.readyReplicas}{"\n"}{.status.availableReplicas}{"\n"}'
kubectl get prometheusrule -n default
```

Expected:

```text
ACTION_MODE=stub
CONSECUTIVE_ESCALATION_COUNT=2
CONSECUTIVE_MEMORY_SECONDS=300
controllable-backend replicas=1
no temporary M10 PrometheusRule exists
```

### 2. Capture Before State

```bash
kubectl get pods -n default -l app=controllable-backend \
  -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,CREATED:.metadata.creationTimestamp,PHASE:.status.phase,NODE:.spec.nodeName
```

Save as:

```text
outputs/pod_identity_before.txt
```

### 3. Reset AutoOrch Memory While Staying In Stub Mode

This rollout intentionally clears previous in-memory candidate history.

```bash
kubectl set env deployment/autoorch-webhook ACTION_MODE=stub --overwrite -n default
kubectl rollout status deployment/autoorch-webhook -n default --timeout=90s
curl -s http://127.0.0.1:18080/health
```

Expected:

```text
"action_mode":"stub"
```

### 4. Open Temporary Port-Forwards

```bash
kubectl port-forward -n default svc/controllable-backend 5000:5000
kubectl port-forward -n default svc/autoorch-webhook 18080:8080
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-prometheus 9090:9090
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-alertmanager 9093:9093
```

If the named Alertmanager service is unavailable, fall back to:

```bash
kubectl port-forward -n monitoring svc/alertmanager-operated 9093:9093
```

### 5. Confirm Fault Toggles Are Off

```bash
curl -s http://127.0.0.1:5000/metrics | grep -E "error_injection_enabled|latency_injection_enabled"
```

Expected:

```text
error_injection_enabled 0.0
latency_injection_enabled 0.0
```

### 6. Start Restart-Like Load/Fault

```bash
kubectl set env deployment/loadgenerator \
  TARGET=http://controllable-backend:5000/api/test \
  RPS=20 \
  CONCURRENCY=15 \
  --overwrite -n default

kubectl rollout status deployment/loadgenerator -n default --timeout=90s

curl -s -X POST "http://127.0.0.1:5000/inject-latency?ms=700"
curl -s -X POST http://127.0.0.1:5000/inject-errors
```

Wait at least 90 seconds for Prometheus `[1m]` windows.

### 7. Confirm Restart-Like Features

```bash
curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=sum(rate(http_requests_total{exported_endpoint="/api/test"}[1m]))'

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[1m])) by (le))'

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=sum(rate(http_requests_total{exported_endpoint="/api/test",status=~"5.."}[1m]))'

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=sum(rate(container_cpu_usage_seconds_total{namespace="default",pod=~"controllable-backend-.*",container!="POD"}[1m])) / 0.5'
```

Expected:

```text
http_5xx_rate >= 0.20
p95 > 0.50
cpu_sat < 0.70
```

### 8. Apply M10 Route

```bash
kubectl apply -f evidence/M10_notifyhuman/manifests/alertmanagerconfig-notifyhuman.yaml
```

### 9. First Restart-Like Alert

```bash
kubectl apply -f evidence/M10_notifyhuman/manifests/prometheusrule-notifyhuman-first.yaml
```

Capture first AutoOrch audit:

```bash
kubectl logs -n default deploy/autoorch-webhook --tail=400
curl -s http://127.0.0.1:18080/metrics
```

Expected first audit:

```text
candidate_action=auto_restart
final_action=auto_restart
decision=auto_restart
reason=restart_confident
action_result.status=simulated
```

### 10. Second Restart-Like Alert Within Memory Window

Apply the second alert only after the first audit is captured. Delete the first rule before applying the second rule so repeated Alertmanager posts from the first alert do not confuse the evidence.

```bash
kubectl delete prometheusrule -n default autoorch-notifyhuman-restart-first --ignore-not-found
```

```bash
kubectl apply -f evidence/M10_notifyhuman/manifests/prometheusrule-notifyhuman-second.yaml
```

Capture second AutoOrch audit:

```bash
kubectl logs -n default deploy/autoorch-webhook --tail=600
curl -s http://127.0.0.1:18080/metrics
```

Expected second audit:

```text
candidate_action=auto_restart
final_action=notify_human
decision=notify_human
reason=repeated_action
escalation.candidate_action=auto_restart
escalation.consecutive_count=2
action_result.action=notify_human
action_result.status=simulated
notify_human metric/counter increases using the actual exposed AutoOrch metric name
```

Before making a hard claim about the metric name, inspect `/metrics` and record the actual exposed name. Expected candidates include:

```text
autoorch_notify_human_total
autoorch_decisions_total{decision="notify_human"}
autoorch_actions_total{action="notify_human",status="simulated"}
```

### 11. Stop Repeated Alerts

Delete temporary rules immediately after the `notify_human` audit is captured:

```bash
kubectl delete prometheusrule -n default autoorch-notifyhuman-restart-first --ignore-not-found
kubectl delete prometheusrule -n default autoorch-notifyhuman-restart-second --ignore-not-found
```

### 12. Capture No Infrastructure Change

```bash
kubectl get deployment controllable-backend -n default \
  -o jsonpath='{.spec.replicas}{"\n"}{.status.readyReplicas}{"\n"}{.status.availableReplicas}{"\n"}'

kubectl get pods -n default -l app=controllable-backend \
  -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,CREATED:.metadata.creationTimestamp,PHASE:.status.phase,NODE:.spec.nodeName
```

Expected:

```text
replicas remain 1/1/1
pod UID unchanged
```

### 13. Cleanup

```bash
curl -s -X POST http://127.0.0.1:5000/inject-latency?ms=0

# /inject-errors is a toggle. Only call it if the metric still reports enabled.
curl -s http://127.0.0.1:5000/metrics | grep error_injection_enabled
if curl -s http://127.0.0.1:5000/metrics | grep -q "error_injection_enabled 1.0"; then
  curl -s -X POST http://127.0.0.1:5000/inject-errors
fi

kubectl set env deployment/loadgenerator \
  TARGET=http://controllable-backend:5000/api/test \
  RPS=0 \
  CONCURRENCY=1 \
  --overwrite -n default

kubectl rollout status deployment/loadgenerator -n default --timeout=90s

kubectl delete prometheusrule -n default autoorch-notifyhuman-restart-first --ignore-not-found
kubectl delete prometheusrule -n default autoorch-notifyhuman-restart-second --ignore-not-found
kubectl delete alertmanagerconfig -n default autoorch-m10-notifyhuman-route --ignore-not-found
```

Final expected state:

```text
ACTION_MODE=stub
controllable-backend replicas=1
loadgenerator RPS=0 CONCURRENCY=1
error_injection_enabled 0.0
latency_injection_enabled 0.0
temporary M10 PrometheusRules deleted
temporary M10 AlertmanagerConfig deleted
```

## Acceptance Criteria

M10 passes only if:

- `ACTION_MODE=stub`;
- first restart-like alert reaches AutoOrch through Alertmanager;
- first decision is `auto_restart` with `action_result.status=simulated`;
- second restart-like alert reaches AutoOrch through Alertmanager within 300 seconds;
- second audit has `candidate_action=auto_restart`;
- second audit has `final_action=notify_human`;
- second audit has `decision=notify_human`;
- second audit has `reason=repeated_action`;
- notify_human counter/metric increases using the actual exposed AutoOrch metric name;
- no real restart happens;
- no real scale happens;
- replicas remain `1/1/1`;
- backend pod UID and creation timestamp do not change;
- cleanup removes temporary M10 resources and resets fault/load settings.

## If M10 Does Not Produce NotifyHuman

- If the first decision is not `auto_restart`, verify restart-like features: 5xx rate, p95, and CPU saturation.
- If the second decision remains `auto_restart`, verify AutoOrch was not rolled between the two alerts and that the second alert occurred within `CONSECUTIVE_MEMORY_SECONDS`.
- If Alertmanager does not send the second alert quickly, use a manual fallback only after approval: send one Alertmanager-like POST to `/alert` while the same restart-like metrics are active. Record this honestly if used.
- Do not fake `notify_human` evidence.
