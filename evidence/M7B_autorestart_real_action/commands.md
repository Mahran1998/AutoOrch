# M7B Commands

## Preflight

```bash
git status --short
kubectl get deploy -n default autoorch-webhook controllable-backend loadgenerator
kubectl get pods -n default -o wide
kubectl get deploy -n default autoorch-webhook \
  -o jsonpath='{.spec.template.spec.serviceAccountName}{"\n"}{.spec.template.spec.containers[0].env[?(@.name=="ACTION_MODE")].value}{"\n"}{.spec.template.spec.containers[0].env[?(@.name=="PLAYBOOK_DIR")].value}{"\n"}'
kubectl auth can-i get deployment/controllable-backend -n default --as=system:serviceaccount:default:autoorch-runner
kubectl auth can-i patch deployment/controllable-backend -n default --as=system:serviceaccount:default:autoorch-runner
kubectl auth can-i patch deployment/demo-backend -n default --as=system:serviceaccount:default:autoorch-runner
```

## Safe Runtime Adjustment

```bash
.venv/bin/python -m unittest discover -s tests -v
kubectl apply -f deploy/autoorch-alertmanager-webhook.yaml
kubectl rollout status deployment/autoorch-webhook -n default --timeout=90s
kubectl apply -f evidence/M7B_autorestart_real_action/manifests/alertmanagerconfig-autorestart.yaml
```

## Port-Forwards

```bash
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-prometheus 9090:9090
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-alertmanager 9093:9093
kubectl port-forward -n default svc/controllable-backend 5000:5000
kubectl port-forward -n default svc/loadgenerator-metrics 8081:8080
kubectl port-forward -n default svc/autoorch-webhook 18080:8080
```

## Switch AutoOrch To Ansible

```bash
kubectl set env deployment/autoorch-webhook ACTION_MODE=ansible --overwrite -n default
kubectl rollout status deployment/autoorch-webhook -n default --timeout=90s
curl -s http://127.0.0.1:18080/health
```

## Configure Traffic

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
```

## Capture Before State

```bash
kubectl get pods -n default -l app=controllable-backend \
  -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,CREATED:.metadata.creationTimestamp,PHASE:.status.phase,NODE:.spec.nodeName

kubectl get deploy -n default controllable-backend \
  -o jsonpath='{.metadata.generation}{"\n"}{.status.observedGeneration}{"\n"}{.spec.template.metadata.annotations}{"\n"}'
```

## Trigger M7B

```bash
kubectl delete prometheusrule -n default autoorch-autorestart-fault --ignore-not-found
kubectl apply -f evidence/M7B_autorestart_real_action/manifests/prometheusrule-autorestart.yaml

curl -s -X POST "http://127.0.0.1:5000/inject-latency?ms=700"
curl -s -X POST http://127.0.0.1:5000/inject-errors
sleep 90
```

## Verify

```bash
curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=sum(rate(http_requests_total{exported_endpoint="/api/test",status=~"5.."}[1m]))'

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[1m])) by (le))'

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=sum(rate(container_cpu_usage_seconds_total{namespace="default",pod=~"controllable-backend-.*",container!="POD"}[1m])) / 0.5'

curl -s http://127.0.0.1:9093/api/v2/alerts
kubectl logs -n default deploy/autoorch-webhook --tail=260
kubectl rollout status deployment/controllable-backend -n default --timeout=120s
kubectl get pods -n default -l app=controllable-backend \
  -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,CREATED:.metadata.creationTimestamp,PHASE:.status.phase,NODE:.spec.nodeName
```

## Cleanup

```bash
kubectl delete prometheusrule -n default autoorch-autorestart-fault --ignore-not-found
curl -s -X POST "http://127.0.0.1:5000/inject-latency?ms=0"
curl -s http://127.0.0.1:5000/metrics | grep -E "error_injection_enabled|latency_injection_enabled"
curl -s -X POST http://127.0.0.1:8081/control \
  -H 'Content-Type: application/json' \
  -d '{"rps":0,"concurrency":1}'
kubectl set env deployment/loadgenerator RPS="0" CONCURRENCY="1" --overwrite -n default
kubectl rollout status deployment/loadgenerator -n default --timeout=60s
kubectl set env deployment/autoorch-webhook ACTION_MODE=stub --overwrite -n default
kubectl rollout status deployment/autoorch-webhook -n default --timeout=90s
curl -s http://127.0.0.1:18080/health
kubectl get deploy -n default autoorch-webhook controllable-backend loadgenerator
```

