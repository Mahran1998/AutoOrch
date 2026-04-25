# AutoOrch

Alert orchestrator for safe automated remediation in Kubernetes.

## Summary
AutoOrch ingests Prometheus Alertmanager alerts, enriches them with recent Prometheus metrics, and evaluates a conservative two-model decision flow:

```text
Alert -> enrichment -> [rps, p95, http_5xx_rate, cpu_sat]
  -> autoscale_classifier.joblib   P(auto_scale) >= 0.90 -> auto_scale
  -> otherwise restart_classifier.joblib P(auto_restart) >= 0.90 -> auto_restart
  -> repeated automation candidate within 300s -> notify_human
  -> otherwise -> no_action
```

Both classifiers use the same four-feature vector. The autoscale model is required at runtime; the restart model is optional until restart experiment data is collected. Missing or stale Prometheus metrics escalate to `notify_human`; low model confidence returns `no_action`.

Runtime model artifacts live in `webhook/models/` in the repository. The webhook container uses `/app/webhook/models/...` because the Docker build context is `./webhook` and the Dockerfile copies it into `/app/webhook`.

The restart model is trained from controlled fault-injection data; the labeling rule for the training dataset is intentionally simple and reproducible: `http_5xx_rate >= 0.20`, `cpu_sat < 0.70`, and `p95 > 0.50`.

## Quickstart (dev)
1. Build webhook image: `docker build -t autoorch-webhook ./webhook`
2. Load into kind: `kind load docker-image autoorch-webhook --name <your-kind>`
3. Deploy manifests in `deploy/`

## Folders
- `webhook/`: FastAPI Alertmanager webhook and decision runtime.
- `webhook/models/`: current autoscale model artifact.
- `ml/restart/`: restart classifier training script.
- `scripts/`: dataset builders, experiment helpers, and autoscale training.
- `playbooks/`: Ansible runbooks for scale, restart, and diagnostic handoff.
- `experiments/`: reproducible training/evaluation datasets.
