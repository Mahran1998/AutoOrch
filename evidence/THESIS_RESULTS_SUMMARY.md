# AutoOrch Thesis Results Summary

This document summarizes the final evidence for `UC-01 Intelligent Alert Remediation with AutoOrch`. It is intended as a Chapter 10 results source and a bridge between the implementation evidence folders and the thesis narrative.

## Controlled Prototype Scope

The scenarios below were executed in a controlled local Kubernetes evaluation environment using Prometheus, Alertmanager, the AutoOrch webhook, ML model artifacts, and Ansible runbooks. The results validate the AutoOrch prototype design under reproducible test conditions. They do not claim universal production generalization without additional workloads, longer observation periods, and broader incident diversity.

## Final Scenario Results

| Scenario | Mode | rps | p95 | http_5xx_rate (req/s) | cpu_sat | p_autoscale | p_restart | final_action | Real action | Observed Kubernetes result | Cleanup status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| M7B AutoRestart | Ansible real action | 19.3782 | 0.9831 | 19.3782 | 0.2534 | 1.2896e-25 | 1.0000 | auto_restart | Yes | Backend pod identity changed; deployment restart annotation updated | Passed; ACTION_MODE reset to stub; faults off; backend 1/1 |
| M8B AutoScale | Ansible real action | 175.3748 | 0.00095 | 0.0000 | 1.8289 | 0.9404 | N/A | auto_scale | Yes | Replicas changed 1 -> 2, then cleanup restored 1 | Passed; ACTION_MODE reset to stub; load idle; backend 1/1 |
| M9 NoAction | Stub/skipped | 9.3926 | 0.00095 | 0.0000 | 0.0838 | 0.0044 | 0.4733 | no_action | No | Replicas remained 1/1/1; pod UID unchanged | Passed; temp rule/config deleted; faults off |
| M10 NotifyHuman | Stub/simulated | 18.8041 | 0.9908 | 18.8041 | 0.1869 | 6.5366e-26 | 1.0000 | notify_human | No | No restart or scale; pod UID unchanged | Passed; temp rules/config deleted; faults off |

Notes:

- M7B values are from the clean AutoRestart audit log. The `http_5xx_rate`, `p95`, and `cpu_sat` satisfy the restart rule: `http_5xx_rate` >= 0.20 req/s, p95 > 0.50, CPU saturation < 0.70.
- M8B has `p_restart=N/A` because the autoscale model confidently selected `auto_scale`; the restart model probability was not needed for the final decision.
- M10 reports the second planned restart-like alert, which produced `notify_human` with `reason=repeated_action` and `escalation.consecutive_count=2`.
- M10 metrics showed `autoorch_notify_human_total 2.0` because Alertmanager briefly repeated the first alert while it was resolving. The accepted proof is the first `notify_human` decision from the second planned alert.

## Scenario Interpretations

### M6 Alertmanager Routing

M6 proves the core implementation wiring. A controlled `AutoOrchM6TestAlert` fired in Prometheus, Alertmanager routed it to AutoOrch, AutoOrch queried Prometheus, computed the four-feature vector, and selected `no_action`. This supports the implementation claim that AutoOrch is a working alert-to-decision pipeline, not just an offline classifier.

Evidence folder: [M6B_alertmanager_route](M6B_alertmanager_route/)

### M7B AutoRestart Real Remediation

M7B maps to `UC-01 Flow A: AutoRestart`. The backend was placed into a restart-like condition with high 5xx requests per second and high p95 latency while CPU saturation remained below the autoscale threshold. AutoOrch selected `auto_restart` with `p_restart=1.0`, then executed the Ansible restart runbook:

```text
ansible-playbook /app/playbooks/restart_deployment.yml -e namespace=default -e workload=controllable-backend
```

The backend pod identity changed and the deployment restart annotation was updated, proving a real Kubernetes restart occurred. Cleanup restored `ACTION_MODE=stub`, disabled fault injection, idled the load generator, deleted the temporary PrometheusRule, and confirmed all deployments were available.

Evidence folder: [M7B_autorestart_real_action](M7B_autorestart_real_action/)

### M8B AutoScale Real Remediation

M8B maps to `UC-01 Flow B: AutoScale`. The backend was placed under CPU-bound load without error or latency injection. Prometheus showed high CPU saturation and low 5xx requests per second, and AutoOrch selected `auto_scale` with `p_autoscale=0.9404`. AutoOrch then executed the Ansible scale runbook:

```text
ansible-playbook /app/playbooks/scale_deployment.yml -e namespace=default -e workload=controllable-backend -e desired_replicas=2
```

The backend deployment scaled from `1` replica to `2` replicas, then cleanup restored it to `1`. This proves AutoOrch can perform real scale remediation through a scoped runbook.

Evidence folder: [M8B_autoscale_real_action](M8B_autoscale_real_action/)

### M9 NoAction

M9 maps to `UC-01 Flow C: NoAction`. A benign/noisy alert reached AutoOrch through Alertmanager, but live Prometheus metrics showed low RPS, low p95, zero 5xx requests per second, and low CPU saturation. Both model probabilities stayed below the action threshold, so AutoOrch selected `no_action` with `reason=below_threshold`.

No runbook executed, replicas stayed `1/1/1`, and the backend pod UID remained unchanged. This supports the thesis claim that AutoOrch reduces alert noise by avoiding unnecessary remediation.

Evidence folder: [M9_noaction](M9_noaction/)

### M10 NotifyHuman

M10 maps to `UC-01 Flow D: NotifyHuman`. The first restart-like alert produced a normal `auto_restart` candidate in `ACTION_MODE=stub`. A second restart-like alert arrived within the configured `300` second memory window. AutoOrch detected the repeated candidate and changed the final decision to `notify_human` with `reason=repeated_action`.

This proves AutoOrch is a safety-oriented orchestration layer: it does not blindly repeat the same automation candidate. Instead, repeated automation candidates are escalated for human attention.

Evidence folder: [M10_notifyhuman](M10_notifyhuman/)

## Repository Traceability

| Milestone | Commit | Evidence package |
| --- | --- | --- |
| M6 | `53ca9264` | [M6B_alertmanager_route](M6B_alertmanager_route/) |
| M7B | `de05212e` | [M7B_autorestart_real_action](M7B_autorestart_real_action/) |
| M8B | `e799883d` | [M8B_autoscale_real_action](M8B_autoscale_real_action/) |
| M9 | `020b55c8` | [M9_noaction](M9_noaction/) |
| M10 | `4481cb72` | [M10_notifyhuman](M10_notifyhuman/) |

## Notes For Thesis Writing

- Present the final system as one main use case: `UC-01 Intelligent Alert Remediation with AutoOrch`.
- Present AutoRestart, AutoScale, NoAction, and NotifyHuman as alternative flows of that use case.
- M7B is the real restart proof: Ansible runbook execution changed backend pod identity.
- M8B is the real scale proof: Ansible runbook execution changed replicas from `1` to `2`.
- M9 is the alert-noise reduction proof: AutoOrch received a benign alert and deliberately skipped remediation.
- M10 is the safety/escalation proof: repeated restart candidates were converted to `notify_human`.
- Mention controlled prototype scope explicitly. The model results and runtime scenarios prove feasibility under controlled conditions, not broad production generalization.
- Screenshots are deferred to M12. Use the `screenshots/README.md` files in each evidence package to capture clean thesis figures later.
- Use formatted code snippets from each `code_snippets/` folder instead of screenshots of code. Screenshots are better reserved for Prometheus, Alertmanager, terminal proof, and Kubernetes state.
