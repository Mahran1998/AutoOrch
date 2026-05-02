# M8B Commands

## Baseline

```bash
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator

kubectl get deployment controllable-backend -n default \
  -o jsonpath='{.spec.replicas}{"\n"}{.status.readyReplicas}{"\n"}{.status.availableReplicas}{"\n"}'

kubectl get pods -n default -l app=controllable-backend \
  -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,CREATED:.metadata.creationTimestamp,PHASE:.status.phase,NODE:.spec.nodeName

curl -s http://127.0.0.1:5000/health
curl -s http://127.0.0.1:5000/metrics
curl -s http://127.0.0.1:18080/health
```

## Switch AutoOrch To Real Ansible Mode

```bash
kubectl set env deployment/autoorch-webhook ACTION_MODE=ansible --overwrite -n default
kubectl rollout status deployment/autoorch-webhook -n default --timeout=90s
curl -s http://127.0.0.1:18080/health
```

## Apply Temporary M8B Routing

```bash
kubectl apply -f evidence/M8B_autoscale_real_action/manifests/alertmanagerconfig-autoscale.yaml
kubectl apply -f evidence/M8B_autoscale_real_action/manifests/prometheusrule-autoscale.yaml
```

## Start Calibrated Load

```bash
kubectl set env deployment/loadgenerator \
  TARGET=http://controllable-backend:5000/api/test \
  RPS=500 \
  CONCURRENCY=75 \
  --overwrite -n default

kubectl rollout status deployment/loadgenerator -n default --timeout=90s
```

## Prometheus Evidence Queries

```bash
curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=sum(rate(http_requests_total{exported_endpoint="/api/test"}[1m]))'

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[1m])) by (le))'

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=(sum(rate(http_requests_total{exported_endpoint="/api/test",status=~"5.."}[1m])) or vector(0))'

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=sum(rate(container_cpu_usage_seconds_total{namespace="default",pod=~"controllable-backend-.*",container!="POD"}[1m])) / 0.5'

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=ALERTS{alertname="AutoOrchScalePressure"}'
```

## Action Evidence

```bash
curl -s http://127.0.0.1:9093/api/v2/alerts
kubectl logs -n default deploy/autoorch-webhook --tail=220
curl -s http://127.0.0.1:18080/metrics

kubectl get deployment controllable-backend -n default \
  -o jsonpath='{.spec.replicas}{"\n"}{.status.readyReplicas}{"\n"}{.status.availableReplicas}{"\n"}'

kubectl get pods -n default -l app=controllable-backend \
  -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,CREATED:.metadata.creationTimestamp,PHASE:.status.phase,NODE:.spec.nodeName
```

## Stop Repeated Alert Posts

```bash
kubectl delete prometheusrule -n default autoorch-autoscale-pressure --ignore-not-found
```

## Cleanup

```bash
kubectl set env deployment/loadgenerator \
  TARGET=http://controllable-backend:5000/api/test \
  RPS=0 \
  CONCURRENCY=1 \
  --overwrite -n default

kubectl scale deployment/controllable-backend -n default --replicas=1

kubectl set env deployment/autoorch-webhook ACTION_MODE=stub --overwrite -n default

kubectl delete alertmanagerconfig -n default autoorch-m8-autoscale-route --ignore-not-found
kubectl delete prometheusrule -n default autoorch-autoscale-pressure --ignore-not-found

kubectl rollout status deployment/controllable-backend -n default --timeout=90s
kubectl rollout status deployment/loadgenerator -n default --timeout=90s
kubectl rollout status deployment/autoorch-webhook -n default --timeout=90s
```

## Final Confirmation

```bash
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
kubectl get prometheusrule -n default
kubectl get alertmanagerconfig -n default
curl -s http://127.0.0.1:18080/health
curl -s http://127.0.0.1:5000/metrics
```
