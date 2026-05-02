# M8-Calibrate: AutoScale Feasibility Calibration

## Goal

Determine whether the current `controllable-backend` can naturally produce an autoscale-like feature pattern before running M8A.

Target pattern:

- high enough request load
- `cpu_sat >= 0.70`
- `http_5xx_rate < 0.20`
- `P(auto_scale) >= 0.90`
- no artificial latency injection
- no error injection

## Boundaries

- `ACTION_MODE` remained `stub`.
- No AutoScale alert rule was applied.
- No real scaling was performed.
- No RBAC changes were made.
- No model retraining was performed.
- No backend code or architecture changes were made.

## Result

The current backend is sufficient for M8A.

The successful calibration point was Trial 3:

- target load: `RPS=500`, `CONCURRENCY=75`
- measured RPS: `132.0316`
- p95: `0.000950`
- `http_5xx_rate`: `0.0`
- `cpu_sat`: `1.8840`
- CPU limit: `0.5`
- `P(auto_scale)`: `0.9311`

This satisfies the M8-Calibrate acceptance target:

- `cpu_sat >= 0.70`: yes
- `http_5xx_rate < 0.20`: yes
- `P(auto_scale) >= 0.90`: yes

## Interpretation

The backend reaches CPU saturation under load without error or latency injection. Measured RPS does not reach the configured target because the single backend pod becomes CPU-bound, which is exactly the autoscale-relevant condition. The p95 value stayed low, which is acceptable because high p95 is not required for the autoscale model.

## Recommendation

Proceed to M8A: AutoScale decision proof in `ACTION_MODE=stub`.

Recommended M8A load point:

- `RPS=500`
- `CONCURRENCY=75`
- errors OFF
- latency OFF

Recommended temporary alert condition should focus on:

- `cpu_sat >= 0.70`
- `http_5xx_rate < 0.20`
- optional RPS guard around `>= 100`

Do not proceed to M8B real scaling until M8A proves `candidate_action=auto_scale` and `final_action=auto_scale` through Alertmanager with `ACTION_MODE=stub`.

## Cleanup Confirmation

After calibration:

- loadgenerator reset to `RPS=0`, `CONCURRENCY=1`
- error injection remained `0.0`
- latency injection remained `0.0`
- `ACTION_MODE` remained `stub`
- `controllable-backend`, `autoorch-webhook`, and `loadgenerator` were all `1/1`
- no default namespace PrometheusRule remained
- no calibration port-forwards remained

