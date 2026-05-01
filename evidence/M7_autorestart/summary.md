# M7A AutoRestart Decision Proof

## Goal

Prove the AutoRestart decision path end to end without executing a real restart.

Expected path:

PrometheusRule `AutoOrchRestartFault` -> Alertmanager -> AutoOrch `POST /alert` -> Prometheus feature extraction -> restart model decision -> stubbed action result.

## Result

M7A passed after one safe parameter adjustment.

The first attempt used `RPS=30`, `CONCURRENCY=15`, and `LATENCY_MS=700`. It generated the correct restart-like metrics, but the restart model confidence was below the runtime threshold:

- `p_restart=0.7866666666666666`
- `candidate_action=no_action`
- `reason=below_threshold`

The second attempt changed one parameter only: `RPS=20` with `CONCURRENCY=15` and `LATENCY_MS=700`. This reduced CPU saturation and produced the expected AutoRestart decision:

- `http_5xx_rate=20.443394512084318`
- `p95=0.9741379310344827`
- `cpu_sat=0.28859644060096723`
- `p_autoscale=2.4050651419655286e-25`
- `p_restart=1.0`
- `candidate_action=auto_restart`
- `final_action=auto_restart`
- `decision=auto_restart`
- `reason=restart_confident`
- `action_result.status=simulated`

## Safety

`ACTION_MODE=stub` was confirmed before and after the test. No real remediation happened.

Post-test state:

- `controllable-backend`: `1/1`
- `autoorch-webhook`: `1/1`
- `loadgenerator`: `1/1`, reset to `RPS=0`, `CONCURRENCY=1`
- `AutoOrchRestartFault` PrometheusRule: deleted
- fault toggles: `error_injection_enabled=0.0`, `latency_injection_enabled=0.0`

The M7 AlertmanagerConfig route remains narrow and only matches `AutoOrchRestartFault` for `controllable-backend`.

## Thesis Note

This milestone proves the decision path, not the real restart action. The real remediation path is reserved for M7B after this evidence is reviewed.
