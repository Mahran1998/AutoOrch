# M7B Manual Screenshot Checklist

Actual screenshots are deferred to M12. The M7B evidence package must prove the scenario without screenshots through `summary.md`, `commands.md`, `outputs/`, `logs/`, `manifests/`, and `code_snippets/`.

When M12 starts, briefly recreate the stable M7B state and capture the screenshots below.

## S-M7B-01 Environment Before Restart

- Open: terminal.
- Command:
  ```bash
  kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
  ```
- Capture when: all deployments are `1/1`.
- Suggested filename: `Figure_M7B_01_before_deployments.png`
- Thesis purpose: show the controlled Kubernetes environment before the real restart action.

## S-M7B-02 Fault Metrics In Prometheus

- Open: Prometheus UI.
- Query 1:
  ```promql
  sum(rate(http_requests_total{exported_endpoint="/api/test",status=~"5.."}[1m]))
  ```
- Query 2:
  ```promql
  histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[1m])) by (le))
  ```
- Query 3:
  ```promql
  sum(rate(container_cpu_usage_seconds_total{namespace="default",pod=~"controllable-backend-.*",container!="POD"}[1m])) / 0.5
  ```
- Capture when: 5xx rate is `>= 0.20`, p95 is `> 0.50`, and CPU saturation is `< 0.70`.
- Suggested filename: `Figure_M7B_02_restart_fault_metrics.png`
- Thesis purpose: prove the incident is restart-like, not autoscale-like.

## S-M7B-03 Alertmanager Alert

- Open: Alertmanager UI.
- Show: active alert `AutoOrchRestartFault`.
- Capture when: receiver/route points to AutoOrch, if visible.
- Suggested filename: `Figure_M7B_03_alertmanager_autorestart_fault.png`
- Thesis purpose: show the alert routing stage of the pipeline.

## S-M7B-04 AutoOrch Real Decision Log

- Open: terminal.
- Command:
  ```bash
  kubectl logs -n default deploy/autoorch-webhook --tail=400
  ```
- Capture when the log shows:
  ```text
  p_restart >= 0.90
  candidate_action=auto_restart
  final_action=auto_restart
  reason=restart_confident
  action_result.status=success
  ```
- Suggested filename: `Figure_M7B_04_autoorch_restart_decision.png`
- Thesis purpose: prove ML decision and policy output.

## S-M7B-05 Ansible Action Evidence

- Open: terminal or saved log file.
- Show: `action_result.details.command` includes:
  ```text
  ansible-playbook /app/playbooks/restart_deployment.yml -e namespace=default -e workload=controllable-backend
  ```
- Capture when: command and successful result are visible together.
- Suggested filename: `Figure_M7B_05_ansible_restart_action.png`
- Thesis purpose: prove remediation was performed through the runbook executor.

## S-M7B-06 Restart Result

- Open: terminal.
- Commands:
  ```bash
  kubectl rollout status deployment/controllable-backend -n default
  kubectl get pods -n default -o wide | grep controllable-backend
  ```
- Capture when: rollout is successful and the controllable-backend pod state is clean.
- Suggested filename: `Figure_M7B_06_restart_result.png`
- Thesis purpose: show the Kubernetes effect of AutoRestart.

## S-M7B-07 Cleanup Safety

- Open: terminal.
- Commands:
  ```bash
  curl -s http://127.0.0.1:5000/metrics | grep -E "error_injection_enabled|latency_injection_enabled"
  kubectl get deploy -n default autoorch-webhook controllable-backend loadgenerator
  ```
- Capture when: fault toggles are `0.0`, deployments are healthy, and AutoOrch is back in `stub` mode.
- Suggested filename: `Figure_M7B_07_cleanup_safety.png`
- Thesis purpose: show the experiment ended safely.

## Code Snippets For Thesis

Prefer formatted thesis code snippets instead of screenshots for:

- AutoOrch `/alert` route.
- Prometheus feature query functions.
- Two-binary decision cascade.
- Ansible action executor.
- `restart_deployment.yml`.
- `autoorch-runner` RBAC.
- `AlertmanagerConfig` receiver.
- `PrometheusRule AutoOrchRestartFault`.

