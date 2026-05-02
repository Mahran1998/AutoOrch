# M8B AutoScale Real Action Evidence

## Goal

Prove the real AutoScale remediation path for `UC-01 Intelligent Alert Remediation with AutoOrch`.

Expected path:

```text
high CPU-bound backend load
-> PrometheusRule AutoOrchScalePressure
-> Alertmanager
-> AutoOrch POST /alert
-> autoscale model predicts auto_scale
-> ACTION_MODE=ansible
-> scale_deployment.yml
-> controllable-backend replicas 1 -> 2
-> cleanup restores replicas to 1 and ACTION_MODE=stub
```

## Result

Successful.

AutoOrch received `AutoOrchScalePressure` through Alertmanager, queried Prometheus, computed the four-feature vector, selected `auto_scale`, and executed the Ansible scale runbook successfully.

Decision evidence from AutoOrch audit log:

| Field | Value |
| --- | --- |
| `rps` | `175.3748110625434` |
| `p95` | `0.00095` |
| `http_5xx_rate` | `0.0` |
| `cpu_sat` | `1.828888305600777` |
| `p_autoscale` | `0.9403768541222671` |
| `candidate_action` | `auto_scale` |
| `final_action` | `auto_scale` |
| `reason` | `autoscale_confident` |
| `action_result.status` | `success` |
| `desired_replicas` | `2` |

Kubernetes state changed as expected:

```text
Before action: replicas 1/1/1
After action:  replicas 2/2/2
Cleanup:       replicas 1/1/1
```

The second backend pod created by the scale action was:

```text
controllable-backend-cf9f896c8-rgx22
UID f5a01fe1-6be1-451c-bc1a-045aae9efa34
created 2026-05-02T14:15:57Z
```

## Safety

- Real action was scoped to `deployment/controllable-backend` in namespace `default`.
- `ACTION_MODE=ansible` was used only during the execution window.
- The temporary `AutoOrchScalePressure` PrometheusRule was deleted immediately after the first successful scale action.
- Cleanup restored `ACTION_MODE=stub`.
- Cleanup restored `controllable-backend` replicas to `1`.
- Cleanup reset loadgenerator to `RPS=0`, `CONCURRENCY=1`.
- Fault injection stayed disabled: `error_injection_enabled 0.0`, `latency_injection_enabled 0.0`.

## Thesis Use

This evidence supports the AutoScale alternative flow of the main use case:

```text
UC-01 Intelligent Alert Remediation with AutoOrch
Alternative Flow B: AutoScale
```

It proves AutoOrch can move from an alert to an ML decision and then to real Kubernetes remediation through an Ansible runbook.
