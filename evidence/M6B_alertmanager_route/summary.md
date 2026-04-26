# M6B Alertmanager Route Evidence

## Goal

Verify the production-like alert routing path:

PrometheusRule -> Alertmanager -> AutoOrch `POST /alert`

This M6 evidence run intentionally did not test AutoRestart or AutoScale remediation. It only proves that the monitoring and webhook components can route an alert into AutoOrch and that AutoOrch can compute the runtime feature vector.

## Result

Successful.

AutoOrch received `AutoOrchM6TestAlert` through Alertmanager, queried Prometheus, computed the four-feature vector, selected `no_action`, and skipped remediation.

Captured decision:

- `alertname`: `AutoOrchM6TestAlert`
- `receiver`: `default/autoorch-m6-test-route/autoorch-webhook`
- `features`: `rps`, `p95`, `http_5xx_rate`, `cpu_sat`
- `candidate_action`: `no_action`
- `final_action`: `no_action`
- `decision`: `no_action`
- `reason`: `below_threshold`
- `action_result.status`: `skipped`

## Safety

- `ACTION_MODE=stub`
- no real restart was executed
- no real scale was executed
- `controllable-backend` remained available as `1/1`
- `autoorch-webhook` remained available as `1/1`

The temporary always-firing `AutoOrchM6TestAlert` PrometheusRule was deleted after capture to avoid repeated test alerts.

## Thesis Use

This evidence supports the use-case claim that AutoOrch is wired as an alert-to-decision pipeline:

Prometheus detects an alert, Alertmanager forwards it to AutoOrch, AutoOrch queries current metrics, the ML decision path evaluates the features, and the safety executor skips remediation when the decision is `no_action`.
