Screenshots for this evidence package can be captured manually from:

1. Prometheus UI: `/alerts`, filtered to `AutoOrchM6TestAlert` while the temporary rule is active.
2. Alertmanager UI: active alert view showing `AutoOrchM6TestAlert`.
3. Terminal: `kubectl logs -n default deploy/autoorch-webhook --tail=120`.
4. Terminal: `curl http://127.0.0.1:8080/metrics` showing AutoOrch counters.
5. Terminal: `kubectl get pods -n monitoring` showing Alertmanager running.

The temporary `AutoOrchM6TestAlert` rule was deleted after evidence capture to avoid repeated test alerts.
