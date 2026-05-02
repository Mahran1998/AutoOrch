# M8-Calibrate Commands

## Preflight

```bash
git status --short
kubectl get deploy -n default controllable-backend loadgenerator autoorch-webhook
kubectl get svc -n default
kubectl get svc -n monitoring
kubectl get deploy -n default autoorch-webhook \
  -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="ACTION_MODE")].value}{"\n"}'
```

## Port-Forwards

```bash
kubectl port-forward -n default svc/controllable-backend 5000:5000
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-prometheus 9090:9090
```

## Fault Toggle Check

```bash
curl -s http://127.0.0.1:5000/metrics | grep -E "error_injection_enabled|latency_injection_enabled"
```

Expected:

```text
error_injection_enabled 0.0
latency_injection_enabled 0.0
```

## CPU Limit Query

```bash
curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=sum(kube_pod_container_resource_limits{namespace="default",pod=~"controllable-backend-.*",resource="cpu"})'
```

Observed CPU limit: `0.5`.

## Trial 1

```bash
kubectl set env deployment/loadgenerator \
  TARGET=http://controllable-backend:5000/api/test \
  RPS=100 \
  CONCURRENCY=25 \
  --overwrite -n default

kubectl rollout status deployment/loadgenerator -n default --timeout=90s
sleep 120
```

## Trial 2

```bash
kubectl set env deployment/loadgenerator \
  TARGET=http://controllable-backend:5000/api/test \
  RPS=300 \
  CONCURRENCY=50 \
  --overwrite -n default

kubectl rollout status deployment/loadgenerator -n default --timeout=90s
sleep 120
```

## Trial 3

```bash
kubectl set env deployment/loadgenerator \
  TARGET=http://controllable-backend:5000/api/test \
  RPS=500 \
  CONCURRENCY=75 \
  --overwrite -n default

kubectl rollout status deployment/loadgenerator -n default --timeout=90s
sleep 120
```

## Prometheus Queries Sampled Per Trial

```promql
sum(rate(http_requests_total{exported_endpoint="/api/test"}[1m]))
```

```promql
histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[1m])) by (le))
```

```promql
sum(rate(http_requests_total{exported_endpoint="/api/test",status=~"5.."}[1m]))
```

```promql
sum(rate(container_cpu_usage_seconds_total{namespace="default",pod=~"controllable-backend-.*",container!="POD"}[1m])) / 0.5
```

```promql
sum(kube_pod_container_resource_limits{namespace="default",pod=~"controllable-backend-.*",resource="cpu"})
```

## Optional Kubernetes CPU Cross-Check

```bash
kubectl top pod -n default
```

Observed:

```text
error: Metrics API not available
```

Prometheus was used as the source of truth.

## Cleanup

```bash
kubectl set env deployment/loadgenerator \
  TARGET=http://controllable-backend:5000/api/test \
  RPS=0 \
  CONCURRENCY=1 \
  --overwrite -n default

kubectl rollout status deployment/loadgenerator -n default --timeout=90s

curl -s http://127.0.0.1:5000/metrics | grep -E "error_injection_enabled|latency_injection_enabled"

kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator

kubectl get deploy -n default loadgenerator \
  -o jsonpath='{.spec.template.spec.containers[0].env}{"\n"}'

kubectl get prometheusrule -n default

pgrep -af 'kubectl port-forward' || true
```

