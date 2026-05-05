# AutoOrch Claim Traceability

This file maps thesis claims to concrete implementation evidence. It should be used when rewriting Chapters 5, 8, 10, and 11.

| Thesis claim | Evidence source | Screenshot | Code/log/output | Supported? |
| --- | --- | --- | --- | --- |
| PrometheusRule alerts can be routed through Alertmanager to AutoOrch. | `evidence/M6B_alertmanager_route/` | `evidence/_screenshots/M6_alertmanager_route/Figure_M6_02_alertmanager_route.png` | `outputs/alertmanager_received_alert.txt`, `logs/autoorch_alert_received.log` | Yes |
| AutoOrch exposes a webhook endpoint that receives Alertmanager alerts. | `evidence/M6B_alertmanager_route/` | `Figure_M6_03_autoorch_received_alert.png` | `code_snippets/post_alert_route.py` | Yes |
| AutoOrch computes the four-feature vector `[rps, p95, http_5xx_rate, cpu_sat]`. | `evidence/M6B_alertmanager_route/`, `evidence/M7B_autorestart_real_action/`, `evidence/M8B_autoscale_real_action/` | M7B/M8B metric screenshots | Prometheus metric outputs and AutoOrch logs | Yes |
| `http_5xx_rate` is measured as 5xx requests per second. | `experiments/dataset_restart.csv`, `evidence/THESIS_RESULTS_SUMMARY.md` | M7B/M10 restart-like metric screenshots | PromQL query outputs and dataset columns | Yes |
| Runtime uses an autoscale binary classifier. | `webhook/models/autoscale_classifier_meta.json` | N/A | model metadata and AutoOrch `/health` model-ready output | Yes |
| Runtime uses a restart binary classifier. | `webhook/models/restart_classifier_meta.json` | N/A | model metadata and AutoOrch `/health` model-ready output | Yes |
| AutoRestart can execute real remediation through Ansible. | `evidence/M7B_autorestart_real_action/` | `Figure_M7B_04_autoorch_restart_decision.png`, `Figure_M7B_05_restart_result.png` | `logs/autoorch_autorestart_real_action.log`, `outputs/pod_identity_before.txt`, `outputs/pod_identity_after.txt` | Yes |
| AutoScale can execute real remediation through Ansible. | `evidence/M8B_autoscale_real_action/` | `Figure_M8B_04_autoorch_scale_decision.png`, `Figure_M8B_05_replicas_after_scale.png` | `logs/autoorch_autoscale_real_action.log`, `outputs/replicas_before_after.txt` | Yes |
| NoAction suppresses unnecessary remediation. | `evidence/M9_noaction/` | `Figure_M9_03_autoorch_noaction_log.png`, `Figure_M9_04_no_infra_change.png` | `logs/autoorch_noaction.log`, `outputs/pod_identity_before.txt`, `outputs/pod_identity_after.txt` | Yes |
| NotifyHuman escalates repeated automation candidates. | `evidence/M10_notifyhuman/` | `Figure_M10_06_notifyhuman_escalation.png`, `Figure_M10_07_notifyhuman_metric.png` | `logs/autoorch_notifyhuman.log`, `outputs/autoorch_metrics_after.txt` | Yes |
| Automated actions are scoped to the intended workload. | `evidence/M7B_autorestart_real_action/`, `evidence/M8B_autoscale_real_action/` | Kubernetes state screenshots | RBAC snippets and command outputs | Yes |
| Final results are controlled prototype results, not broad production generalization. | `evidence/THESIS_RESULTS_SUMMARY.md`, `evidence/analysis/correlation/summary.md` | N/A | controlled-scope notes and limitations | Yes |
| Correlation analysis supports feature interpretation. | `evidence/analysis/correlation/` | heatmap PNGs | Pearson/Spearman CSVs and summary | Yes, descriptive only |

