def execute(
    self,
    *,
    decision: str,
    target: ActionTarget,
    max_replicas: int,
) -> Dict[str, Any]:
    started_at = time.time()
    if decision == "no_action":
        return self._result(decision, "skipped", started_at, details={"reason": "no_action"})

    if self.mode == "stub":
        details = {"mode": "stub", "target": {"namespace": target.namespace, "workload": target.workload}}
        if decision == "notify_human" and self.collect_diagnostics_on_notify:
            details["diagnostics"] = "simulated"
        return self._result(decision, "simulated", started_at, details=details)

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

