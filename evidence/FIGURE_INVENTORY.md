# AutoOrch Figure Inventory

This inventory maps committed screenshots to thesis use. Not every screenshot should appear in the final thesis. Use primary figures in the main text and backup figures only if space allows or in an appendix.

| Figure file | Milestone | Scenario | What it proves | Suggested thesis caption | Suggested thesis section | Use |
| --- | --- | --- | --- | --- | --- | --- |
| `evidence/_screenshots/M6_alertmanager_route/Figure_M6_01_prometheus_alert_firing.png` | M6 | Alertmanager routing | Prometheus alert rule fires | Prometheus firing a controlled AutoOrch routing alert | Implementation / alert routing | Primary |
| `evidence/_screenshots/M6_alertmanager_route/Figure_M6_02_alertmanager_route.png` | M6 | Alertmanager routing | Alertmanager routes alert to AutoOrch receiver | Alertmanager receiver selected for the AutoOrch webhook | Implementation / alert routing | Primary |
| `evidence/_screenshots/M6_alertmanager_route/Figure_M6_03_autoorch_received_alert.png` | M6 | Alertmanager routing | AutoOrch receives POST `/alert` | AutoOrch receiving the Alertmanager webhook request | Implementation / alert routing | Primary |
| `evidence/_screenshots/M6_alertmanager_route/Figure_M6_04_autoorch_metrics.png` | M6 | Alertmanager routing | AutoOrch exposes decision/action metrics | AutoOrch self-observability metrics after alert processing | Implementation / observability | Backup |
| `evidence/_screenshots/M6_alertmanager_route/M6_alertmanager_route.PNG` | M6 | Alertmanager routing | Combined/legacy routing screenshot | Backup screenshot for M6 routing evidence | Appendix or discard if duplicate | Backup |
| `evidence/_screenshots/M7B_autorestart_real_action/Figure_M7B_01_before_restart_state.png` | M7B | AutoRestart | Backend state before restart action | Backend deployment state before AutoRestart remediation | Evaluation / AutoRestart | Backup |
| `evidence/_screenshots/M7B_autorestart_real_action/Figure_M7B_02_restart_like_metrics.png` | M7B | AutoRestart | High 5xx req/s, high p95, low CPU | Restart-like Prometheus metrics before remediation | Evaluation / AutoRestart | Primary |
| `evidence/_screenshots/M7B_autorestart_real_action/Figure_M7B_03_alertmanager_autorestart_fault.png` | M7B | AutoRestart | AutoRestart alert reaches Alertmanager | Alertmanager receiving the AutoRestart fault alert | Evaluation / AutoRestart | Backup |
| `evidence/_screenshots/M7B_autorestart_real_action/Figure_M7B_04_autoorch_restart_decision.png` | M7B | AutoRestart | AutoOrch selects `auto_restart` and runs Ansible | AutoOrch restart decision and Ansible runbook execution | Evaluation / AutoRestart | Primary |
| `evidence/_screenshots/M7B_autorestart_real_action/Figure_M7B_05_restart_result.png` | M7B | AutoRestart | Pod identity changed after restart | Kubernetes evidence of successful backend restart | Evaluation / AutoRestart | Primary |
| `evidence/_screenshots/M8B_autoscale_real_action/Figure_M8B_01_before_scale_state.png` | M8B | AutoScale | Deployment starts at one replica | Backend deployment before AutoScale remediation | Evaluation / AutoScale | Backup |
| `evidence/_screenshots/M8B_autoscale_real_action/Figure_M8B_02_autoscale_metrics.png` | M8B | AutoScale | High CPU/load with low 5xx | Autoscale-like Prometheus metrics under load | Evaluation / AutoScale | Primary |
| `evidence/_screenshots/M8B_autoscale_real_action/Figure_M8B_03_alertmanager_autoscale_alert.png` | M8B | AutoScale | AutoScale alert reaches Alertmanager | Alertmanager receiving the AutoScale pressure alert | Evaluation / AutoScale | Backup |
| `evidence/_screenshots/M8B_autoscale_real_action/Figure_M8B_04_autoorch_scale_decision.png` | M8B | AutoScale | AutoOrch selects `auto_scale` and runs Ansible | AutoOrch scale decision and Ansible runbook execution | Evaluation / AutoScale | Primary |
| `evidence/_screenshots/M8B_autoscale_real_action/Figure_M8B_05_replicas_after_scale.png` | M8B | AutoScale | Replicas changed from 1 to 2 | Kubernetes deployment after AutoScale remediation | Evaluation / AutoScale | Primary |
| `evidence/_screenshots/M8B_autoscale_real_action/Figure_M8B_06_cleanup_final_state.png` | M8B | AutoScale | Cleanup restored one replica | Cleanup state after AutoScale evidence capture | Appendix / safety evidence | Backup |
| `evidence/_screenshots/M9_noaction/Figure_M9_01b_cpu_saturation.png` | M9 | NoAction | Healthy/low CPU metric state | Healthy metrics used for the NoAction scenario | Evaluation / NoAction | Primary |
| `evidence/_screenshots/M9_noaction/Figure_M9_02_benign_alert.png` | M9 | NoAction | Benign alert reaches Alertmanager | Controlled benign alert routed to AutoOrch | Evaluation / NoAction | Backup |
| `evidence/_screenshots/M9_noaction/Figure_M9_03_autoorch_noaction_log.png` | M9 | NoAction | AutoOrch selects `no_action` | AutoOrch no-action decision under healthy metrics | Evaluation / NoAction | Primary |
| `evidence/_screenshots/M9_noaction/Figure_M9_03a_autoorch_noaction_log.png` | M9 | NoAction | Alternate no_action log capture | Backup no-action log evidence | Appendix or discard if duplicate | Backup |
| `evidence/_screenshots/M9_noaction/Figure_M9_04_no_infra_change.png` | M9 | NoAction | Pod and replicas unchanged | Kubernetes state unchanged after NoAction decision | Evaluation / NoAction | Primary |
| `evidence/_screenshots/M10_notifyhuman/Figure_M10_01_kubernetes_state_before.png` | M10 | NotifyHuman | Baseline state before escalation proof | Backend state before NotifyHuman test | Evaluation / NotifyHuman | Backup |
| `evidence/_screenshots/M10_notifyhuman/Figure_M10_02_restart_like_metrics.png` | M10 | NotifyHuman | Restart-like metrics used for repeated candidate | Restart-like metrics used to trigger repeated automation candidates | Evaluation / NotifyHuman | Backup |
| `evidence/_screenshots/M10_notifyhuman/Figure_M10_03_alertmanager_first_alert.png` | M10 | NotifyHuman | First restart-like alert in Alertmanager | First restart-like alert in the NotifyHuman scenario | Evaluation / NotifyHuman | Backup |
| `evidence/_screenshots/M10_notifyhuman/Figure_M10_04_first_autorestart_candidate.png` | M10 | NotifyHuman | First candidate is `auto_restart` | First restart-like alert produces an AutoRestart candidate | Evaluation / NotifyHuman | Primary |
| `evidence/_screenshots/M10_notifyhuman/Figure_M10_05_alertmanager_second_alert.png` | M10 | NotifyHuman | Second alert arrives within memory window | Second restart-like alert used for repeated-candidate escalation | Evaluation / NotifyHuman | Backup |
| `evidence/_screenshots/M10_notifyhuman/Figure_M10_06_notifyhuman_escalation.png` | M10 | NotifyHuman | Second candidate escalates to `notify_human` | Repeated AutoRestart candidate escalated to NotifyHuman | Evaluation / NotifyHuman | Primary |
| `evidence/_screenshots/M10_notifyhuman/Figure_M10_07_notifyhuman_metric.png` | M10 | NotifyHuman | NotifyHuman metric/counter visible | AutoOrch NotifyHuman metric after repeated-candidate escalation | Evaluation / observability | Primary |
| `evidence/_screenshots/M10_notifyhuman/Figure_M10_08_no_infra_change.png` | M10 | NotifyHuman | No restart/scale occurred | Kubernetes state unchanged after NotifyHuman escalation | Evaluation / NotifyHuman | Primary |

## Recommended Main-Text Figure Set

Use approximately 10 figures in the main thesis:

1. M6 Prometheus alert firing.
2. M6 Alertmanager receiver route.
3. M7B restart-like metrics.
4. M7B AutoOrch restart decision.
5. M7B restart result.
6. M8B autoscale metrics.
7. M8B AutoOrch scale decision.
8. M8B replicas after scale.
9. M9 no_action decision.
10. M10 notify_human escalation.

The remaining screenshots can be kept as backup or appendix evidence.

