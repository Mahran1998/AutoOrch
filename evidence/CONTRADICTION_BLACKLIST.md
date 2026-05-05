# AutoOrch Thesis Contradiction Blacklist

This checklist lists wording that must not appear as a **current implementation claim** in the final thesis. Some terms may appear only inside a clearly framed subsection such as "Design evolution and final implementation choices."

| Forbidden or risky wording | Use this replacement |
| --- | --- |
| single 4-class classifier | cascaded two-binary-model decision flow plus policy layer |
| unified 4-class classifier | autoscale binary classifier followed by restart binary classifier |
| one multi-class model for all actions | two specialized binary classifiers with a safety policy layer |
| trained 4-class classifier | `autoscale_classifier.joblib` and `restart_classifier.joblib` |
| `autoorch_4class_classifier.joblib` | `webhook/models/autoscale_classifier.joblib` and `webhook/models/restart_classifier.joblib` |
| `notify_human` as an ML class | `notify_human` as policy-based escalation |
| `notify_human` predicted by the classifier | `notify_human` selected by policy when repeated automation candidates or unsafe conditions occur |
| 14-feature runtime | four-feature runtime vector |
| broad runtime feature set | `[rps, p95, http_5xx_rate, cpu_sat]` |
| `http_5xx_rate` as a percentage | `http_5xx_rate` as 5xx requests per second |
| `http_5xx_rate` as a ratio or fraction | `http_5xx_rate` as 5xx requests per second |
| `rate/ratio of 5xx responses` | rate of 5xx responses in requests per second |
| demo-backend as the final evaluation target | controllable-backend as the final evaluation target |
| simulated-only remediation | real Ansible restart and real Ansible scale were proven; no_action and notify_human are safe non-remediation outcomes |
| all decision logic resides in the trained model | decision uses model cascade plus safety policy |
| no runtime rule branches | policy rules exist for scope checks, confidence thresholds, repeated-candidate escalation, and safe fallback |
| model decides `notify_human` directly | policy layer escalates to `notify_human` |
| production-proven generalization | controlled local prototype validation |

## Required Locked Terminology

- `Prometheus`
- `Alertmanager`
- `AutoOrch`
- `Ansible runbook`
- `controllable-backend`
- `auto_scale`
- `auto_restart`
- `no_action`
- `notify_human`
- `http_5xx_rate (req/s)`
- `cpu_sat`

## Final Architecture Sentence

Use this wording when a concise final-architecture statement is needed:

> AutoOrch uses a cascaded two-model decision flow. The autoscale classifier first evaluates whether the alert context matches a CPU/load-driven scaling pattern. If autoscaling is not selected, the restart classifier evaluates whether the condition resembles an application-failure pattern suitable for restart. If neither model exceeds the confidence threshold, AutoOrch selects `no_action`. If repeated automation candidates occur within the configured memory window, the policy layer escalates to `notify_human`.

