# M6B Commands

## Enable Alertmanager

```bash
helm get values prometheus-stack -n monitoring -o yaml > /tmp/prometheus-stack-values-before-alertmanager.yaml
printf 'alertmanager:\n  enabled: true\n' > /tmp/enable-alertmanager-values.yaml
helm upgrade prometheus-stack prometheus-community/kube-prometheus-stack \
  --version 79.4.0 \
  -n monitoring \
  -f /tmp/enable-alertmanager-values.yaml \
  --reuse-values
```

## Verify Alertmanager

```bash
kubectl get pods -n monitoring
kubectl get svc -n monitoring
kubectl get alertmanager -A
kubectl get alertmanagerconfig -A
kubectl get alertmanager -n monitoring prometheus-stack-kube-prom-alertmanager -o yaml
```

## Apply Narrow M6 Route And Test Alert

```bash
kubectl apply -f evidence/M6B_alertmanager_route/manifests/alertmanagerconfig-autoorch.yaml
kubectl apply -f evidence/M6B_alertmanager_route/manifests/prometheusrule-autoorch-m6-test.yaml
```

## Check Alert State And AutoOrch Evidence

```bash
kubectl port-forward -n default svc/autoorch-webhook 8080:8080
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-prometheus 9090:9090
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-alertmanager 9093:9093

curl -sG http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=ALERTS{alertname="AutoOrchM6TestAlert"}'

curl -s http://127.0.0.1:9093/api/v2/alerts
curl -s http://127.0.0.1:8080/metrics
kubectl logs -n default deploy/autoorch-webhook --tail=120
```

## Cleanup

```bash
kubectl delete prometheusrule -n default autoorch-m6-test-alert
pkill -f 'kubectl port-forward -n default svc/autoorch-webhook 8080:8080'
pkill -f 'kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-prometheus 9090:9090'
pkill -f 'kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-alertmanager 9093:9093'
```
