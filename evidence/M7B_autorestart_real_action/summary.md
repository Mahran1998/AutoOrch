# M7B AutoRestart Real Action Summary

## Goal

Prove the real AutoRestart remediation path:

PrometheusRule `AutoOrchRestartFault` -> Alertmanager -> AutoOrch `POST /alert` -> Prometheus feature extraction -> restart model decision -> Ansible runbook -> Kubernetes deployment restart.

## Result

M7B passed after a focused runtime safeguard.

The clean run produced a real restart of `deployment/controllable-backend` in namespace `default` using:

```text
ansible-playbook /app/playbooks/restart_deployment.yml -e namespace=default -e workload=controllable-backend
```

AutoOrch selected:

```text
candidate_action=auto_restart
final_action=auto_restart
decision=auto_restart
reason=restart_confident
p_restart=1.0
action_result.status=success
```

The backend pod identity changed from:

```text
controllable-backend-75d6db8655-snr69
UID 80b27ff3-ccf7-43be-b678-2cd7557b2e72
CREATED 2026-05-01T20:34:01Z
```

to:

```text
controllable-backend-cf9f896c8-w2bbs
UID dedf5ab0-f8a7-45c9-b41d-ad83421ccd93
CREATED 2026-05-01T20:43:38Z
```

The deployment annotation also changed to:

```text
kubectl.kubernetes.io/restartedAt: 2026-05-01T20:43:38Z
```

## Fault Metrics

During the clean run:

```text
http_5xx_rate: 19.396551724137932
p95: 0.9830508474576272
cpu_sat: 0.24378081848011385
```

These satisfy the restart rule:

```text
http_5xx_rate >= 0.20
p95 > 0.50
cpu_sat < 0.70
```

## Safety Notes

The first real attempt successfully ran Ansible, but exposed a runtime issue: the webhook process was too sensitive to probe/Alertmanager timeouts during a blocking Ansible action, which led to a second backend rollout. Before the clean rerun, the deployment probe budget was increased and the M7B AlertmanagerConfig webhook timeout was set to 30 seconds.

The clean rerun completed without AutoOrch liveness failure during the action window.

Final cleanup confirmed:

```text
ACTION_MODE=stub
error_injection_enabled 0.0
latency_injection_enabled 0.0
loadgenerator RPS=0
loadgenerator CONCURRENCY=1
temporary PrometheusRule deleted
autoorch-webhook 1/1
controllable-backend 1/1
loadgenerator 1/1
```

## Thesis Use

This milestone proves the AutoRestart alternative flow of the unified use case:

`UC-01 Intelligent Alert Remediation with AutoOrch -> AutoRestart flow`

Screenshots are deferred to M12. This evidence package is complete enough to stand alone without screenshots.

