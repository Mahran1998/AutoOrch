from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class ActionTarget:
    namespace: str
    workload: str
    current_replicas: Optional[int] = None


class ActionExecutor:
    def __init__(
        self,
        *,
        mode: str = "stub",
        playbook_dir: str = "playbooks",
        ansible_binary: str = "ansible-playbook",
        kubectl_binary: str = "kubectl",
        timeout_seconds: int = 120,
        scale_step: int = 1,
        collect_diagnostics_on_notify: bool = True,
    ) -> None:
        self.mode = mode
        self.playbook_dir = Path(playbook_dir)
        self.ansible_binary = ansible_binary
        self.kubectl_binary = kubectl_binary
        self.timeout_seconds = timeout_seconds
        self.scale_step = scale_step
        self.collect_diagnostics_on_notify = collect_diagnostics_on_notify

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

        if decision == "auto_restart":
            return self._run_restart(target, started_at)

        if decision == "notify_human":
            if self.collect_diagnostics_on_notify:
                return self._run_collect_diagnostics(target, started_at)
            return self._result(decision, "recorded", started_at, details={"reason": "notify_only"})

        return self._result(decision, "skipped", started_at, details={"reason": "unsupported_decision"})

    def _run_scale(self, target: ActionTarget, desired_replicas: int, started_at: float) -> Dict[str, Any]:
        if self.mode == "kubectl":
            cmd = [
                self.kubectl_binary,
                "scale",
                f"deployment/{target.workload}",
                "-n",
                target.namespace,
                f"--replicas={desired_replicas}",
            ]
            return self._run_command("auto_scale", cmd, started_at, {"desired_replicas": desired_replicas})

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

        return self._result("auto_scale", "blocked", started_at, details={"reason": f"unknown_mode:{self.mode}"})

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

    def _run_collect_diagnostics(self, target: ActionTarget, started_at: float) -> Dict[str, Any]:
        if self.mode == "kubectl":
            cmd = [
                self.kubectl_binary,
                "describe",
                f"deployment/{target.workload}",
                "-n",
                target.namespace,
            ]
            return self._run_command("notify_human", cmd, started_at, {"diagnostics": "kubectl_describe"})

        if self.mode == "ansible":
            playbook = self.playbook_dir / "collect_diagnostics.yml"
            cmd = [
                self.ansible_binary,
                str(playbook),
                "-e",
                f"namespace={target.namespace}",
                "-e",
                f"workload={target.workload}",
            ]
            return self._run_command("notify_human", cmd, started_at, {"diagnostics": "ansible"})

        return self._result("notify_human", "recorded", started_at, details={"reason": "notify_only"})

    def _run_command(
        self,
        action_name: str,
        cmd: list[str],
        started_at: float,
        extra_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        binary = shutil.which(cmd[0])
        if binary is None:
            details = {"reason": f"binary_not_found:{cmd[0]}", **extra_details, "command": cmd}
            return self._result(action_name, "failed", started_at, details=details)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            details = {"reason": "timeout", "stdout": exc.stdout, "stderr": exc.stderr, **extra_details, "command": cmd}
            return self._result(action_name, "failed", started_at, details=details)

        details = {
            "command": cmd,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            **extra_details,
        }
        status = "success" if proc.returncode == 0 else "failed"
        return self._result(action_name, status, started_at, details=details)

    def _desired_replicas(self, current_replicas: Optional[int], max_replicas: int) -> Optional[int]:
        if current_replicas is None:
            return None
        current = int(current_replicas)
        if current >= max_replicas:
            return current
        return current + self.scale_step

    def _result(
        self,
        action_name: str,
        status: str,
        started_at: float,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "action": action_name,
            "status": status,
            "started_at": started_at,
            "finished_at": time.time(),
            "duration_seconds": round(time.time() - started_at, 6),
            "details": details,
        }
