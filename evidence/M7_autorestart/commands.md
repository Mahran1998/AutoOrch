# M7A Commands

## Baseline Safety Checks

```bash
curl -s http://127.0.0.1:8080/health
kubectl get deploy -n default autoorch-webhook controllable-backend loadgenerator
kubectl get pods -n default -o wide
kubectl get prometheusrule -n default autoorch-autorestart-fault
```

## Traffic Setup

```bash
kubectl set env deployment/loadgenerator \
  TARGET="http://controllable-backend:5000/api/test" \
  RPS="30" \
  CONCURRENCY="15" \
  --overwrite -n default

kubectl rollout status deployment/loadgenerator -n default --timeout=60s
kubectl port-forward -n default svc/loadgenerator-metrics 8081:8080

curl -s -X POST http://127.0.0.1:8081/control \
  -H 'Content-Type: application/json' \
  -d '{"rps":30,"concurrency":15}'
```

## Apply M7A Routing And Alert Rule

```bash
kubectl apply -f evidence/M7_autorestart/manifests/alertmanagerconfig-autorestart.yaml
kubectl apply -f evidence/M7_autorestart/manifests/prometheusrule-autorestart.yaml
```

## First Attempt Fault Injection

```bash
curl -s -X POST "http://127.0.0.1:5000/inject-latency?ms=700"
curl -s -X POST http://127.0.0.1:5000/inject-errors
sleep 120
kubectl logs -n default deploy/autoorch-webhook --tail=300
```

The first attempt generated restart-like metrics, but `p_restart=0.7866666666666666`, below the runtime threshold.

## Cleanup After First Attempt

```bash
curl -s -X POST http://127.0.0.1:5000/inject-errors
curl -s -X POST "http://127.0.0.1:5000/inject-latency?ms=0"
curl -s -X POST http://127.0.0.1:8081/control \
  -H 'Content-Type: application/json' \
  -d '{"rps":0,"concurrency":1}'
kubectl delete prometheusrule -n default autoorch-autorestart-fault
```

## Second Attempt With One-Parameter Adjustment

```bash
kubectl set env deployment/loadgenerator \
  TARGET="http://controllable-backend:5000/api/test" \
  RPS="20" \
  CONCURRENCY="15" \
  --overwrite -n default

kubectl rollout status deployment/loadgenerator -n default --timeout=60s

curl -s -X POST http://127.0.0.1:8081/control \
  -H 'Content-Type: application/json' \
  -d '{"rps":20,"concurrency":15}'

kubectl apply -f evidence/M7_autorestart/manifests/prometheusrule-autorestart.yaml
curl -s -X POST "http://127.0.0.1:5000/inject-latency?ms=700"
curl -s -X POST http://127.0.0.1:5000/inject-errors
sleep 120
```

## Prometheus Queries Used During The Passing Attempt

```bash
curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=sum(rate(http_requests_total{exported_endpoint="/api/test",status=~"5.."}[1m]))'

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[1m])) by (le))'

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=sum(rate(container_cpu_usage_seconds_total{namespace="default",pod=~"controllable-backend-.*",container!="POD"}[1m])) / 0.5'
```

## Final Cleanup

```bash
curl -s -X POST http://127.0.0.1:5000/inject-errors
curl -s -X POST "http://127.0.0.1:5000/inject-latency?ms=0"
kubectl set env deployment/loadgenerator RPS="0" CONCURRENCY="1" --overwrite -n default
kubectl rollout status deployment/loadgenerator -n default --timeout=60s
kubectl delete prometheusrule -n default autoorch-autorestart-fault
curl -s http://127.0.0.1:5000/metrics | grep -E "error_injection_enabled|latency_injection_enabled"
kubectl get deploy -n default autoorch-webhook controllable-backend loadgenerator
kubectl get prometheusrule -n default autoorch-autorestart-fault
```

## Metrics Evidence

```bash
kubectl port-forward -n default svc/autoorch-webhook 18080:8080
curl -s http://127.0.0.1:18080/health
curl -s http://127.0.0.1:18080/metrics | head -120
```
