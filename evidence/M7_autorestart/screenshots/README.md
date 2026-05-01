Screenshots for this evidence package can be captured manually from:

1. Prometheus UI: `/alerts`, filtered to `AutoOrchRestartFault` while the temporary rule is active.
2. Alertmanager UI: active alert view showing `AutoOrchRestartFault`.
3. Terminal: `kubectl logs -n default deploy/autoorch-webhook --tail=200`.
4. Terminal: Prometheus queries for 5xx rate, p95, and cpu saturation.
5. Terminal: `kubectl get deploy -n default controllable-backend autoorch-webhook`.

The temporary `AutoOrchRestartFault` PrometheusRule should be deleted after evidence capture to avoid repeated test alerts.

M7A passed in command-line evidence. Screenshots are still manual polish items for the thesis and can be captured by briefly reapplying `evidence/M7_autorestart/manifests/prometheusrule-autorestart.yaml` while `ACTION_MODE=stub`, then deleting it again.
