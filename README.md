AutoOrch — Alert Orchestrator for safe automated remediation in Kubernetes.

## Summary
Ingests Prometheus/Alertmanager alerts, enriches them, classifies with a lightweight ML model, and executes audited Ansible playbooks for low-risk incidents.

## Quickstart (dev)
1. Build webhook image: docker build -t autoorch-webhook ./webhook
2. Load into kind: kind load docker-image autoorch-webhook --name <your-kind>
3. Deploy manifests in /deploy

## Folders
- /webhook : FastAPI app + Dockerfile
- /playbooks : ansible playbooks (restart, scale, collect_diag)
- /scripts : run_constant.sh, run_schedule.py, fault injectors
- /ml : training notebook and model
