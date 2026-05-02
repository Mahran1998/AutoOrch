# M8-Calibrate Screenshot Checklist

Actual screenshots will be captured later in M12. This checklist records what to recreate manually.

## S-M8C-1: Backend Fault Toggles Off

Open a terminal and run:

```bash
curl -s http://127.0.0.1:5000/metrics | grep -E "error_injection_enabled|latency_injection_enabled"
```

Capture when both values show `0.0`.

Suggested filename:

```text
S_M8C_1_fault_toggles_off.png
```

Purpose: prove the autoscale calibration did not use error or latency injection.

## S-M8C-2: Prometheus CPU Saturation Query

Open Prometheus and run:

```promql
sum(rate(container_cpu_usage_seconds_total{namespace="default",pod=~"controllable-backend-.*",container!="POD"}[1m])) / 0.5
```

Capture during the calibrated load point when the value is above `0.70`.

Suggested filename:

```text
S_M8C_2_cpu_saturation.png
```

Purpose: show the backend can produce autoscale-like CPU pressure.

## S-M8C-3: Prometheus 5xx Query

Open Prometheus and run:

```promql
sum(rate(http_requests_total{exported_endpoint="/api/test",status=~"5.."}[1m]))
```

Capture when the value is empty or zero.

Suggested filename:

```text
S_M8C_3_5xx_zero.png
```

Purpose: show this is not a restart-like fault.

## S-M8C-4: Loadgenerator Configuration

Open a terminal and run:

```bash
kubectl get deploy -n default loadgenerator -o jsonpath='{.spec.template.spec.containers[0].env}{"\n"}'
```

Capture the calibrated load configuration during the rerun.

Suggested filename:

```text
S_M8C_4_loadgenerator_config.png
```

Purpose: show the load settings used to create the autoscale-like feature pattern.

