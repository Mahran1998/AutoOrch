# M9 Manual Screenshot Checklist

Actual screenshots will be captured later in M12 after M9 is technically accepted.

## S-M9-1: Kubernetes State Before NoAction

Terminal command:

```bash
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
```

Capture when all deployments are healthy and `controllable-backend` has one replica.

Suggested filename:

```text
S_M9_1_kubernetes_state_before.png
```

Purpose: show the environment starts healthy.

## S-M9-2: Healthy Prometheus Metrics

Prometheus queries:

```promql
sum(rate(http_requests_total{exported_endpoint="/api/test"}[1m]))
```

```promql
(sum(rate(http_requests_total{exported_endpoint="/api/test",status=~"5.."}[1m])) or vector(0))
```

```promql
sum(rate(container_cpu_usage_seconds_total{namespace="default",pod=~"controllable-backend-.*",container!="POD"}[1m])) / 0.5
```

Capture when CPU and 5xx are low.

Suggested filename:

```text
S_M9_2_healthy_metrics.png
```

Purpose: show the alert is benign relative to live metrics.

## S-M9-3: Alertmanager Benign Alert

Alertmanager UI:

```text
AutoOrchNoActionBenign
```

Capture when the alert is active and routed to the AutoOrch receiver.

Suggested filename:

```text
S_M9_3_alertmanager_noaction_alert.png
```

Purpose: prove the alert route was used.

## S-M9-4: AutoOrch NoAction Log

Terminal command:

```bash
kubectl logs -n default deploy/autoorch-webhook --tail=400
```

Capture lines showing:

```text
p_autoscale < 0.90
p_restart < 0.90
candidate_action=no_action
final_action=no_action
reason=below_threshold
action_result.status=skipped
```

Suggested filename:

```text
S_M9_4_autoorch_noaction_log.png
```

Purpose: prove the ML decision suppressed remediation.

## S-M9-5: Replica And Pod Identity Unchanged

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
S_M9_5_no_infra_change.png
```

Purpose: prove no restart or scale happened.
