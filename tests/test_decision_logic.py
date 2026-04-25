from __future__ import annotations

import unittest

from webhook.decision import FEATURES, RestartContext, build_feature_vector, compute_cpu_saturation, decide_action


class DecisionLogicTests(unittest.TestCase):
    def test_compute_cpu_saturation_uses_fallback_limit(self) -> None:
        self.assertAlmostEqual(compute_cpu_saturation(0.21, None, 0.3), 0.7)

    def test_autoscale_decision_when_probability_high_and_errors_low(self) -> None:
        result = decide_action(
            features={"rps": 900.0, "p95": 0.02, "http_5xx_rate": 0.0, "cpu_sat": 0.95},
            context=RestartContext(),
            p_autoscale=0.96,
            p_restart=0.10,
            autoscale_threshold=0.90,
            restart_threshold=0.90,
        )
        self.assertEqual(result.decision, "auto_scale")
        self.assertEqual(result.candidate_action, "auto_scale")
        self.assertEqual(result.final_action, "auto_scale")
        self.assertEqual(result.reason, "autoscale_confident")

    def test_restart_decision_when_probability_high_and_autoscale_low(self) -> None:
        result = decide_action(
            features={"rps": 60.0, "p95": 0.5, "http_5xx_rate": 0.25, "cpu_sat": 0.22},
            context=RestartContext(restart_evidence=2.0, available_replicas=0.0, unavailable_replicas=1.0, desired_replicas=1.0),
            p_autoscale=0.12,
            p_restart=0.94,
            autoscale_threshold=0.90,
            restart_threshold=0.90,
        )
        self.assertEqual(result.decision, "auto_restart")
        self.assertEqual(result.candidate_action, "auto_restart")
        self.assertEqual(result.final_action, "auto_restart")
        self.assertEqual(result.reason, "restart_confident")

    def test_no_action_when_model_probabilities_are_low(self) -> None:
        result = decide_action(
            features={"rps": 55.0, "p95": 0.3, "http_5xx_rate": 0.25, "cpu_sat": 0.15},
            context=RestartContext(),
            p_autoscale=0.10,
            p_restart=0.40,
            autoscale_threshold=0.90,
            restart_threshold=0.90,
        )
        self.assertEqual(result.decision, "no_action")
        self.assertEqual(result.reason, "below_threshold")

    def test_no_action_when_restart_model_missing_and_autoscale_low(self) -> None:
        result = decide_action(
            features={"rps": 55.0, "p95": 0.3, "http_5xx_rate": 0.25, "cpu_sat": 0.15},
            context=RestartContext(),
            p_autoscale=0.10,
            p_restart=None,
            autoscale_threshold=0.90,
            restart_threshold=0.90,
            restart_model_ready=False,
        )
        self.assertEqual(result.decision, "no_action")
        self.assertEqual(result.candidate_action, "no_action")
        self.assertEqual(result.final_action, "no_action")
        self.assertEqual(result.reason, "below_threshold_or_restart_model_unavailable")

    def test_no_action_when_benign_and_recovered(self) -> None:
        result = decide_action(
            features={"rps": 40.0, "p95": 0.01, "http_5xx_rate": 0.0, "cpu_sat": 0.12},
            context=RestartContext(),
            p_autoscale=0.04,
            p_restart=0.02,
            autoscale_threshold=0.90,
            restart_threshold=0.90,
            alert_status="resolved",
        )
        self.assertEqual(result.decision, "no_action")
        self.assertEqual(result.reason, "below_threshold")

    def test_feature_order_is_fixed(self) -> None:
        self.assertEqual(FEATURES, ["rps", "p95", "http_5xx_rate", "cpu_sat"])
        vector = build_feature_vector(
            {"rps": 1.0, "p95": 2.0, "http_5xx_rate": 3.0, "cpu_sat": 4.0},
            FEATURES,
        )
        self.assertEqual(vector, [1.0, 2.0, 3.0, 4.0])


if __name__ == "__main__":
    unittest.main()
