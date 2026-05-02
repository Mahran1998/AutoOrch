# M8B Plan: Real AutoScale Remediation

Do not execute this plan until M8B-Prep is accepted.

## Scope

M8B is the first AutoScale milestone allowed to change Kubernetes replica state.

Expected path:

```text
high-load condition
-> PrometheusRule AutoOrchScalePressure
-> Alertmanager
-> AutoOrch /alert
-> P(auto_scale) >= 0.90
-> candidate_action=auto_scale
-> final_action=auto_scale
-> ACTION_MODE=ansible
-> scale_deployment.yml
-> kubectl scale deployment/controllable-backend --replicas=2
```

## Required Precondition

M8B-Prep must first add and verify narrow `deployments/scale` RBAC for `autoorch-runner`.

## Proposed Execution Steps

### 1. Confirm Baseline

```bash
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
kubectl get deploy -n default controllable-backend \
  -o custom-columns=NAME:.metadata.name,READY:.status.readyReplicas,REPLICAS:.spec.replicas,AVAILABLE:.status.availableReplicas
kubectl get pods -n default -l app=controllable-backend \
  -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,CREATED:.metadata.creationTimestamp,PHASE:.status.phase,NODE:.spec.nodeName
```

Expected:

```text
controllable-backend replicas=1
```

### 2. Switch to Ansible Mode

```bash
kubectl set env deployment/autoorch-webhook ACTION_MODE=ansible --overwrite -n default
kubectl rollout status deployment/autoorch-webhook -n default --timeout=90s
curl -s http://127.0.0.1:18080/health
```

Expected:

```json
"action_mode":"ansible"
```

### 3. Apply Temporary M8B Route and Rule

Reuse the M8A manifests unless copied into M8B-specific manifest files:

```bash
kubectl apply -f evidence/M8B_autoscale_real_action/manifests/alertmanagerconfig-autoscale.yaml
kubectl apply -f evidence/M8B_autoscale_real_action/manifests/prometheusrule-autoscale.yaml
```

### 4. Start Calibrated Load

```bash
kubectl set env deployment/loadgenerator \
  TARGET=http://controllable-backend:5000/api/test \
  RPS=500 \
  CONCURRENCY=75 \
  --overwrite -n default

kubectl rollout status deployment/loadgenerator -n default --timeout=90s
```

Wait at least 120 seconds.

### 5. Capture Real Action

Expected AutoOrch audit:

```text
candidate_action=auto_scale
final_action=auto_scale
reason=autoscale_confident
p_autoscale >= 0.90
action_result.status=success
action_result.details.desired_replicas=2
command includes ansible-playbook /app/playbooks/scale_deployment.yml
```

Expected Kubernetes state:

```text
controllable-backend replicas=2
available replicas eventually 2
```

### 6. Stop Repeated Alerts

After first successful scale:

```bash
kubectl delete prometheusrule -n default autoorch-autoscale-pressure --ignore-not-found
```

### 7. Cleanup

```bash
kubectl scale deployment/controllable-backend -n default --replicas=1
kubectl rollout status deployment/controllable-backend -n default --timeout=90s

kubectl set env deployment/loadgenerator \
  TARGET=http://controllable-backend:5000/api/test \
  RPS=0 \
  CONCURRENCY=1 \
  --overwrite -n default
kubectl rollout status deployment/loadgenerator -n default --timeout=90s

kubectl set env deployment/autoorch-webhook ACTION_MODE=stub --overwrite -n default
kubectl rollout status deployment/autoorch-webhook -n default --timeout=90s

kubectl delete prometheusrule -n default autoorch-autoscale-pressure --ignore-not-found
kubectl delete alertmanagerconfig -n default autoorch-m8-autoscale-route --ignore-not-found
```

Final expected state:

```text
ACTION_MODE=stub
controllable-backend replicas=1
loadgenerator RPS=0 CONCURRENCY=1
error_injection_enabled 0.0
latency_injection_enabled 0.0
```

## Acceptance Criteria

M8B passes only if:

- `ACTION_MODE=ansible` during action window;
- AutoOrch receives `AutoOrchScalePressure`;
- `candidate_action=auto_scale`;
- `final_action=auto_scale`;
- `reason=autoscale_confident`;
- `action_result.status=success`;
- deployment scales from `1` to `2`;
- cleanup returns deployment to `1`;
- `ACTION_MODE` returns to `stub`;
- no unrelated workloads are changed.

