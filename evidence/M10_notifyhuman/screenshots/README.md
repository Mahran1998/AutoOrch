# M10 Manual Screenshot Checklist

Actual screenshots will be captured later in M12 after M10 is technically accepted.

## S-M10-1: Kubernetes State Before NotifyHuman

Terminal command:

```bash
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
```

Capture when all are healthy and `controllable-backend` has one replica.

Suggested filename:

```text
S_M10_1_kubernetes_state_before.png
```

Purpose: show the environment starts safe.

## S-M10-2: Restart-Like Metrics

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

Capture when 5xx and p95 are high, while CPU is below the autoscale overload threshold.

Suggested filename:

```text
S_M10_2_restart_like_metrics.png
```

Purpose: show the metrics would normally support an AutoRestart candidate.

## S-M10-3: Alertmanager M10 Alerts

Alertmanager UI:

```text
AutoOrchNotifyHumanRestartFaultFirst
AutoOrchNotifyHumanRestartFaultSecond
```

Capture when the alerts are active and routed to the AutoOrch receiver.

Suggested filename:

```text
S_M10_3_alertmanager_m10_alerts.png
```

Purpose: prove the escalation test uses the alert route.

## S-M10-4: First AutoRestart Candidate

Terminal command:

```bash
kubectl logs -n default deploy/autoorch-webhook --tail=600
```

Capture the first audit showing:

```text
candidate_action=auto_restart
final_action=auto_restart
reason=restart_confident
action_result.status=simulated
```

Suggested filename:

```text
S_M10_4_first_autorestart_candidate.png
```

Purpose: show the first automation candidate.

## S-M10-5: NotifyHuman Escalation

Terminal command:

```bash
kubectl logs -n default deploy/autoorch-webhook --tail=600
```

Capture the second audit showing:

```text
candidate_action=auto_restart
final_action=notify_human
reason=repeated_action
escalation.consecutive_count=2
action_result.action=notify_human
```

Suggested filename:

```text
S_M10_5_notifyhuman_escalation.png
```

Purpose: prove AutoOrch blocks repeated automation and escalates to a human.

## S-M10-6: NotifyHuman Metric

AutoOrch `/metrics` or Prometheus query:

```promql
autoorch_notify_human_total
```

Capture when value is at least `1`.

Suggested filename:

```text
S_M10_6_notifyhuman_metric.png
```

Purpose: show observable notify_human signal.

## S-M10-7: No Infrastructure Change

Terminal commands:

```bash
kubectl get deployment controllable-backend -n default \
  -o jsonpath='{.spec.replicas}{"\n"}{.status.readyReplicas}{"\n"}{.status.availableReplicas}{"\n"}'

kubectl get pods -n default -l app=controllable-backend \
  -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,CREATED:.metadata.creationTimestamp,PHASE:.status.phase,NODE:.spec.nodeName
```

Capture before/after output showing the same pod UID and one replica.

Suggested filename:

```text
S_M10_7_no_infra_change.png
```

Purpose: prove no second remediation happened.
