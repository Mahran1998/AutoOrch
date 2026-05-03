# M12 Manual Thesis Screenshot Capture Runbook

## Goal

Capture clean thesis screenshots for the final AutoOrch use case evidence.

M12 is not a new proof phase. M6 through M10 already proved the implementation through logs, manifests, outputs, and command evidence. M12 is for selecting readable screenshots for the thesis.

## Ground Rules

- Do not retrain models.
- Do not change runtime code.
- Do not modify architecture.
- Do not commit screenshots until reviewed.
- Prefer clean terminal screenshots with a large font.
- Use formatted thesis code snippets instead of screenshots of code.
- Use screenshots for Prometheus, Alertmanager, terminal logs, metrics, and Kubernetes state.
- Run one checkpoint at a time.
- After each checkpoint, verify cleanup before moving on.

## Screenshot Quality Checklist

- Use browser zoom around 125%.
- Use terminal font large enough to read in Word.
- Capture only the relevant window or area, not the full desktop.
- Avoid personal folders, unrelated pods, browser bookmarks, or private data.
- Keep filenames exactly as listed in the runbook.
- After each checkpoint, show the screenshot or output for review before continuing.

## Screenshot Output Folders

Save manual screenshots under:

```text
evidence/_screenshots/M6_alertmanager_route/
evidence/_screenshots/M7B_autorestart_real_action/
evidence/_screenshots/M8B_autoscale_real_action/
evidence/_screenshots/M9_noaction/
evidence/_screenshots/M10_notifyhuman/
```

## Risk Levels

| Checkpoint | Risk | Notes |
| --- | --- | --- |
| M12-Prep | Low | Opens port-forwards and verifies clean state |
| M12-1 M6 routing | Low | Uses synthetic routing alert only |
| M12-2 M7B AutoRestart | Medium | Real restart screenshot requires rerunning restart action |
| M12-3 M8B AutoScale | Medium | Real scale screenshot requires rerunning scale action |
| M12-4 M9 NoAction | Low | Stub/skipped action only |
| M12-5 M10 NotifyHuman | Low to medium | Stub mode, but uses fault injection and repeated alerts |
| M12-Final | Low | Inventory and cleanup verification |

Safest order:

```text
M12-Prep -> M12-1 -> M12-4 -> M12-5 -> M12-2 -> M12-3 -> M12-Final
```

This captures low-risk screenshots first and leaves the real restart/scale reruns for last.

## M12-Prep: Clean Environment And UI Access

### Purpose

Open the local UI access points and verify the cluster starts from a clean state.

### Required Starting State

- `ACTION_MODE=stub`
- no fault injection
- loadgenerator idle
- `controllable-backend` is `1/1`
- `autoorch-webhook` is `1/1`
- Alertmanager and Prometheus are reachable

### Commands

Terminal 1:

```bash
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-prometheus 9090:9090
```

Terminal 2:

```bash
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-alertmanager 9093:9093
```

Terminal 3:

```bash
kubectl port-forward -n default svc/autoorch-webhook 18080:8080
```

Terminal 4:

```bash
kubectl port-forward -n default svc/controllable-backend 5000:5000
```

Optional terminal 5, needed for loadgenerator control:

```bash
kubectl port-forward -n default svc/loadgenerator-metrics 8081:8080
```

Clean-state verification:

```bash
mkdir -p evidence/_screenshots/M6_alertmanager_route \
  evidence/_screenshots/M7B_autorestart_real_action \
  evidence/_screenshots/M8B_autoscale_real_action \
  evidence/_screenshots/M9_noaction \
  evidence/_screenshots/M10_notifyhuman

kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
kubectl get pods -n monitoring | grep -E "prometheus|alertmanager"
kubectl get deployment autoorch-webhook -n default -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="ACTION_MODE")].value}{"\n"}'
curl -s http://127.0.0.1:5000/metrics | grep -E "error_injection_enabled|latency_injection_enabled"
kubectl get prometheusrule -n default
```

### UI URLs

- Prometheus: <http://127.0.0.1:9090>
- Prometheus alerts: <http://127.0.0.1:9090/alerts>
- Alertmanager: <http://127.0.0.1:9093>
- AutoOrch health: <http://127.0.0.1:18080/health>
- AutoOrch metrics: <http://127.0.0.1:18080/metrics>
- Backend metrics: <http://127.0.0.1:5000/metrics>

### Screenshot

Filename:

```text
evidence/_screenshots/M6_alertmanager_route/Figure_M12_Prep_environment_ready.png
```

Capture:

```bash
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
kubectl get pods -n monitoring | grep -E "prometheus|alertmanager"
```

Thesis purpose: show the evaluation environment is running.

## M12-1: M6 Alertmanager Routing Screenshots

### Purpose

Show that Prometheus alerts route through Alertmanager into AutoOrch.

### Starting State

- Keep `ACTION_MODE=stub`.
- No fault injection required.
- Do not run restart or scale.

### Commands

Apply the M6 route and synthetic test rule:

```bash
kubectl apply -f evidence/M6B_alertmanager_route/manifests/alertmanagerconfig-autoorch.yaml
kubectl apply -f evidence/M6B_alertmanager_route/manifests/prometheusrule-autoorch-m6-test.yaml
sleep 45
```

Check Prometheus and AutoOrch:

```bash
curl -sG http://127.0.0.1:9090/api/v1/query --data-urlencode 'query=ALERTS{alertname="AutoOrchM6TestAlert"}'
kubectl logs -n default deploy/autoorch-webhook --tail=120
curl -s http://127.0.0.1:18080/metrics | grep autoorch
```

### Screenshots

1. Prometheus alert firing

Open:

```text
http://127.0.0.1:9090/alerts
```

Capture when `AutoOrchM6TestAlert` is firing.

Filename:

```text
evidence/_screenshots/M6_alertmanager_route/Figure_M6_01_prometheus_alert_firing.png
```

Caption idea: Prometheus test alert used to verify the AutoOrch alert route.

2. Alertmanager received alert

Open:

```text
http://127.0.0.1:9093
```

Capture when `AutoOrchM6TestAlert` is visible.

Filename:

```text
evidence/_screenshots/M6_alertmanager_route/Figure_M6_02_alertmanager_route.png
```

Caption idea: Alertmanager received the test alert and routed it to the AutoOrch receiver.

3. AutoOrch log

Command:

```bash
kubectl logs -n default deploy/autoorch-webhook --tail=120
```

Capture lines showing `POST /alert`, `candidate_action=no_action`, and `action_result.status=skipped`.

Filename:

```text
evidence/_screenshots/M6_alertmanager_route/Figure_M6_03_autoorch_received_alert.png
```

4. AutoOrch metrics

Command:

```bash
curl -s http://127.0.0.1:18080/metrics | grep autoorch
```

Filename:

```text
evidence/_screenshots/M6_alertmanager_route/Figure_M6_04_autoorch_metrics.png
```

### Cleanup

```bash
kubectl delete prometheusrule -n default autoorch-m6-test-alert --ignore-not-found
kubectl get prometheusrule -n default
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
```

Leave the M6 AlertmanagerConfig if it already existed from prior evidence. Delete it only if you intentionally created a temporary duplicate.

## M12-4: M9 NoAction Screenshots

### Purpose

Show that AutoOrch suppresses benign/noisy alerts when live metrics are healthy.

### Starting State

- `ACTION_MODE=stub`
- faults off
- loadgenerator low or idle
- backend `1/1`

### Commands

Set low healthy load:

```bash
kubectl set env deployment/loadgenerator TARGET=http://controllable-backend:5000/api/test RPS=10 CONCURRENCY=5 --overwrite -n default
kubectl rollout status deployment/loadgenerator -n default --timeout=60s
sleep 90
```

Apply M9 rule and route:

```bash
kubectl apply -f evidence/M9_noaction/manifests/alertmanagerconfig-noaction.yaml
kubectl apply -f evidence/M9_noaction/manifests/prometheusrule-noaction.yaml
sleep 45
```

### Prometheus Queries

Use Prometheus graph UI:

```promql
sum(rate(http_requests_total{exported_endpoint="/api/test"}[1m]))
```

```promql
(sum(rate(http_requests_total{exported_endpoint="/api/test",status=~"5.."}[1m])) or vector(0))
```

```promql
sum(rate(container_cpu_usage_seconds_total{namespace="default",pod=~"controllable-backend-.*",container!="POD"}[1m])) / 0.5
```

### Screenshots

1. Healthy metrics

Filename:

```text
evidence/_screenshots/M9_noaction/Figure_M9_01_healthy_metrics.png
```

Capture low 5xx and low CPU.

2. Benign alert

Open:

```text
http://127.0.0.1:9090/alerts
```

Capture `AutoOrchNoActionBenign`.

Filename:

```text
evidence/_screenshots/M9_noaction/Figure_M9_02_benign_alert.png
```

3. AutoOrch no_action log

```bash
kubectl logs -n default deploy/autoorch-webhook --tail=400
```

Capture:

```text
p_autoscale < 0.90
p_restart < 0.90
candidate_action=no_action
final_action=no_action
reason=below_threshold
action_result.status=skipped
```

Filename:

```text
evidence/_screenshots/M9_noaction/Figure_M9_03_noaction_decision.png
```

4. No infrastructure change

```bash
kubectl get deployment controllable-backend -n default -o jsonpath='{.spec.replicas}{"\n"}{.status.readyReplicas}{"\n"}{.status.availableReplicas}{"\n"}'
kubectl get pods -n default -l app=controllable-backend -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,CREATED:.metadata.creationTimestamp,PHASE:.status.phase,NODE:.spec.nodeName
```

Filename:

```text
evidence/_screenshots/M9_noaction/Figure_M9_04_no_infra_change.png
```

### Cleanup

```bash
kubectl delete prometheusrule -n default autoorch-noaction-benign --ignore-not-found
kubectl delete alertmanagerconfig -n default autoorch-m9-noaction-route --ignore-not-found
kubectl set env deployment/loadgenerator TARGET=http://controllable-backend:5000/api/test RPS=0 CONCURRENCY=1 --overwrite -n default
kubectl rollout status deployment/loadgenerator -n default --timeout=60s
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
curl -s http://127.0.0.1:5000/metrics | grep -E "error_injection_enabled|latency_injection_enabled"
```

## M12-5: M10 NotifyHuman Screenshots

### Purpose

Show that repeated automation candidates are escalated to `notify_human` instead of repeated remediation.

### Starting State

- `ACTION_MODE=stub`
- faults off
- backend `1/1`
- AutoOrch memory should be clean

### Commands

Reset AutoOrch in-memory streaks:

```bash
kubectl rollout restart deployment/autoorch-webhook -n default
kubectl rollout status deployment/autoorch-webhook -n default --timeout=90s
```

Activate restart-like load:

```bash
kubectl set env deployment/loadgenerator TARGET=http://controllable-backend:5000/api/test RPS=20 CONCURRENCY=15 --overwrite -n default
kubectl rollout status deployment/loadgenerator -n default --timeout=60s
curl -s -X POST http://127.0.0.1:5000/inject-latency?ms=700
curl -s -X POST http://127.0.0.1:5000/inject-errors
sleep 90
```

Apply first alert:

```bash
kubectl apply -f evidence/M10_notifyhuman/manifests/alertmanagerconfig-notifyhuman.yaml
kubectl apply -f evidence/M10_notifyhuman/manifests/prometheusrule-notifyhuman-first.yaml
sleep 45
kubectl logs -n default deploy/autoorch-webhook --tail=250
```

Delete first rule and apply second alert inside 300 seconds:

```bash
kubectl delete prometheusrule -n default autoorch-notifyhuman-restart-first --ignore-not-found
kubectl apply -f evidence/M10_notifyhuman/manifests/prometheusrule-notifyhuman-second.yaml
sleep 90
kubectl logs -n default deploy/autoorch-webhook --tail=500
```

### Screenshots

1. Restart-like metrics

Prometheus queries:

```promql
sum(rate(http_requests_total{exported_endpoint="/api/test",status=~"5.."}[1m]))
```

```promql
histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[1m])) by (le))
```

```promql
sum(rate(container_cpu_usage_seconds_total{namespace="default",pod=~"controllable-backend-.*",container!="POD"}[1m])) / 0.5
```

Filename:

```text
evidence/_screenshots/M10_notifyhuman/Figure_M10_01_restart_like_metrics.png
```

2. First candidate

Capture log showing:

```text
candidate_action=auto_restart
final_action=auto_restart
reason=restart_confident
action_result.status=simulated
```

Filename:

```text
evidence/_screenshots/M10_notifyhuman/Figure_M10_02_first_autorestart_candidate.png
```

3. NotifyHuman escalation

Capture log showing:

```text
candidate_action=auto_restart
final_action=notify_human
reason=repeated_action
escalation.consecutive_count=2
action_result.action=notify_human
```

Filename:

```text
evidence/_screenshots/M10_notifyhuman/Figure_M10_03_notifyhuman_escalation.png
```

4. NotifyHuman metric

Prometheus query:

```promql
autoorch_notify_human_total
```

or terminal:

```bash
curl -s http://127.0.0.1:18080/metrics | grep -E "autoorch_notify_human_total|autoorch_decisions_total|autoorch_actions_total"
```

Filename:

```text
evidence/_screenshots/M10_notifyhuman/Figure_M10_04_notifyhuman_metric.png
```

5. No infrastructure change

```bash
kubectl get deployment controllable-backend -n default -o jsonpath='{.spec.replicas}{"\n"}{.status.readyReplicas}{"\n"}{.status.availableReplicas}{"\n"}'
kubectl get pods -n default -l app=controllable-backend -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,CREATED:.metadata.creationTimestamp,PHASE:.status.phase,NODE:.spec.nodeName
```

Filename:

```text
evidence/_screenshots/M10_notifyhuman/Figure_M10_05_no_infra_change.png
```

### Cleanup

```bash
kubectl delete prometheusrule -n default autoorch-notifyhuman-restart-first --ignore-not-found
kubectl delete prometheusrule -n default autoorch-notifyhuman-restart-second --ignore-not-found
kubectl delete alertmanagerconfig -n default autoorch-m10-notifyhuman-route --ignore-not-found
curl -s -X POST http://127.0.0.1:5000/inject-latency?ms=0
curl -s http://127.0.0.1:5000/metrics | grep error_injection_enabled
```

If `error_injection_enabled 1.0`, toggle it off:

```bash
curl -s -X POST http://127.0.0.1:5000/inject-errors
```

Finish cleanup:

```bash
kubectl set env deployment/loadgenerator TARGET=http://controllable-backend:5000/api/test RPS=0 CONCURRENCY=1 --overwrite -n default
kubectl rollout status deployment/loadgenerator -n default --timeout=60s
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
curl -s http://127.0.0.1:5000/metrics | grep -E "error_injection_enabled|latency_injection_enabled"
```

## M12-2: M7B AutoRestart Real Action Screenshots

### Purpose

Capture the real AutoRestart remediation path.

### Important Risk

This checkpoint intentionally allows a real restart of `deployment/controllable-backend`. Run it only after you approve real action for screenshots.

### Starting State

- backend `1/1`
- faults off
- loadgenerator idle
- `ACTION_MODE=stub` before starting

### Commands

Switch AutoOrch to Ansible mode for the action window:

```bash
kubectl set env deployment/autoorch-webhook ACTION_MODE=ansible --overwrite -n default
kubectl rollout status deployment/autoorch-webhook -n default --timeout=90s
curl -s http://127.0.0.1:18080/health
```

Capture pod identity before:

```bash
kubectl get pods -n default -l app=controllable-backend -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,CREATED:.metadata.creationTimestamp,PHASE:.status.phase,NODE:.spec.nodeName
```

Activate restart-like fault:

```bash
kubectl set env deployment/loadgenerator TARGET=http://controllable-backend:5000/api/test RPS=20 CONCURRENCY=15 --overwrite -n default
kubectl rollout status deployment/loadgenerator -n default --timeout=60s
curl -s -X POST http://127.0.0.1:5000/inject-latency?ms=700
curl -s -X POST http://127.0.0.1:5000/inject-errors
sleep 90
```

Apply M7B route and rule:

```bash
kubectl apply -f evidence/M7B_autorestart_real_action/manifests/alertmanagerconfig-autorestart.yaml
kubectl apply -f evidence/M7B_autorestart_real_action/manifests/prometheusrule-autorestart.yaml
sleep 90
```

### Screenshots

1. Restart-like Prometheus metrics

Use the same M10 restart-like Prometheus queries.

Filename:

```text
evidence/_screenshots/M7B_autorestart_real_action/Figure_M7B_01_restart_metrics.png
```

2. AutoRestart alert

Open:

```text
http://127.0.0.1:9090/alerts
```

Capture `AutoOrchRestartFault`.

Filename:

```text
evidence/_screenshots/M7B_autorestart_real_action/Figure_M7B_02_autorestart_alert.png
```

3. AutoOrch decision and Ansible action

```bash
kubectl logs -n default deploy/autoorch-webhook --tail=500
```

Capture:

```text
p_restart=1.0
final_action=auto_restart
reason=restart_confident
action_result.status=success
ansible-playbook /app/playbooks/restart_deployment.yml
```

Filename:

```text
evidence/_screenshots/M7B_autorestart_real_action/Figure_M7B_03_autorestart_action_log.png
```

4. Restart result

```bash
kubectl rollout status deployment/controllable-backend -n default
kubectl get pods -n default -l app=controllable-backend -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,CREATED:.metadata.creationTimestamp,PHASE:.status.phase,NODE:.spec.nodeName
```

Filename:

```text
evidence/_screenshots/M7B_autorestart_real_action/Figure_M7B_04_restart_result.png
```

### Cleanup

```bash
kubectl delete prometheusrule -n default autoorch-autorestart-fault --ignore-not-found
curl -s -X POST http://127.0.0.1:5000/inject-latency?ms=0
curl -s http://127.0.0.1:5000/metrics | grep error_injection_enabled
```

If `error_injection_enabled 1.0`, toggle it off:

```bash
curl -s -X POST http://127.0.0.1:5000/inject-errors
```

Reset mode and load:

```bash
kubectl set env deployment/autoorch-webhook ACTION_MODE=stub --overwrite -n default
kubectl rollout status deployment/autoorch-webhook -n default --timeout=90s
kubectl set env deployment/loadgenerator TARGET=http://controllable-backend:5000/api/test RPS=0 CONCURRENCY=1 --overwrite -n default
kubectl rollout status deployment/loadgenerator -n default --timeout=60s
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
curl -s http://127.0.0.1:5000/metrics | grep -E "error_injection_enabled|latency_injection_enabled"
```

## M12-3: M8B AutoScale Real Action Screenshots

### Purpose

Capture the real AutoScale remediation path.

### Important Risk

This checkpoint intentionally allows real scaling of `deployment/controllable-backend` from `1` to `2` replicas. Run it only after you approve real action for screenshots.

### Starting State

- backend replicas `1`
- faults off
- loadgenerator idle
- `ACTION_MODE=stub` before starting

### Commands

Switch AutoOrch to Ansible mode:

```bash
kubectl set env deployment/autoorch-webhook ACTION_MODE=ansible --overwrite -n default
kubectl rollout status deployment/autoorch-webhook -n default --timeout=90s
```

Capture before scale:

```bash
kubectl get deploy -n default controllable-backend -o wide
kubectl get pods -n default -l app=controllable-backend -o wide
```

Start calibrated autoscale load:

```bash
kubectl set env deployment/loadgenerator TARGET=http://controllable-backend:5000/api/test RPS=500 CONCURRENCY=75 --overwrite -n default
kubectl rollout status deployment/loadgenerator -n default --timeout=60s
sleep 120
```

Apply M8B route and rule:

```bash
kubectl apply -f evidence/M8B_autoscale_real_action/manifests/alertmanagerconfig-autoscale.yaml
kubectl apply -f evidence/M8B_autoscale_real_action/manifests/prometheusrule-autoscale.yaml
sleep 90
```

### Screenshots

1. Replicas before scale

Filename:

```text
evidence/_screenshots/M8B_autoscale_real_action/Figure_M8B_01_replicas_before.png
```

2. AutoScale pressure metrics

Prometheus queries:

```promql
sum(rate(container_cpu_usage_seconds_total{namespace="default",pod=~"controllable-backend-.*",container!="POD"}[1m])) / 0.5
```

```promql
(sum(rate(http_requests_total{exported_endpoint="/api/test",status=~"5.."}[1m])) or vector(0))
```

Capture CPU saturation above `0.70` and 5xx below `0.20`.

Filename:

```text
evidence/_screenshots/M8B_autoscale_real_action/Figure_M8B_02_autoscale_metrics.png
```

3. AutoScale decision and Ansible action

```bash
kubectl logs -n default deploy/autoorch-webhook --tail=500
```

Capture:

```text
p_autoscale >= 0.90
final_action=auto_scale
action_result.status=success
desired_replicas=2
ansible-playbook /app/playbooks/scale_deployment.yml
```

Filename:

```text
evidence/_screenshots/M8B_autoscale_real_action/Figure_M8B_03_autoscale_action_log.png
```

4. Replicas after scale

```bash
kubectl get deploy -n default controllable-backend -o wide
kubectl get pods -n default -l app=controllable-backend -o wide
```

Capture when replicas are `2`.

Filename:

```text
evidence/_screenshots/M8B_autoscale_real_action/Figure_M8B_04_replicas_after.png
```

### Cleanup

```bash
kubectl delete prometheusrule -n default autoorch-autoscale-pressure --ignore-not-found
kubectl set env deployment/loadgenerator TARGET=http://controllable-backend:5000/api/test RPS=0 CONCURRENCY=1 --overwrite -n default
kubectl rollout status deployment/loadgenerator -n default --timeout=60s
kubectl scale deployment/controllable-backend --replicas=1 -n default
kubectl rollout status deployment/controllable-backend -n default --timeout=90s
kubectl set env deployment/autoorch-webhook ACTION_MODE=stub --overwrite -n default
kubectl rollout status deployment/autoorch-webhook -n default --timeout=90s
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
curl -s http://127.0.0.1:5000/metrics | grep -E "error_injection_enabled|latency_injection_enabled"
```

Final screenshot:

```text
evidence/_screenshots/M8B_autoscale_real_action/Figure_M8B_05_cleanup_final_state.png
```

## M12-Final: Screenshot Inventory And Cleanup

### Purpose

Verify screenshot filenames and ensure the cluster is safe.

### Commands

```bash
find evidence/_screenshots -maxdepth 2 -type f | sort
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
kubectl get prometheusrule -n default
kubectl get deployment autoorch-webhook -n default -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="ACTION_MODE")].value}{"\n"}'
curl -s http://127.0.0.1:5000/metrics | grep -E "error_injection_enabled|latency_injection_enabled"
```

### Expected Final State

```text
ACTION_MODE=stub
error_injection_enabled 0.0
latency_injection_enabled 0.0
controllable-backend 1/1
autoorch-webhook 1/1
loadgenerator 1/1
no temporary M12 PrometheusRule resources in default namespace
```

### Inventory File

After screenshots are reviewed, create:

```text
evidence/_screenshots/SCREENSHOT_INDEX.md
```

Do not commit screenshots or the index until reviewed.
