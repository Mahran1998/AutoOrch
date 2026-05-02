# M8A: AutoScale Decision Proof in Stub Mode

## Goal

Prove the AutoScale decision path through the real alert route without changing Kubernetes replica state.

Path proved:

```text
high-load condition
-> PrometheusRule AutoOrchScalePressure
-> Alertmanager
-> AutoOrch POST /alert
-> Prometheus feature extraction
-> autoscale model decision
-> ACTION_MODE=stub simulated action
```

## Result

M8A passed.

AutoOrch received `AutoOrchScalePressure` through Alertmanager and made an `auto_scale` decision in stub mode.

Key AutoOrch audit values:

```text
rps: 190.46596521365683
p95: 0.000950214253495715
http_5xx_rate: 0.0
cpu_sat: 1.7157971006035118
p_autoscale: 0.9203574706967853
candidate_action: auto_scale
final_action: auto_scale
decision: auto_scale
reason: autoscale_confident
action_result.status: simulated
```

## Replica Safety

`controllable-backend` replicas before M8A:

```text
READY=1
REPLICAS=1
AVAILABLE=1
```

`controllable-backend` replicas after M8A:

```text
READY=1
REPLICAS=1
AVAILABLE=1
```

This confirms that M8A proved the decision path only. No real scaling happened.

## Notes

An independent Prometheus sample taken after the AutoOrch decision still showed the alert firing and a CPU-bound backend:

```text
rps=184.85915492957744
p95=0.00095
http_5xx_rate=0.0
cpu_sat=1.6571915705565101
```

The offline probability calculated from that later sample was `0.8976990646880287`, slightly below the threshold because the load fluctuated after the decision. The accepted decision evidence is the AutoOrch audit line, which records the exact feature vector used by the live decision and `p_autoscale=0.9203574706967853`.

## Cleanup Confirmation

After M8A:

- loadgenerator reset to `RPS=0`, `CONCURRENCY=1`
- `ACTION_MODE` remained `stub`
- error injection remained `0.0`
- latency injection remained `0.0`
- `controllable-backend`, `autoorch-webhook`, and `loadgenerator` were all `1/1`
- temporary `AutoOrchScalePressure` PrometheusRule was deleted
- temporary `autoorch-m8-autoscale-route` AlertmanagerConfig was deleted
- no M8A port-forwards remained

## Recommendation

Proceed to M8B planning only. M8B should prepare narrow `deployments/scale` RBAC and then run one real scale remediation test after review.

