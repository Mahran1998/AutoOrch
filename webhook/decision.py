from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


FEATURES = ["rps", "p95", "http_5xx_rate", "cpu_sat"]
AUTOSCALE_FEATURES = FEATURES
RESTART_FEATURES = FEATURES


@dataclass
class RestartContext:
    restart_evidence: float = 0.0
    available_replicas: float = 0.0
    unavailable_replicas: float = 0.0
    desired_replicas: float = 0.0
    missing_metrics: List[str] = field(default_factory=list)
    query_errors: List[str] = field(default_factory=list)

    @property
    def degraded_availability(self) -> bool:
        if self.unavailable_replicas > 0:
            return True
        if self.desired_replicas > 0 and self.available_replicas < self.desired_replicas:
            return True
        return False

    @property
    def instability_present(self) -> bool:
        return self.restart_evidence > 0.0 or self.degraded_availability

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["degraded_availability"] = self.degraded_availability
        data["instability_present"] = self.instability_present
        return data


@dataclass
class DecisionResult:
    candidate_action: str
    final_action: str
    reason: str
    p_autoscale: Optional[float]
    p_restart: Optional[float]
    signals: Dict[str, Any]

    @property
    def decision(self) -> str:
        return self.final_action

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_action": self.candidate_action,
            "final_action": self.final_action,
            "decision": self.final_action,
            "reason": self.reason,
            "p_autoscale": self.p_autoscale,
            "p_restart": self.p_restart,
            "signals": self.signals,
        }


def compute_cpu_saturation(
    cpu_usage: Optional[float],
    cpu_limit: Optional[float],
    fallback_limit: float,
) -> float:
    usage = float(cpu_usage or 0.0)
    limit = float(cpu_limit or 0.0)
    if limit <= 0.0:
        limit = float(fallback_limit)
    if limit <= 0.0:
        return 0.0
    return usage / limit


def build_feature_vector(features: Dict[str, float], feature_order: List[str]) -> List[float]:
    return [float(features[name]) for name in feature_order]


def build_autoscale_vector(features: Dict[str, float], feature_order: List[str]) -> List[float]:
    return build_feature_vector(features, feature_order)


def decide_action(
    *,
    features: Dict[str, float],
    context: RestartContext,
    p_autoscale: Optional[float],
    p_restart: Optional[float],
    autoscale_threshold: float,
    restart_threshold: float,
    alert_status: str = "firing",
    autoscale_model_ready: bool = True,
    restart_model_ready: bool = True,
) -> DecisionResult:
    alert_status = (alert_status or "firing").lower()
    signals = {
        "feature_order": list(FEATURES),
        "missing_metrics": list(context.missing_metrics),
        "query_errors": list(context.query_errors),
        "alert_status": alert_status,
        "autoscale_model_ready": bool(autoscale_model_ready),
        "restart_model_ready": bool(restart_model_ready),
    }

    if alert_status == "resolved":
        return DecisionResult(
            candidate_action="no_action",
            final_action="no_action",
            reason="below_threshold",
            p_autoscale=p_autoscale,
            p_restart=p_restart,
            signals=signals,
        )

    if context.missing_metrics or context.query_errors:
        return DecisionResult(
            candidate_action="notify_human",
            final_action="notify_human",
            reason="missing_or_stale_metrics",
            p_autoscale=p_autoscale,
            p_restart=p_restart,
            signals=signals,
        )

    if not autoscale_model_ready:
        raise RuntimeError("autoscale model unavailable")

    if p_autoscale is not None and p_autoscale >= autoscale_threshold:
        return DecisionResult(
            candidate_action="auto_scale",
            final_action="auto_scale",
            reason="autoscale_confident",
            p_autoscale=p_autoscale,
            p_restart=p_restart,
            signals=signals,
        )

    if not restart_model_ready:
        return DecisionResult(
            candidate_action="no_action",
            final_action="no_action",
            reason="below_threshold_or_restart_model_unavailable",
            p_autoscale=p_autoscale,
            p_restart=p_restart,
            signals=signals,
        )

    if p_restart is not None and p_restart >= restart_threshold:
        return DecisionResult(
            candidate_action="auto_restart",
            final_action="auto_restart",
            reason="restart_confident",
            p_autoscale=p_autoscale,
            p_restart=p_restart,
            signals=signals,
        )

    return DecisionResult(
        candidate_action="no_action",
        final_action="no_action",
        reason="below_threshold",
        p_autoscale=p_autoscale,
        p_restart=p_restart,
        signals=signals,
    )
