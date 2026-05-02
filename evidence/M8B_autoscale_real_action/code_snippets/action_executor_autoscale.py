```python
if decision == "auto_scale":
    desired = self._desired_replicas(target.current_replicas, max_replicas)
    if desired is None:
        return self._result(decision, "blocked", started_at, details={"reason": "missing_current_replicas"})
    return self._run_scale(target, desired, started_at)

def _run_scale(self, target: ActionTarget, desired_replicas: int, started_at: float) -> Dict[str, Any]:
    if self.mode == "ansible":
        playbook = self.playbook_dir / "scale_deployment.yml"
        cmd = [
            self.ansible_binary,
            str(playbook),
            "-e",
            f"namespace={target.namespace}",
            "-e",
            f"workload={target.workload}",
            "-e",
            f"desired_replicas={desired_replicas}",
        ]
        return self._run_command("auto_scale", cmd, started_at, {"desired_replicas": desired_replicas})
```
