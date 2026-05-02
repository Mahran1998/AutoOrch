# M10 NotifyHuman Evidence Summary

## Goal

Prove the human-escalation outcome of UC-01 Intelligent Alert Remediation with AutoOrch.

This milestone verifies that AutoOrch does not repeatedly automate the same remediation candidate. When the same restart-like candidate appears twice within the configured memory window, AutoOrch converts the second decision to `notify_human`.

## Scope

- `ACTION_MODE=stub`
- No real restart
- No real scale
- No model retraining
- No architecture change
- Target workload: `default/controllable-backend`

## Result

M10 passed.

First restart-like alert:

- Alert: `AutoOrchNotifyHumanRestartFaultFirst`
- `candidate_action`: `auto_restart`
- `final_action`: `auto_restart`
- `decision`: `auto_restart`
- `reason`: `restart_confident`
- `p_restart`: `1.0`
- `action_result.status`: `simulated`

Second restart-like alert inside the 300 second memory window:

- Alert: `AutoOrchNotifyHumanRestartFaultSecond`
- `candidate_action`: `auto_restart`
- `final_action`: `notify_human`
- `decision`: `notify_human`
- `reason`: `repeated_action`
- `p_restart`: `1.0`
- `action_result.status`: `simulated`
- `escalation.consecutive_count`: `2`
- `escalation.threshold`: `2`
- `escalation.memory_seconds`: `300`

## Measured Features

First alert feature vector:

- `rps`: `18.818948734587927`
- `p95`: `0.991398158803222`
- `http_5xx_rate`: `18.818948734587927`
- `cpu_sat`: `0.17954434350597967`

Second alert feature vector:

- `rps`: `18.8040616773223`
- `p95`: `0.9908151549942594`
- `http_5xx_rate`: `18.8040616773223`
- `cpu_sat`: `0.18685141215884504`

## Metrics Proof

AutoOrch exposed the notify-human metric and decision/action counters:

- `autoorch_decisions_total{decision="auto_restart"} 1.0`
- `autoorch_decisions_total{decision="notify_human"} 2.0`
- `autoorch_notify_human_total 2.0`
- `autoorch_actions_total{action="auto_restart",status="simulated"} 1.0`
- `autoorch_actions_total{action="notify_human",status="simulated"} 2.0`

The acceptance proof is the first `notify_human` decision from `AutoOrchNotifyHumanRestartFaultSecond`. Alertmanager briefly repeated the first alert while it was resolving after rule deletion, which created one additional `notify_human` audit with `consecutive_count=3`. This did not change infrastructure because `ACTION_MODE` remained `stub`.

## Safety Proof

Final cleanup confirmed:

- `ACTION_MODE=stub`
- `error_injection_enabled 0.0`
- `latency_injection_enabled 0.0`
- `controllable-backend` remained `1/1`
- `autoorch-webhook` remained `1/1`
- `loadgenerator` remained `1/1`
- no `PrometheusRule` resources remained in namespace `default`
- M10 `AlertmanagerConfig` was deleted
- backend pod identity did not change

Backend pod before and after:

```text
NAME                                   UID                                    CREATED                PHASE     NODE
controllable-backend-cf9f896c8-w2bbs   dedf5ab0-f8a7-45c9-b41d-ad83421ccd93   2026-05-01T20:43:38Z   Running   autoorch-worker
```

Replicas before and after:

```text
spec.replicas: 1
readyReplicas: 1
availableReplicas: 1
```

## Thesis Interpretation

M10 demonstrates the safety/escalation behavior of AutoOrch. The models still recognized the same restart-like condition, but the policy layer prevented repeated automated remediation and escalated the incident as `notify_human`.

