# M8B-Prep: Real AutoScale Remediation Readiness

## Goal

Prepare the real AutoScale remediation milestone without executing it.

M8B will prove:

```text
AutoOrchScalePressure
-> Alertmanager
-> AutoOrch /alert
-> autoscale model predicts auto_scale
-> ACTION_MODE=ansible
-> scale_deployment.yml executes kubectl scale
-> controllable-backend replicas increase from 1 to 2
-> cleanup resets replicas to 1
```

## Current State

```text
ACTION_MODE=stub
MAX_REPLICAS=5
PLAYBOOK_DIR=/app/playbooks
controllable-backend replicas=1 ready=1 available=1
HPA: none
default PrometheusRule: none
```

## Scale Playbook

File:

```text
playbooks/scale_deployment.yml
```

Command executed by the playbook:

```bash
kubectl scale deployment/{{ workload }} -n {{ namespace }} --replicas={{ desired_replicas }}
```

Defaults:

```text
namespace=default
workload=demo-backend
desired_replicas=2
```

AutoOrch passes explicit runtime variables, so M8B should execute:

```bash
ansible-playbook /app/playbooks/scale_deployment.yml \
  -e namespace=default \
  -e workload=controllable-backend \
  -e desired_replicas=2
```

## Desired Replica Logic

AutoOrch computes desired replicas in `webhook/actions.py`:

```text
desired_replicas = current_replicas + scale_step
scale_step = 1
max_replicas = 5
```

With current replicas `1`, M8B should scale to `2`.

## Current RBAC

Current service account:

```text
autoorch-runner
```

Current Role grants:

```yaml
apiGroups: ["apps"]
resources: ["deployments"]
resourceNames: ["controllable-backend"]
verbs: ["get", "patch"]
```

Current `kubectl auth can-i` results:

```text
get deployment/controllable-backend: yes
patch deployment/controllable-backend: yes
get deployment/controllable-backend/scale: no
patch deployment/controllable-backend/scale: no
update deployment/controllable-backend/scale: no
patch deployment/demo-backend/scale: no
```

## Required M8B RBAC Patch

Real scaling needs narrow access to the `deployments/scale` subresource for only `controllable-backend`.

Proposed addition:

```yaml
- apiGroups: ["apps"]
  resources: ["deployments/scale"]
  resourceNames: ["controllable-backend"]
  verbs: ["get", "patch", "update"]
```

Rationale:

- `kubectl scale` interacts with the `scale` subresource.
- `get` allows reading current scale state.
- `patch`/`update` allow the scale operation depending on the Kubernetes client/server behavior.
- The `resourceNames` constraint keeps the permission scoped to `controllable-backend`.

Safety expectation after patch:

```text
patch deployment/controllable-backend/scale: yes
update deployment/controllable-backend/scale: yes
patch deployment/demo-backend/scale: no
```

## M8B Execution Mode

Use:

```text
ACTION_MODE=ansible
```

Only during the M8B execution window.

Immediately after M8B:

```text
ACTION_MODE=stub
```

## M8B Evidence Folder

```text
evidence/M8B_autoscale_real_action/
  PREP.md
  PLAN.md
  commands.md
  manifests/
  outputs/
  logs/
  code_snippets/
  screenshots/README.md
```

## M8B Safety Requirements

- Do not run real scaling until this prep is reviewed.
- Keep `ACTION_MODE=stub` during RBAC/tooling prep.
- Apply only narrow RBAC for `deployments/scale` on `controllable-backend`.
- Start from `controllable-backend` replicas `1`.
- Real M8B target should be replicas `2`.
- Cleanup must reset replicas to `1`.
- Delete temporary M8B PrometheusRule quickly after first successful scale action.
- Reset loadgenerator to `RPS=0`, `CONCURRENCY=1`.
- Confirm no error/latency injection.
- Confirm final deployments `1/1`.

## Recommendation

Proceed with an M8B readiness patch only:

1. update RBAC with narrow `deployments/scale` subresource access;
2. verify `kubectl auth can-i`;
3. verify `ansible-playbook --syntax-check /app/playbooks/scale_deployment.yml` inside the running AutoOrch pod;
4. keep `ACTION_MODE=stub`;
5. stop for review before real scaling.

