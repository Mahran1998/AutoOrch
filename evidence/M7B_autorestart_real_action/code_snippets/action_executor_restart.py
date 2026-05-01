def _run_restart(self, target: ActionTarget, started_at: float) -> Dict[str, Any]:
    if self.mode == "kubectl":
        cmd = [
            self.kubectl_binary,
            "rollout",
            "restart",
            f"deployment/{target.workload}",
            "-n",
            target.namespace,
        ]
        return self._run_command("auto_restart", cmd, started_at, {})

    if self.mode == "ansible":
        playbook = self.playbook_dir / "restart_deployment.yml"
        cmd = [
            self.ansible_binary,
            str(playbook),
            "-e",
            f"namespace={target.namespace}",
            "-e",
            f"workload={target.workload}",
        ]
        return self._run_command("auto_restart", cmd, started_at, {})

    return self._result("auto_restart", "blocked", started_at, details={"reason": f"unknown_mode:{self.mode}"})

