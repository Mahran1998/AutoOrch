# M9 Plan: NoAction Proof

Do not execute this plan until it is reviewed and approved.

## Scope

M9 proves that AutoOrch does not blindly remediate every alert. It should suppress a benign/noisy alert when the live Prometheus feature vector is healthy.

Expected path:

```text
benign test alert
-> Alertmanager
-> AutoOrch POST /alert
-> Prometheus feature extraction
-> P(auto_scale) < 0.90
-> P(auto_restart) < 0.90
-> candidate_action=no_action
-> final_action=no_action
-> action_result.status=skipped
-> no Kubernetes state change
```

## Boundaries

- Keep `ACTION_MODE=stub`.
- Do not run real restart.
- Do not run real scale.
- Do not retrain models.
- Do not change architecture.
- Do not broaden RBAC.
- Do not inject errors.
- Do not inject latency.
- Use low healthy load only.
- Delete the temporary PrometheusRule after the first clean NoAction proof.

## Important Interpretation

The M9 alert is intentionally a temporary benign test alert:

```promql
vector(1)
```

This creates a controlled noisy alert. The alert is synthetic, but the decision features are real Prometheus metrics from `controllable-backend`.

This is thesis-safe because the purpose of M9 is not to prove a natural production incident; it is to prove the AutoOrch decision layer can avoid unnecessary remediation when an alert arrives but the measured system state is healthy.

## Proposed Healthy Load

Use low load only to keep histogram and request-rate series active:

```text
RPS=10
CONCURRENCY=5
errors OFF
latency OFF
ACTION_MODE=stub
```

If idle traffic already produces stable metrics, keep load at `RPS=0`; otherwise use the low load above.

## Temporary Alert Rule

Alert name:

```text
AutoOrchNoActionBenign
```

The rule must include labels:

```text
namespace=default
service=controllable-backend
deployment=controllable-backend
severity=info
```

## Proposed Files

```text
evidence/M9_noaction/
  PLAN.md
  summary.md
  commands.md
  manifests/
    alertmanagerconfig-noaction.yaml
    prometheusrule-noaction.yaml
  outputs/
  logs/
  code_snippets/
  screenshots/README.md
```

## Commands To Run After Approval

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
no temporary M9 PrometheusRule exists
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

```bash
kubectl set env deployment/autoorch-webhook ACTION_MODE=stub --overwrite -n default
kubectl rollout status deployment/autoorch-webhook -n default --timeout=90s
```

Expected:

```text
ACTION_MODE=stub
```

### 4. Open Temporary Port-Forwards

```bash
kubectl port-forward -n default svc/controllable-backend 5000:5000
kubectl port-forward -n default svc/autoorch-webhook 18080:8080
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-prometheus 9090:9090
kubectl port-forward -n monitoring svc/alertmanager-operated 9093:9093
```

### 5. Verify Fault Toggles Are Off

```bash
curl -s http://127.0.0.1:5000/metrics | grep -E "error_injection_enabled|latency_injection_enabled"
```

Expected:

```text
error_injection_enabled 0.0
latency_injection_enabled 0.0
```

If latency is not zero, reset it:

```bash
curl -s -X POST http://127.0.0.1:5000/inject-latency?ms=0
```

### 6. Start Low Healthy Load

```bash
kubectl set env deployment/loadgenerator \
  TARGET=http://controllable-backend:5000/api/test \
  RPS=10 \
  CONCURRENCY=5 \
  --overwrite -n default

kubectl rollout status deployment/loadgenerator -n default --timeout=90s
```

Wait at least 90 seconds before judging the feature vector.

### 7. Apply M9 Route And Benign Alert

```bash
kubectl apply -f evidence/M9_noaction/manifests/alertmanagerconfig-noaction.yaml
kubectl apply -f evidence/M9_noaction/manifests/prometheusrule-noaction.yaml
```

### 8. Capture Decision Evidence

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
  --data-urlencode 'query=ALERTS{alertname="AutoOrchNoActionBenign"}'
```

Alertmanager:

```bash
curl -s http://127.0.0.1:9093/api/v2/alerts
```

AutoOrch:

```bash
curl -s http://127.0.0.1:18080/health
curl -s http://127.0.0.1:18080/metrics
kubectl logs -n default deploy/autoorch-webhook --tail=400
```

Replica and pod safety:

```bash
kubectl get deployment controllable-backend -n default \
  -o jsonpath='{.spec.replicas}{"\n"}{.status.readyReplicas}{"\n"}{.status.availableReplicas}{"\n"}'

kubectl get pods -n default -l app=controllable-backend \
  -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,CREATED:.metadata.creationTimestamp,PHASE:.status.phase,NODE:.spec.nodeName
```

### 9. Stop Repeated Alert Posts

After the first clean NoAction decision:

```bash
kubectl delete prometheusrule -n default autoorch-noaction-benign --ignore-not-found
```

### 10. Cleanup

```bash
kubectl set env deployment/loadgenerator \
  TARGET=http://controllable-backend:5000/api/test \
  RPS=0 \
  CONCURRENCY=1 \
  --overwrite -n default

kubectl rollout status deployment/loadgenerator -n default --timeout=90s

kubectl delete prometheusrule -n default autoorch-noaction-benign --ignore-not-found
kubectl delete alertmanagerconfig -n default autoorch-m9-noaction-route --ignore-not-found
```

Final expected state:

```text
ACTION_MODE=stub
controllable-backend replicas=1
loadgenerator RPS=0 CONCURRENCY=1
error_injection_enabled 0.0
latency_injection_enabled 0.0
temporary M9 PrometheusRule deleted
temporary M9 AlertmanagerConfig deleted
```

## Acceptance Criteria

M9 passes only if:

- `ACTION_MODE=stub`;
- `AutoOrchNoActionBenign` reaches AutoOrch through Alertmanager;
- Prometheus features are healthy or benign;
- `p_autoscale < 0.90`;
- `p_restart < 0.90`;
- `candidate_action=no_action`;
- `final_action=no_action`;
- `decision=no_action`;
- `reason=below_threshold` or equivalent;
- `action_result.status=skipped`;
- replicas remain `1/1/1`;
- backend pod UID and creation timestamp do not change;
- no real restart or scale happens;
- cleanup removes temporary M9 resources.

## If M9 Does Not Produce NoAction

- If `p_autoscale >= 0.90`, reduce load to `RPS=0` or `RPS=5`.
- If `p_restart >= 0.90`, check for leftover error/latency injection or restart evidence.
- If metrics are missing, use low healthy load for 90 seconds and retry once.
- Do not fake a NoAction result.
