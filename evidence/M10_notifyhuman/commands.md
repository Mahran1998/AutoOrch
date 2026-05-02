# M10 NotifyHuman Commands

## Preflight

```bash
git status --short
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
kubectl get deployment autoorch-webhook -n default -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="ACTION_MODE")].value}{"\n"}'
kubectl get deployment autoorch-webhook -n default -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="CONSECUTIVE_ESCALATION_COUNT")].value}{"\n"}'
kubectl get deployment autoorch-webhook -n default -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="CONSECUTIVE_MEMORY_SECONDS")].value}{"\n"}'
kubectl get pods -n default -l app=controllable-backend -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,CREATED:.metadata.creationTimestamp,PHASE:.status.phase,NODE:.spec.nodeName
kubectl get prometheusrule -n default
```

## Reset AutoOrch Memory

```bash
kubectl rollout restart deployment/autoorch-webhook -n default
kubectl rollout status deployment/autoorch-webhook -n default --timeout=90s
kubectl logs -n default deploy/autoorch-webhook --tail=120
```

## Port-Forward Services

```bash
kubectl port-forward -n default svc/controllable-backend 5000:5000
kubectl port-forward -n default svc/autoorch-webhook 18080:8080
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-prometheus 9090:9090
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-alertmanager 9093:9093
```

## Health And Baseline Metrics

```bash
curl -s http://127.0.0.1:18080/health
curl -s http://127.0.0.1:5000/health
curl -s http://127.0.0.1:5000/metrics
curl -s http://127.0.0.1:18080/metrics
```

## Activate Restart-Like Load

```bash
kubectl set env deployment/loadgenerator TARGET=http://controllable-backend:5000/api/test RPS=20 CONCURRENCY=15 --overwrite -n default
kubectl rollout status deployment/loadgenerator -n default --timeout=60s
curl -s -X POST http://127.0.0.1:5000/inject-latency?ms=700
curl -s -X POST http://127.0.0.1:5000/inject-errors
sleep 45
```

## Feature Queries

```bash
curl -sG http://127.0.0.1:9090/api/v1/query --data-urlencode 'query=sum(rate(http_requests_total{exported_endpoint="/api/test"}[1m]))'
curl -sG http://127.0.0.1:9090/api/v1/query --data-urlencode 'query=histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[1m])) by (le))'
curl -sG http://127.0.0.1:9090/api/v1/query --data-urlencode 'query=sum(rate(http_requests_total{exported_endpoint="/api/test",status=~"5.."}[1m]))'
curl -sG http://127.0.0.1:9090/api/v1/query --data-urlencode 'query=sum(rate(container_cpu_usage_seconds_total{namespace="default",pod=~"controllable-backend-.*",container!="POD"}[1m])) / 0.5'
```

## First Alert

```bash
kubectl apply -f evidence/M10_notifyhuman/manifests/alertmanagerconfig-notifyhuman.yaml
kubectl apply -f evidence/M10_notifyhuman/manifests/prometheusrule-notifyhuman-first.yaml
sleep 45
curl -sG http://127.0.0.1:9090/api/v1/query --data-urlencode 'query=ALERTS{alertname="AutoOrchNotifyHumanRestartFaultFirst"}'
kubectl logs -n default deploy/autoorch-webhook --tail=120
curl -s http://127.0.0.1:18080/metrics
```

## Second Alert

```bash
kubectl delete prometheusrule -n default autoorch-notifyhuman-restart-first --ignore-not-found
kubectl apply -f evidence/M10_notifyhuman/manifests/prometheusrule-notifyhuman-second.yaml
sleep 90
curl -sG http://127.0.0.1:9090/api/v1/query --data-urlencode 'query=ALERTS{alertname="AutoOrchNotifyHumanRestartFaultSecond"}'
kubectl logs -n default deploy/autoorch-webhook --tail=180
curl -s http://127.0.0.1:18080/metrics
```

## Cleanup

```bash
kubectl delete prometheusrule -n default autoorch-notifyhuman-restart-second --ignore-not-found
kubectl delete alertmanagerconfig -n default autoorch-m10-notifyhuman-route --ignore-not-found
curl -s -X POST http://127.0.0.1:5000/inject-latency?ms=0
curl -s http://127.0.0.1:5000/metrics
curl -s -X POST http://127.0.0.1:5000/inject-errors
kubectl set env deployment/loadgenerator TARGET=http://controllable-backend:5000/api/test RPS=0 CONCURRENCY=1 --overwrite -n default
kubectl rollout status deployment/loadgenerator -n default --timeout=60s
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
kubectl get prometheusrule -n default
kubectl get alertmanagerconfig -n default
curl -s http://127.0.0.1:5000/metrics
```
