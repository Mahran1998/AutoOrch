from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

try:
    import webhook.main as webhook_main
    from webhook.decision import RestartContext
except Exception as exc:  # pragma: no cover - depends on local env
    webhook_main = None
    RestartContext = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


class FakeRequest:
    def __init__(self, payload: dict | None = None, raw_body: bytes | None = None) -> None:
        self.payload = payload
        self.raw_body = raw_body or b""

    async def json(self):
        if self.payload is None:
            raise ValueError("no json payload")
        return self.payload

    async def body(self) -> bytes:
        return self.raw_body


@unittest.skipIf(webhook_main is None, f"fastapi runtime dependencies unavailable: {IMPORT_ERROR}")
class WebhookIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        webhook_main.LAST_ACTION_AT.clear()
        webhook_main.CANDIDATE_STREAK.clear()
        webhook_main.SETTINGS.consecutive_escalation_count = 2
        webhook_main.SETTINGS.consecutive_memory_seconds = 300

    def _payload(self) -> dict:
        return {
            "status": "firing",
            "alerts": [{"labels": {"namespace": "default", "deployment": "demo-backend", "severity": "warning"}}],
        }

    def test_alert_endpoint_returns_auto_restart(self) -> None:
        features = {"rps": 70.0, "p95": 0.6, "http_5xx_rate": 0.30, "cpu_sat": 0.20}
        restart_context = RestartContext(
            restart_evidence=1.0,
            available_replicas=0.0,
            unavailable_replicas=1.0,
            desired_replicas=1.0,
        )
        with (
            patch.object(webhook_main, "fetch_signal_bundle", return_value=(features, restart_context)),
            patch.object(webhook_main, "autoscale_probability", return_value=0.11),
            patch.object(webhook_main, "restart_probability", return_value=0.94),
            patch.object(webhook_main, "MODEL_READY", True),
            patch.object(webhook_main, "RESTART_MODEL_READY", True),
            patch.object(
                webhook_main.ACTION_EXECUTOR,
                "execute",
                return_value={"action": "auto_restart", "status": "simulated", "duration_seconds": 0.01},
            ),
        ):
            response = asyncio.run(
                webhook_main.alert_receiver(
                    FakeRequest(
                        {
                            "status": "firing",
                            "alerts": [
                                {"labels": {"namespace": "default", "deployment": "demo-backend", "severity": "warning"}}
                            ],
                        }
                    )
                )
            )
        self.assertEqual(response["decision"], "auto_restart")
        self.assertEqual(response["candidate_action"], "auto_restart")
        self.assertEqual(response["final_action"], "auto_restart")
        self.assertEqual(response["reason"], "restart_confident")
        self.assertEqual(response["target"]["workload"], "demo-backend")

    def test_alert_endpoint_falls_back_to_notify_human_when_metrics_missing(self) -> None:
        features = {"rps": 0.0, "p95": 0.0, "http_5xx_rate": 0.0, "cpu_sat": 0.0}
        restart_context = RestartContext(missing_metrics=["rps"])
        with (
            patch.object(webhook_main, "fetch_signal_bundle", return_value=(features, restart_context)),
            patch.object(webhook_main, "autoscale_probability", return_value=None),
            patch.object(webhook_main, "restart_probability", return_value=None),
            patch.object(webhook_main, "MODEL_READY", True),
            patch.object(
                webhook_main.ACTION_EXECUTOR,
                "execute",
                return_value={"action": "notify_human", "status": "recorded", "duration_seconds": 0.01},
            ),
        ):
            response = asyncio.run(
                webhook_main.alert_receiver(
                    FakeRequest(
                        {
                            "status": "firing",
                            "alerts": [
                                {"labels": {"namespace": "default", "deployment": "demo-backend", "severity": "critical"}}
                            ],
                        }
                    )
                )
        )
        self.assertEqual(response["decision"], "notify_human")
        self.assertEqual(response["reason"], "missing_or_stale_metrics")

    def test_second_consecutive_auto_scale_candidate_escalates(self) -> None:
        features = {"rps": 900.0, "p95": 0.8, "http_5xx_rate": 0.0, "cpu_sat": 0.95}
        restart_context = RestartContext(desired_replicas=1.0, available_replicas=1.0)

        executed = []

        def recording_execute(*, decision, target, max_replicas):
            executed.append(decision)
            return {"action": decision, "status": "simulated", "duration_seconds": 0.01}

        payload = self._payload()

        with (
            patch.object(webhook_main, "fetch_signal_bundle", return_value=(features, restart_context)),
            patch.object(webhook_main, "autoscale_probability", return_value=0.95),
            patch.object(webhook_main, "restart_probability", side_effect=AssertionError("restart should not run")),
            patch.object(webhook_main, "MODEL_READY", True),
            patch.object(webhook_main, "RESTART_MODEL_READY", True),
            patch.object(webhook_main.ACTION_EXECUTOR, "execute", side_effect=recording_execute),
        ):
            first = asyncio.run(webhook_main.alert_receiver(FakeRequest(payload)))
            second = asyncio.run(webhook_main.alert_receiver(FakeRequest(payload)))

        self.assertEqual(first["decision"], "auto_scale")
        self.assertEqual(first["candidate_action"], "auto_scale")
        self.assertEqual(first["final_action"], "auto_scale")
        self.assertEqual(second["decision"], "notify_human")
        self.assertEqual(second["candidate_action"], "auto_scale")
        self.assertEqual(second["final_action"], "notify_human")
        self.assertEqual(second["reason"], "repeated_action")
        self.assertEqual(executed, ["auto_scale", "notify_human"])

    def test_second_consecutive_auto_restart_candidate_escalates_before_restart_execution(self) -> None:
        features = {"rps": 60.0, "p95": 0.7, "http_5xx_rate": 0.35, "cpu_sat": 0.20}
        restart_context = RestartContext(desired_replicas=1.0, available_replicas=1.0)
        executed = []

        def recording_execute(*, decision, target, max_replicas):
            executed.append(decision)
            return {"action": decision, "status": "simulated", "duration_seconds": 0.01}

        with (
            patch.object(webhook_main, "fetch_signal_bundle", return_value=(features, restart_context)),
            patch.object(webhook_main, "autoscale_probability", return_value=0.10),
            patch.object(webhook_main, "restart_probability", return_value=0.96),
            patch.object(webhook_main, "MODEL_READY", True),
            patch.object(webhook_main, "RESTART_MODEL_READY", True),
            patch.object(webhook_main.ACTION_EXECUTOR, "execute", side_effect=recording_execute),
        ):
            first = asyncio.run(webhook_main.alert_receiver(FakeRequest(self._payload())))
            second = asyncio.run(webhook_main.alert_receiver(FakeRequest(self._payload())))

        self.assertEqual(first["decision"], "auto_restart")
        self.assertEqual(second["candidate_action"], "auto_restart")
        self.assertEqual(second["decision"], "notify_human")
        self.assertEqual(second["reason"], "repeated_action")
        self.assertEqual(executed, ["auto_restart", "notify_human"])

    def test_missing_restart_model_returns_no_action_when_autoscale_low(self) -> None:
        features = {"rps": 50.0, "p95": 0.2, "http_5xx_rate": 0.10, "cpu_sat": 0.20}
        restart_context = RestartContext(desired_replicas=1.0, available_replicas=1.0)

        with (
            patch.object(webhook_main, "fetch_signal_bundle", return_value=(features, restart_context)),
            patch.object(webhook_main, "autoscale_probability", return_value=0.10),
            patch.object(webhook_main, "restart_probability", side_effect=AssertionError("restart should not run")),
            patch.object(webhook_main, "MODEL_READY", True),
            patch.object(webhook_main, "RESTART_MODEL_READY", False),
            patch.object(
                webhook_main.ACTION_EXECUTOR,
                "execute",
                return_value={"action": "no_action", "status": "skipped", "duration_seconds": 0.01},
            ),
        ):
            response = asyncio.run(webhook_main.alert_receiver(FakeRequest(self._payload())))

        self.assertEqual(response["candidate_action"], "no_action")
        self.assertEqual(response["final_action"], "no_action")
        self.assertEqual(response["decision"], "no_action")
        self.assertEqual(response["reason"], "below_threshold_or_restart_model_unavailable")

    def test_action_failure_preserves_candidate_and_returns_notify_human(self) -> None:
        features = {"rps": 900.0, "p95": 0.8, "http_5xx_rate": 0.0, "cpu_sat": 0.95}
        restart_context = RestartContext(desired_replicas=1.0, available_replicas=1.0)

        with (
            patch.object(webhook_main, "fetch_signal_bundle", return_value=(features, restart_context)),
            patch.object(webhook_main, "autoscale_probability", return_value=0.95),
            patch.object(webhook_main, "restart_probability", side_effect=AssertionError("restart should not run")),
            patch.object(webhook_main, "MODEL_READY", True),
            patch.object(webhook_main, "RESTART_MODEL_READY", True),
            patch.object(
                webhook_main.ACTION_EXECUTOR,
                "execute",
                return_value={"action": "auto_scale", "status": "failed", "duration_seconds": 0.01},
            ),
        ):
            response = asyncio.run(webhook_main.alert_receiver(FakeRequest(self._payload())))

        self.assertEqual(response["candidate_action"], "auto_scale")
        self.assertEqual(response["final_action"], "notify_human")
        self.assertEqual(response["decision"], "notify_human")
        self.assertEqual(response["reason"], "action_failed")
        self.assertEqual(response["failed_action_result"]["action"], "auto_scale")

    def test_non_json_payload_falls_back_to_notify_human(self) -> None:
        response = asyncio.run(webhook_main.alert_receiver(FakeRequest(None, raw_body=b"oops")))
        self.assertEqual(response["decision"], "notify_human")
        self.assertEqual(response["final_action"], "notify_human")
        self.assertEqual(response["reason"], "missing_or_stale_metrics")


if __name__ == "__main__":
    unittest.main()
