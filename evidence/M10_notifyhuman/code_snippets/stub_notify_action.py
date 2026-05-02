if self.mode == "stub":
    details = {"mode": "stub", "target": {"namespace": target.namespace, "workload": target.workload}}
    if decision == "notify_human" and self.collect_diagnostics_on_notify:
        details["diagnostics"] = "simulated"
    return self._result(decision, "simulated", started_at, details=details)

