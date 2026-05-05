# AutoOrch Evidence Index

This folder contains the implementation evidence for the final AutoOrch evaluation scenarios. Each evidence package is designed to stand alone with commands, manifests, outputs, logs, and code snippets. Manual thesis screenshots have also been captured and committed separately under [`_screenshots/`](_screenshots/).

## Evidence Overview

| Milestone | Scenario | Result | Evidence folder | Thesis use |
| --- | --- | --- | --- | --- |
| M6 | Alertmanager routing | Passed | [M6B_alertmanager_route](M6B_alertmanager_route/) | Implementation wiring |
| M7B | AutoRestart real action | Passed | [M7B_autorestart_real_action](M7B_autorestart_real_action/) | UC-01 Flow A |
| M8B | AutoScale real action | Passed | [M8B_autoscale_real_action](M8B_autoscale_real_action/) | UC-01 Flow B |
| M9 | NoAction | Passed | [M9_noaction](M9_noaction/) | UC-01 Flow C |
| M10 | NotifyHuman | Passed | [M10_notifyhuman](M10_notifyhuman/) | UC-01 Flow D |

## Repository Traceability

| Milestone | Evidence commit | Notes |
| --- | --- | --- |
| M6 | `53ca9264` | Add M6 Alertmanager routing evidence package |
| M7B | `de05212e` | Add M7B AutoRestart real action evidence package |
| M8B | `e799883d` | Add M8B AutoScale real action evidence package |
| M9 | `020b55c8` | Add M9 NoAction evidence package |
| M10 | `4481cb72` | Add M10 NotifyHuman evidence package |

## Controlled Prototype Scope

These results come from controlled Kubernetes and Prometheus prototype scenarios in a local evaluation environment. They validate the AutoOrch design and implementation under reproducible workload, fault, and alert conditions. They should not be overclaimed as broad production generalization across arbitrary applications, incidents, or infrastructure.

## Key Files By Evidence Package

### M6 Alertmanager Routing

- [summary.md](M6B_alertmanager_route/summary.md)
- [commands.md](M6B_alertmanager_route/commands.md)
- [manifests/](M6B_alertmanager_route/manifests/)
- [outputs/](M6B_alertmanager_route/outputs/)
- [logs/](M6B_alertmanager_route/logs/)
- [code_snippets/](M6B_alertmanager_route/code_snippets/)
- [screenshots/README.md](M6B_alertmanager_route/screenshots/README.md)

M6 proves the monitoring-to-webhook wiring:

```text
PrometheusRule -> Alertmanager -> AutoOrch POST /alert -> feature extraction -> no_action
```

### M7B AutoRestart Real Action

- [summary.md](M7B_autorestart_real_action/summary.md)
- [commands.md](M7B_autorestart_real_action/commands.md)
- [PLAN.md](M7B_autorestart_real_action/PLAN.md)
- [manifests/](M7B_autorestart_real_action/manifests/)
- [outputs/](M7B_autorestart_real_action/outputs/)
- [logs/](M7B_autorestart_real_action/logs/)
- [code_snippets/](M7B_autorestart_real_action/code_snippets/)
- [screenshots/README.md](M7B_autorestart_real_action/screenshots/README.md)

M7B proves real AutoRestart remediation through an Ansible runbook. The backend pod identity changed and the deployment restart annotation was updated.

### M8B AutoScale Real Action

- [summary.md](M8B_autoscale_real_action/summary.md)
- [commands.md](M8B_autoscale_real_action/commands.md)
- [PREP.md](M8B_autoscale_real_action/PREP.md)
- [PLAN.md](M8B_autoscale_real_action/PLAN.md)
- [manifests/](M8B_autoscale_real_action/manifests/)
- [outputs/](M8B_autoscale_real_action/outputs/)
- [logs/](M8B_autoscale_real_action/logs/)
- [code_snippets/](M8B_autoscale_real_action/code_snippets/)
- [screenshots/README.md](M8B_autoscale_real_action/screenshots/README.md)

M8B proves real AutoScale remediation through an Ansible runbook. The backend deployment scaled from `1` replica to `2` replicas, then cleanup restored it to `1`.

### M9 NoAction

- [summary.md](M9_noaction/summary.md)
- [commands.md](M9_noaction/commands.md)
- [PLAN.md](M9_noaction/PLAN.md)
- [manifests/](M9_noaction/manifests/)
- [outputs/](M9_noaction/outputs/)
- [logs/](M9_noaction/logs/)
- [code_snippets/](M9_noaction/code_snippets/)
- [screenshots/README.md](M9_noaction/screenshots/README.md)

M9 proves benign/noisy alert suppression. AutoOrch received an alert, checked live Prometheus metrics, selected `no_action`, and made no Kubernetes state change.

### M10 NotifyHuman

- [summary.md](M10_notifyhuman/summary.md)
- [commands.md](M10_notifyhuman/commands.md)
- [PLAN.md](M10_notifyhuman/PLAN.md)
- [manifests/](M10_notifyhuman/manifests/)
- [outputs/](M10_notifyhuman/outputs/)
- [logs/](M10_notifyhuman/logs/)
- [code_snippets/](M10_notifyhuman/code_snippets/)
- [screenshots/README.md](M10_notifyhuman/screenshots/README.md)

M10 proves repeated-candidate escalation. The first restart-like candidate produced `auto_restart`; the second restart-like candidate within the memory window produced `notify_human`.

## Thesis Mapping

The final thesis use case should be presented as:

```text
UC-01 Intelligent Alert Remediation with AutoOrch
```

with four alternative flows:

| Flow | Evidence | Meaning |
| --- | --- | --- |
| Flow A | M7B AutoRestart | High 5xx/high latency with low CPU is remediated by restart |
| Flow B | M8B AutoScale | CPU-bound load is remediated by scaling replicas |
| Flow C | M9 NoAction | Benign/noisy alert is intentionally ignored |
| Flow D | M10 NotifyHuman | Repeated automation candidate is escalated to a human |

## Screenshot Status

Screenshot evidence has been captured and committed separately under [`_screenshots/`](_screenshots/). The machine-verifiable evidence remains the source of truth through logs, command output, manifests, and code snippets. For the thesis, use formatted code snippets rather than screenshots of code unless a visual appendix is needed.
