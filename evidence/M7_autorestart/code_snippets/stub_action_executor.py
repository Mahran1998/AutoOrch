class ActionExecutor:
    def execute(self, *, decision, target, max_replicas):
        if decision == "no_action":
            return {"action": "no_action", "status": "skipped"}

        if self.mode == "stub":
            return {
                "action": decision,
                "status": "simulated",
                "details": {
                    "mode": "stub",
                    "target": {
                        "namespace": target.namespace,
                        "workload": target.workload,
                    },
                },
            }

        if decision == "auto_restart":
            return self._run_restart(target)
