# M8B Manual Screenshot Checklist

Actual screenshots will be captured later in M12 after M8B is technically accepted.

## S-M8B-1: Replicas Before Scale

```bash
kubectl get deploy -n default controllable-backend -o wide
```

Capture when replicas are `1`.

Suggested filename:

```text
S_M8B_1_replicas_before.png
```

## S-M8B-2: AutoScale Pressure Metrics

Prometheus queries:

```promql
sum(rate(container_cpu_usage_seconds_total{namespace="default",pod=~"controllable-backend-.*",container!="POD"}[1m])) / 0.5
```

```promql
(sum(rate(http_requests_total{exported_endpoint="/api/test",status=~"5.."}[1m])) or vector(0))
```

Capture CPU saturation above `0.70` and 5xx below `0.20`.

Suggested filename:

```text
S_M8B_2_autoscale_metrics.png
```

## S-M8B-3: AutoOrch Real Scale Decision

```bash
kubectl logs -n default deploy/autoorch-webhook --tail=500
```

Capture lines showing:

```text
p_autoscale >= 0.90
candidate_action=auto_scale
final_action=auto_scale
action_result.status=success
desired_replicas=2
ansible-playbook /app/playbooks/scale_deployment.yml
```

Suggested filename:

```text
S_M8B_3_autoorch_real_scale_log.png
```

## S-M8B-4: Replicas After Scale

```bash
kubectl get deploy -n default controllable-backend -o wide
kubectl get pods -n default -l app=controllable-backend -o wide
```

Capture when replicas are `2`.

Suggested filename:

```text
S_M8B_4_replicas_after.png
```

## S-M8B-5: Cleanup Back to One Replica

```bash
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
```

Capture final state after cleanup:

```text
controllable-backend 1/1
autoorch-webhook 1/1
loadgenerator 1/1
```

Suggested filename:

```text
S_M8B_5_cleanup_final_state.png
```

