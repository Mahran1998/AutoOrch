# M8A Manual Screenshot Checklist

Actual screenshots will be captured later in M12 after M8A is technically accepted.

## S-M8A-1: Kubernetes State Before Decision

Terminal command:

```bash
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
```

Capture when all are `1/1`.

Suggested filename:

```text
S_M8A_1_kubernetes_state_before.png
```

Purpose: show the environment is healthy before the AutoScale decision test.

## S-M8A-2: Prometheus CPU Saturation

Prometheus query:

```promql
sum(rate(container_cpu_usage_seconds_total{namespace="default",pod=~"controllable-backend-.*",container!="POD"}[1m])) / 0.5
```

Capture when value is above `0.70`.

Suggested filename:

```text
S_M8A_2_cpu_saturation.png
```

Purpose: show the autoscale pressure signal.

## S-M8A-3: Prometheus 5xx Low

Prometheus query:

```promql
(sum(rate(http_requests_total{exported_endpoint="/api/test",status=~"5.."}[1m])) or vector(0))
```

Capture when value is below `0.20`.

Suggested filename:

```text
S_M8A_3_5xx_low.png
```

Purpose: show the condition is not a restart-like fault.

## S-M8A-4: Alertmanager AutoScale Alert

Alertmanager UI:

```text
AutoOrchScalePressure
```

Capture when the alert is active and routed to the AutoOrch receiver.

Suggested filename:

```text
S_M8A_4_alertmanager_autoscale_alert.png
```

Purpose: prove Alertmanager delivered the autoscale scenario.

## S-M8A-5: AutoOrch Decision Log

Terminal command:

```bash
kubectl logs -n default deploy/autoorch-webhook --tail=400
```

Capture lines showing:

```text
p_autoscale >= 0.90
candidate_action=auto_scale
final_action=auto_scale
reason=autoscale_confident
action_result.status=simulated
```

Suggested filename:

```text
S_M8A_5_autoorch_decision_log.png
```

Purpose: prove the ML decision without real scaling.

## S-M8A-6: Replica Count Unchanged

Terminal command:

```bash
kubectl get deploy -n default controllable-backend -o wide
```

Capture after the decision, showing replicas remain `1`.

Suggested filename:

```text
S_M8A_6_replicas_unchanged.png
```

Purpose: prove `ACTION_MODE=stub` prevented real remediation.

