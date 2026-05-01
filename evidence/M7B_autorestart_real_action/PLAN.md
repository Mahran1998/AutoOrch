# M7B AutoRestart Real Action Plan

Status: plan only. Do not execute until explicitly approved.

## Goal

Prove the real AutoRestart remediation path:

PrometheusRule `AutoOrchRestartFault` -> Alertmanager -> AutoOrch `POST /alert` -> Prometheus feature extraction -> restart model decision -> Ansible runbook -> Kubernetes deployment restart.

M7B differs from M7A because `ACTION_MODE` will temporarily switch from `stub` to `ansible` and the restart action will actually execute.

## Boundaries

- Do not start M8.
- Do not retrain models.
- Do not change architecture.
- Do not broaden RBAC.
- Do not fake Ansible execution.
- Run only against namespace `default` and deployment `controllable-backend`.
- Return `ACTION_MODE` to `stub` during cleanup.

## Executor Mode

Approved real executor for M7B:

```bash
ACTION_MODE=ansible
PLAYBOOK_DIR=/app/playbooks
```

Expected AutoOrch command for real restart:

```bash
ansible-playbook /app/playbooks/restart_deployment.yml -e namespace=default -e workload=controllable-backend
```

The playbook internally runs:

```bash
kubectl rollout restart deployment/controllable-backend -n default
```

External rollout completion will be verified from the operator terminal:

```bash
kubectl rollout status deployment/controllable-backend -n default --timeout=120s
```

## Evidence Folder

Create this structure before the run:

```bash
mkdir -p evidence/M7B_autorestart_real_action/{manifests,outputs,logs,code_snippets,screenshots}
```

The folder must stand alone without screenshots. Screenshots are thesis polish and will be captured later in M12.

Required files after the run:

```text
evidence/M7B_autorestart_real_action/
  summary.md
  commands.md
  manifests/
  outputs/
  logs/
  code_snippets/
  screenshots/README.md
```

## Preflight

Confirm current Git state and intended runtime:

```bash
git status --short
kubectl get deploy -n default autoorch-webhook controllable-backend loadgenerator
kubectl get pods -n default -o wide
kubectl get prometheusrule -n default autoorch-autorestart-fault || true
kubectl get alertmanagerconfig -n default autoorch-m7-autorestart-route || true
kubectl get deploy -n default autoorch-webhook -o jsonpath='{.spec.template.spec.serviceAccountName}{"\n"}{.spec.template.spec.containers[0].env[?(@.name=="ACTION_MODE")].value}{"\n"}{.spec.template.spec.containers[0].env[?(@.name=="PLAYBOOK_DIR")].value}{"\n"}'
```

Expected before M7B:

```text
autoorch-runner
stub
/app/playbooks
```

Verify RBAC remains narrow:

```bash
kubectl auth can-i get deployment/controllable-backend -n default --as=system:serviceaccount:default:autoorch-runner
kubectl auth can-i patch deployment/controllable-backend -n default --as=system:serviceaccount:default:autoorch-runner
kubectl auth can-i patch deployment/demo-backend -n default --as=system:serviceaccount:default:autoorch-runner
```

Expected:

```text
yes
yes
no
```

Verify tools and playbook syntax inside the pod:

```bash
POD=$(kubectl get pod -n default -l app=autoorch -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n default "$POD" -- kubectl version --client
kubectl exec -n default "$POD" -- sh -c 'command -v ansible-playbook && ansible-playbook --version | head -1'
kubectl exec -n default "$POD" -- ansible-playbook --syntax-check /app/playbooks/restart_deployment.yml
```

## Save Manifests

Reuse the narrow M7 route and restart fault rule from M7A:

```bash
cp evidence/M7_autorestart/manifests/alertmanagerconfig-autorestart.yaml \
  evidence/M7B_autorestart_real_action/manifests/alertmanagerconfig-autorestart.yaml

cp evidence/M7_autorestart/manifests/prometheusrule-autorestart.yaml \
  evidence/M7B_autorestart_real_action/manifests/prometheusrule-autorestart.yaml
```

Route:

```text
AlertmanagerConfig: autoorch-m7-autorestart-route
Receiver URL: http://autoorch-webhook.default.svc.cluster.local:8080/alert
Alert: AutoOrchRestartFault
Target labels: namespace=default, service=controllable-backend, deployment=controllable-backend
Webhook timeout: 30s
```

Runtime probe safeguard:

The real Ansible action can take several seconds. AutoOrch readiness/liveness probes should allow enough timeout budget during the action window so a successful runbook does not cause a webhook pod restart. The deployment uses `timeoutSeconds: 5` and `failureThreshold: 6` for both probes.

## Switch To Real Ansible Mode

Approval gate: do not run this until M7B execution is approved.

This rollout intentionally resets AutoOrch in-memory decision history before the real action test.

```bash
kubectl set env deployment/autoorch-webhook ACTION_MODE=ansible --overwrite -n default
kubectl rollout status deployment/autoorch-webhook -n default --timeout=90s
kubectl logs -n default deploy/autoorch-webhook --tail=120
```

Verify:

```bash
kubectl port-forward -n default svc/autoorch-webhook 18080:8080
curl -s http://127.0.0.1:18080/health
```

Expected health includes:

```json
"action_mode":"ansible"
```

Stop the port-forward after the health check.

## Configure Traffic

Use the M7A-passing load profile:

```bash
kubectl set env deployment/loadgenerator \
  TARGET="http://controllable-backend:5000/api/test" \
  RPS="20" \
  CONCURRENCY="15" \
  --overwrite -n default

kubectl rollout status deployment/loadgenerator -n default --timeout=60s
kubectl port-forward -n default svc/loadgenerator-metrics 8081:8080

curl -s -X POST http://127.0.0.1:8081/control \
  -H 'Content-Type: application/json' \
  -d '{"rps":20,"concurrency":15}'
```

## Capture Before State

```bash
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator -o wide
kubectl get pods -n default -o wide | grep -E 'controllable-backend|autoorch-webhook|loadgenerator'
kubectl get pods -n default -l app=controllable-backend \
  -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,CREATED:.metadata.creationTimestamp,PHASE:.status.phase,NODE:.spec.nodeName
kubectl get deploy -n default controllable-backend -o jsonpath='{.metadata.generation}{"\n"}{.status.observedGeneration}{"\n"}{.spec.template.metadata.annotations}{"\n"}'
```

Save to:

```text
outputs/before_state.txt
outputs/pod_identity_before.txt
outputs/deployment_annotations_before.txt
```

## Apply Route And Alert Rule

Delete any old temporary rule first to avoid stale firing state:

```bash
kubectl delete prometheusrule -n default autoorch-autorestart-fault --ignore-not-found
kubectl apply -f evidence/M7B_autorestart_real_action/manifests/alertmanagerconfig-autorestart.yaml
kubectl apply -f evidence/M7B_autorestart_real_action/manifests/prometheusrule-autorestart.yaml
```

## Trigger Restart-Like Fault

Port-forward the backend if needed:

```bash
kubectl port-forward -n default svc/controllable-backend 5000:5000
```

Then enable the fault:

```bash
curl -s -X POST "http://127.0.0.1:5000/inject-latency?ms=700"
curl -s -X POST http://127.0.0.1:5000/inject-errors
sleep 120
```

## Verify Feature Thresholds

Run Prometheus queries:

```bash
curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=sum(rate(http_requests_total{exported_endpoint="/api/test",status=~"5.."}[1m]))'

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[1m])) by (le))'

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=sum(rate(container_cpu_usage_seconds_total{namespace="default",pod=~"controllable-backend-.*",container!="POD"}[1m])) / 0.5'
```

Acceptance thresholds:

```text
http_5xx_rate >= 0.20
p95 > 0.50
cpu_sat < 0.70
```

Save to:

```text
outputs/prometheus_fault_metrics.txt
```

## Verify Alert And AutoOrch Decision

Check Prometheus/Alertmanager state:

```bash
curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=ALERTS{alertname="AutoOrchRestartFault"}'

curl -s http://127.0.0.1:9093/api/v2/alerts
```

Check AutoOrch logs:

```bash
kubectl logs -n default deploy/autoorch-webhook --tail=400
```

Required decision evidence:

```text
POST /alert
p_autoscale below threshold
p_restart >= 0.90
candidate_action=auto_restart
final_action=auto_restart
decision=auto_restart
reason=restart_confident
action_result.action=auto_restart
action_result.status=success
action_result.details.command includes ansible-playbook /app/playbooks/restart_deployment.yml
```

Save to:

```text
outputs/alertmanager_received_alert.txt
logs/autoorch_autorestart_real_action.log
outputs/autoorch_metrics_after.txt
```

After the first successful AutoRestart action is captured, delete the temporary PrometheusRule quickly so repeated Alertmanager posts do not turn a second candidate into `notify_human`:

```bash
kubectl delete prometheusrule -n default autoorch-autorestart-fault --ignore-not-found
```

## Verify Real Restart Happened

```bash
kubectl rollout status deployment/controllable-backend -n default --timeout=120s
kubectl get deploy -n default controllable-backend -o wide
kubectl get pods -n default -o wide | grep controllable-backend
kubectl get pods -n default -l app=controllable-backend \
  -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,CREATED:.metadata.creationTimestamp,PHASE:.status.phase,NODE:.spec.nodeName
kubectl get deploy -n default controllable-backend -o jsonpath='{.metadata.generation}{"\n"}{.status.observedGeneration}{"\n"}{.spec.template.metadata.annotations}{"\n"}'
```

Expected:

- Deployment remains available.
- A new pod is created or rollout annotation changes.
- Replicas remain `1/1`; this is restart, not scale.

Save to:

```text
outputs/restart_after_state.txt
outputs/pod_identity_after.txt
outputs/deployment_annotations_after.txt
```

## Cleanup

Disable faults:

```bash
curl -s -X POST "http://127.0.0.1:5000/inject-latency?ms=0"
curl -s http://127.0.0.1:5000/metrics | grep -E "error_injection_enabled|latency_injection_enabled"
```

If `error_injection_enabled 1.0`, toggle it off:

```bash
curl -s -X POST http://127.0.0.1:5000/inject-errors
curl -s http://127.0.0.1:5000/metrics | grep -E "error_injection_enabled|latency_injection_enabled"
```

Reset loadgenerator:

```bash
curl -s -X POST http://127.0.0.1:8081/control \
  -H 'Content-Type: application/json' \
  -d '{"rps":0,"concurrency":1}'

kubectl set env deployment/loadgenerator RPS="0" CONCURRENCY="1" --overwrite -n default
kubectl rollout status deployment/loadgenerator -n default --timeout=60s
```

Delete only the temporary firing rule:

```bash
kubectl delete prometheusrule -n default autoorch-autorestart-fault --ignore-not-found
```

Return AutoOrch to safe mode:

```bash
kubectl set env deployment/autoorch-webhook ACTION_MODE=stub --overwrite -n default
kubectl rollout status deployment/autoorch-webhook -n default --timeout=90s
```

Confirm final safety:

```bash
curl -s http://127.0.0.1:5000/metrics | grep -E "error_injection_enabled|latency_injection_enabled"
kubectl get deploy -n default autoorch-webhook controllable-backend loadgenerator
kubectl get prometheusrule -n default autoorch-autorestart-fault || true
kubectl port-forward -n default svc/autoorch-webhook 18080:8080
curl -s http://127.0.0.1:18080/health
```

Expected final state:

```text
error_injection_enabled 0.0
latency_injection_enabled 0.0
autoorch-webhook 1/1
controllable-backend 1/1
loadgenerator 1/1
ACTION_MODE=stub
```

## Summary Acceptance Criteria

M7B passes only if:

- `ACTION_MODE=ansible` during the real action window.
- Fault metrics satisfy the restart rule.
- Alertmanager forwards `AutoOrchRestartFault` to AutoOrch.
- AutoOrch logs show `candidate_action=auto_restart`.
- AutoOrch logs show `final_action=auto_restart`.
- AutoOrch logs show `reason=restart_confident`.
- `action_result.status=success`.
- The action command is Ansible-based.
- `controllable-backend` restarts successfully.
- Replicas remain `1/1`.
- Cleanup returns `ACTION_MODE=stub`.
- Fault toggles return to `0.0`.
- Temporary PrometheusRule is deleted.

## Commit Policy

After successful execution, commit only:

```text
evidence/M7B_autorestart_real_action/
```

Do not commit unrelated local files.
