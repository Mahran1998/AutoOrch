# M8A Commands

## Commit Reviewed Plan

```bash
git add evidence/M8_autoscale/decision_stub/PLAN.md \
  evidence/M8_autoscale/decision_stub/manifests/alertmanagerconfig-autoscale.yaml \
  evidence/M8_autoscale/decision_stub/manifests/prometheusrule-autoscale.yaml \
  evidence/M8_autoscale/decision_stub/screenshots/README.md

git commit -m "Add M8 AutoScale decision proof plan"
git push origin main
```

Committed as:

```text
3dcc5085 Add M8 AutoScale decision proof plan
```

## Preflight

```bash
git status --short
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
kubectl get deploy -n default autoorch-webhook \
  -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="ACTION_MODE")].value}{"\n"}'
kubectl get deploy -n default controllable-backend \
  -o jsonpath='{.spec.replicas}{"\n"}{.status.readyReplicas}{"\n"}{.status.availableReplicas}{"\n"}'
kubectl get prometheusrule -n default
```

AutoOrch was initially unavailable, so the planned memory-reset rollout was used.

## Reset AutoOrch Memory While Staying in Stub Mode

```bash
kubectl rollout restart deployment/autoorch-webhook -n default
kubectl rollout status deployment/autoorch-webhook -n default --timeout=90s
kubectl get pods -n default -o wide
kubectl logs -n default deploy/autoorch-webhook --tail=200
```

The rollout status command timed out narrowly, but the deployment became healthy shortly after. AutoOrch remained in `ACTION_MODE=stub`.

## Port-Forwards

```bash
kubectl port-forward -n default svc/controllable-backend 5000:5000
kubectl port-forward -n default svc/autoorch-webhook 18080:8080
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-prometheus 9090:9090
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-alertmanager 9093:9093
```

## Pre-Run Checks

```bash
curl -s http://127.0.0.1:5000/metrics
curl -s http://127.0.0.1:18080/health
kubectl get deploy -n default controllable-backend \
  -o custom-columns=NAME:.metadata.name,READY:.status.readyReplicas,REPLICAS:.spec.replicas,AVAILABLE:.status.availableReplicas
```

## Apply Temporary M8A Route and Rule

```bash
kubectl apply -f evidence/M8_autoscale/decision_stub/manifests/alertmanagerconfig-autoscale.yaml
kubectl apply -f evidence/M8_autoscale/decision_stub/manifests/prometheusrule-autoscale.yaml
```

## Start Calibrated Load

```bash
kubectl set env deployment/loadgenerator \
  TARGET=http://controllable-backend:5000/api/test \
  RPS=500 \
  CONCURRENCY=75 \
  --overwrite -n default

kubectl rollout status deployment/loadgenerator -n default --timeout=90s
sleep 120
```

## Capture Evidence

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

curl -s http://127.0.0.1:9093/api/v2/alerts
curl -s http://127.0.0.1:18080/metrics
kubectl logs -n default deploy/autoorch-webhook --tail=500
kubectl get deploy -n default controllable-backend \
  -o custom-columns=NAME:.metadata.name,READY:.status.readyReplicas,REPLICAS:.spec.replicas,AVAILABLE:.status.availableReplicas
```

## Stop Repeated Posts and Cleanup

```bash
kubectl delete prometheusrule -n default autoorch-autoscale-pressure --ignore-not-found

kubectl set env deployment/loadgenerator \
  TARGET=http://controllable-backend:5000/api/test \
  RPS=0 \
  CONCURRENCY=1 \
  --overwrite -n default

kubectl rollout status deployment/loadgenerator -n default --timeout=90s

kubectl delete alertmanagerconfig -n default autoorch-m8-autoscale-route --ignore-not-found

curl -s http://127.0.0.1:5000/metrics
curl -s http://127.0.0.1:18080/health
kubectl get deploy -n default controllable-backend autoorch-webhook loadgenerator
kubectl get deploy -n default loadgenerator \
  -o jsonpath='{.spec.template.spec.containers[0].env}{"\n"}'
kubectl get prometheusrule -n default
kubectl get alertmanagerconfig -n default
pgrep -af 'kubectl port-forward' || true
```

