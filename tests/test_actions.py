from __future__ import annotations

import unittest
from unittest.mock import patch

from webhook.actions import ActionExecutor, ActionTarget


class ActionExecutorTests(unittest.TestCase):
    def test_stub_executor_simulates_notify_with_diagnostics(self) -> None:
        executor = ActionExecutor(mode="stub", collect_diagnostics_on_notify=True)
        result = executor.execute(
            decision="notify_human",
            target=ActionTarget(namespace="default", workload="demo-backend", current_replicas=1),
            max_replicas=5,
        )
        self.assertEqual(result["status"], "simulated")
        self.assertEqual(result["action"], "notify_human")
        self.assertEqual(result["details"]["diagnostics"], "simulated")

    @patch("webhook.actions.shutil.which", return_value=None)
    def test_kubectl_executor_reports_missing_binary(self, _which) -> None:
        executor = ActionExecutor(mode="kubectl")
        result = executor.execute(
            decision="auto_restart",
            target=ActionTarget(namespace="default", workload="demo-backend", current_replicas=1),
            max_replicas=5,
        )
        self.assertEqual(result["status"], "failed")
        self.assertIn("binary_not_found", result["details"]["reason"])


if __name__ == "__main__":
    unittest.main()
