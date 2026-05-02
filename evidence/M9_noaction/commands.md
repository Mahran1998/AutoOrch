# M9 Commands

## Plan Commit

```bash
git add evidence/M9_noaction/PLAN.md \
  evidence/M9_noaction/manifests/alertmanagerconfig-noaction.yaml \
  evidence/M9_noaction/manifests/prometheusrule-noaction.yaml \
  evidence/M9_noaction/screenshots/README.md

git commit -m "Add M9 NoAction proof plan"
git push origin main
```

## Preflight

```bash
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator

kubectl get deploy -n default autoorch-webhook \
  -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="ACTION_MODE")].value}{"\n"}'

kubectl get deployment controllable-backend -n default \
  -o jsonpath='{.spec.replicas}{"\n"}{.status.readyReplicas}{"\n"}{.status.availableReplicas}{"\n"}'

kubectl get pods -n default -l app=controllable-backend \
  -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,CREATED:.metadata.creationTimestamp,PHASE:.status.phase,NODE:.spec.nodeName

kubectl get prometheusrule -n default
kubectl get alertmanagerconfig -n default
```

## Port-Forwards

```bash
kubectl port-forward -n default svc/controllable-backend 5000:5000
kubectl port-forward -n default svc/autoorch-webhook 18080:8080
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-prometheus 9090:9090
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-alertmanager 9093:9093
```

## Health And Fault State

```bash
curl -s http://127.0.0.1:5000/health
curl -s http://127.0.0.1:5000/metrics
curl -s http://127.0.0.1:18080/health
curl -s http://127.0.0.1:18080/metrics
```

## Healthy Low Load

```bash
kubectl set env deployment/loadgenerator \
  TARGET=http://controllable-backend:5000/api/test \
  RPS=10 \
  CONCURRENCY=5 \
  --overwrite -n default

kubectl rollout status deployment/loadgenerator -n default --timeout=90s
```

## Feature Precheck

```bash
curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=sum(rate(http_requests_total{exported_endpoint="/api/test"}[1m]))'

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[1m])) by (le))'

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=(sum(rate(http_requests_total{exported_endpoint="/api/test",status=~"5.."}[1m])) or vector(0))'

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=sum(rate(container_cpu_usage_seconds_total{namespace="default",pod=~"controllable-backend-.*",container!="POD"}[1m])) / 0.5'
```

## Apply Temporary M9 Benign Alert

```bash
kubectl apply -f evidence/M9_noaction/manifests/alertmanagerconfig-noaction.yaml
kubectl apply -f evidence/M9_noaction/manifests/prometheusrule-noaction.yaml
```

## Decision Evidence

```bash
curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=ALERTS{alertname="AutoOrchNoActionBenign"}'

curl -s http://127.0.0.1:9093/api/v2/alerts
kubectl logs -n default deploy/autoorch-webhook --tail=260

kubectl get deployment controllable-backend -n default \
  -o jsonpath='{.spec.replicas}{"\n"}{.status.readyReplicas}{"\n"}{.status.availableReplicas}{"\n"}'

kubectl get pods -n default -l app=controllable-backend \
  -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,CREATED:.metadata.creationTimestamp,PHASE:.status.phase,NODE:.spec.nodeName
```

## Cleanup

```bash
kubectl delete prometheusrule -n default autoorch-noaction-benign --ignore-not-found
kubectl delete alertmanagerconfig -n default autoorch-m9-noaction-route --ignore-not-found

kubectl set env deployment/loadgenerator \
  TARGET=http://controllable-backend:5000/api/test \
  RPS=0 \
  CONCURRENCY=1 \
  --overwrite -n default

kubectl rollout status deployment/loadgenerator -n default --timeout=90s
```

## Final Confirmation

```bash
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
kubectl get prometheusrule -n default
kubectl get alertmanagerconfig -n default
curl -s http://127.0.0.1:18080/health
curl -s http://127.0.0.1:5000/metrics
curl -s http://127.0.0.1:18080/metrics
```
