from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import joblib
import requests
from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from webhook.actions import ActionExecutor, ActionTarget
from webhook.decision import (
    AUTOSCALE_FEATURES,
    RESTART_FEATURES,
    RestartContext,
    build_autoscale_vector,
    build_feature_vector,
    compute_cpu_saturation,
    decide_action,
)


logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("autoorch")


@dataclass
class Settings:
    prom_base_url: str
    prom_window: str
    prom_restart_window: str
    prom_timeout: float
    cpu_limit_fallback: float
    autoscale_threshold: float
    restart_threshold: float
    consecutive_escalation_count: int
    consecutive_memory_seconds: int
    cooldown_seconds: int
    max_replicas: int
    target_namespace: str
    target_workload: str
    target_pod_regex: str
    allowed_namespaces: set[str]
    allowed_workloads: set[str]
    action_mode: str
    action_timeout_seconds: int
    collect_diagnostics_on_notify: bool
    playbook_dir: Path
    autoscale_model_path: Path
    autoscale_meta_path: Path
    restart_model_path: Path
    restart_meta_path: Path


def _env_csv(name: str, default: str) -> set[str]:
    raw = os.getenv(name, default)
    return {item.strip() for item in raw.split(",") if item.strip()}


def _default_model_path(filename: str) -> Path:
    return Path(__file__).resolve().parent / "models" / filename


def load_settings() -> Settings:
    target_namespace = os.getenv("TARGET_NAMESPACE", "default")
    target_workload = os.getenv("TARGET_WORKLOAD", "demo-backend")
    return Settings(
        prom_base_url=os.getenv("PROM_BASE_URL", "http://127.0.0.1:9090"),
        prom_window=os.getenv("PROM_WINDOW", "60s"),
        prom_restart_window=os.getenv("PROM_RESTART_WINDOW", "5m"),
        prom_timeout=float(os.getenv("PROM_TIMEOUT", "5")),
        cpu_limit_fallback=float(os.getenv("CPU_LIMIT_FALLBACK", "0.3")),
        autoscale_threshold=float(os.getenv("P_AUTO_SCALE_THRESHOLD", "0.90")),
        restart_threshold=float(os.getenv("P_AUTO_RESTART_THRESHOLD", "0.90")),
        consecutive_escalation_count=int(os.getenv("CONSECUTIVE_ESCALATION_COUNT", "2")),
        consecutive_memory_seconds=int(os.getenv("CONSECUTIVE_MEMORY_SECONDS", "300")),
        cooldown_seconds=int(os.getenv("COOLDOWN_SECONDS", "300")),
        max_replicas=int(os.getenv("MAX_REPLICAS", "5")),
        target_namespace=target_namespace,
        target_workload=target_workload,
        target_pod_regex=os.getenv("TARGET_POD_REGEX", f"{target_workload}-.*"),
        allowed_namespaces=_env_csv("ALLOWED_NAMESPACES", target_namespace),
        allowed_workloads=_env_csv("ALLOWED_WORKLOADS", target_workload),
        action_mode=os.getenv("ACTION_MODE", "stub").lower(),
        action_timeout_seconds=int(os.getenv("ACTION_TIMEOUT_SECONDS", "120")),
        collect_diagnostics_on_notify=os.getenv("COLLECT_DIAGNOSTICS_ON_NOTIFY", "true").lower() != "false",
        playbook_dir=Path(os.getenv("PLAYBOOK_DIR", "playbooks")),
        autoscale_model_path=Path(
            os.getenv("AUTOSCALE_MODEL_PATH", str(_default_model_path("autoscale_classifier.joblib")))
        ),
        autoscale_meta_path=Path(
            os.getenv("AUTOSCALE_META_PATH", str(_default_model_path("autoscale_classifier_meta.json")))
        ),
        restart_model_path=Path(
            os.getenv("RESTART_MODEL_PATH", str(_default_model_path("restart_classifier.joblib")))
        ),
        restart_meta_path=Path(
            os.getenv("RESTART_META_PATH", str(_default_model_path("restart_classifier_meta.json")))
        ),
    )


SETTINGS = load_settings()
MODEL = None
META: Dict[str, Any] = {}
FEATURE_ORDER: List[str] = list(AUTOSCALE_FEATURES)
MODEL_READY = False

RESTART_MODEL = None
RESTART_META: Dict[str, Any] = {}
RESTART_FEATURE_ORDER: List[str] = list(RESTART_FEATURES)
RESTART_MODEL_READY = False

LAST_ACTION_AT: Dict[str, float] = {}
CANDIDATE_STREAK: Dict[str, Dict[str, Any]] = {}

app = FastAPI(title="AutoOrch Webhook")

ALERTS_RECEIVED = Counter("autoorch_alerts_received_total", "Total alerts received by AutoOrch")
DECISIONS = Counter("autoorch_decisions_total", "Total decisions made by AutoOrch", ["decision"])
NOTIFY_HUMAN = Counter("autoorch_notify_human_total", "Number of notify_human decisions")
ACTIONS = Counter("autoorch_actions_total", "Total actions attempted by AutoOrch", ["action", "status"])
ACTION_FAILURES = Counter("autoorch_action_failures_total", "Failed actions attempted by AutoOrch", ["action"])
PROM_QUERY_SECONDS = Histogram("autoorch_prometheus_query_seconds", "Time spent querying Prometheus")
ACTION_DURATION_SECONDS = Histogram(
    "autoorch_action_duration_seconds",
    "Action execution time",
    ["action"],
)

ACTION_EXECUTOR = ActionExecutor(
    mode=SETTINGS.action_mode,
    playbook_dir=str(SETTINGS.playbook_dir),
    timeout_seconds=SETTINGS.action_timeout_seconds,
    collect_diagnostics_on_notify=SETTINGS.collect_diagnostics_on_notify,
)


# Restart model prediction metrics
RESTART_MODEL_PREDICTIONS = Counter(
    "autoorch_restart_model_predictions_total",
    "Restart model probability evaluations",
    ["result"],
)


def _metadata_features(meta: Dict[str, Any], default: List[str]) -> List[str]:
    raw = meta.get("feature_order") or meta.get("features") or meta.get("feature_names") or default
    return [str(item) for item in raw]


@app.on_event("startup")
def load_model() -> None:
    global MODEL, META, FEATURE_ORDER, MODEL_READY
    global RESTART_MODEL, RESTART_META, RESTART_FEATURE_ORDER, RESTART_MODEL_READY

    MODEL = None
    META = {}
    FEATURE_ORDER = list(AUTOSCALE_FEATURES)
    MODEL_READY = False
    RESTART_MODEL = None
    RESTART_META = {}
    RESTART_FEATURE_ORDER = list(RESTART_FEATURES)
    RESTART_MODEL_READY = False

    model_path = SETTINGS.autoscale_model_path
    meta_path = SETTINGS.autoscale_meta_path
    if not model_path.exists() or not meta_path.exists():
        MODEL_READY = False
        raise RuntimeError(
            f"autoscale model unavailable: model={model_path} meta={meta_path}"
        )

    try:
        MODEL = joblib.load(model_path)
        META = json.loads(meta_path.read_text())
        FEATURE_ORDER = _metadata_features(META, AUTOSCALE_FEATURES)
        if FEATURE_ORDER != list(AUTOSCALE_FEATURES):
            raise RuntimeError(
                f"autoscale feature order mismatch: got {FEATURE_ORDER}, expected {AUTOSCALE_FEATURES}"
            )
        MODEL_READY = True
        logger.info("Loaded autoscale model: %s", model_path)
        logger.info("Autoscale features=%s threshold=%.2f", FEATURE_ORDER, SETTINGS.autoscale_threshold)
    except Exception:
        MODEL_READY = False
        logger.exception("Failed to load autoscale model from %s", model_path)
        raise

    restart_model_path = SETTINGS.restart_model_path
    restart_meta_path = SETTINGS.restart_meta_path
    if not restart_model_path.exists() or not restart_meta_path.exists():
        logger.warning("restart model unavailable; skipping restart inference")
        return

    try:
        restart_meta = json.loads(restart_meta_path.read_text())
        restart_features = _metadata_features(restart_meta, RESTART_FEATURES)
        if restart_features != list(RESTART_FEATURES):
            logger.warning(
                "Ignoring restart model %s because its feature order is %s, expected %s.",
                restart_model_path,
                restart_features,
                RESTART_FEATURES,
            )
            return

        RESTART_MODEL = joblib.load(restart_model_path)
        RESTART_META = restart_meta
        RESTART_FEATURE_ORDER = restart_features
        RESTART_MODEL_READY = True
        logger.info("Loaded restart model: %s", restart_model_path)
        logger.info("Restart features=%s threshold=%.2f", RESTART_FEATURE_ORDER, SETTINGS.restart_threshold)
    except Exception:
        RESTART_MODEL_READY = False
        logger.exception("Failed to load restart model from %s", restart_model_path)


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "autoscale_model_ready": MODEL_READY,
        "restart_model_ready": RESTART_MODEL_READY,
        "action_mode": SETTINGS.action_mode,
        "target": {"namespace": SETTINGS.target_namespace, "workload": SETTINGS.target_workload},
    }


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _normalize_workload(raw_workload: Optional[str]) -> str:
    if not raw_workload:
        return SETTINGS.target_workload
    if raw_workload.startswith(f"{SETTINGS.target_workload}-"):
        return SETTINGS.target_workload
    return raw_workload


def extract_target(payload: Dict[str, Any]) -> Dict[str, Any]:
    alerts = payload.get("alerts", [])
    first_alert = alerts[0] if isinstance(alerts, list) and alerts else {}
    labels = first_alert.get("labels", {}) if isinstance(first_alert, dict) else {}

    namespace = labels.get("namespace") or SETTINGS.target_namespace
    workload = _normalize_workload(
        labels.get("deployment")
        or labels.get("workload")
        or labels.get("app")
        or labels.get("service")
        or labels.get("job")
        or SETTINGS.target_workload
    )

    pod_name = labels.get("pod")
    if pod_name and pod_name.startswith(f"{SETTINGS.target_workload}-"):
        workload = SETTINGS.target_workload

    return {
        "namespace": namespace,
        "workload": workload,
        "pod": pod_name,
        "alertname": labels.get("alertname"),
        "severity": labels.get("severity"),
        "status": (payload.get("status") or first_alert.get("status") or "firing"),
        "receiver": payload.get("receiver"),
    }


def target_in_scope(target: Dict[str, Any]) -> bool:
    return target["namespace"] in SETTINGS.allowed_namespaces and target["workload"] in SETTINGS.allowed_workloads


def prom_query_value(query: str) -> Tuple[Optional[float], bool]:
    url = f"{SETTINGS.prom_base_url}/api/v1/query"
    with PROM_QUERY_SECONDS.time():
        response = requests.get(url, params={"query": query}, timeout=SETTINGS.prom_timeout)
    response.raise_for_status()
    payload = response.json()
    result = payload.get("data", {}).get("result", [])
    if not result:
        return None, False
    value = result[0].get("value", [None, None])[1]
    if value is None:
        return None, False
    return float(value), True


def _query_signal(
    *,
    name: str,
    candidates: Iterable[str],
    required: bool,
    default: Optional[float] = None,
) -> Tuple[Optional[float], List[str], List[str]]:
    missing = []
    errors = []
    for query in candidates:
        try:
            value, present = prom_query_value(query)
        except Exception as exc:  # pragma: no cover - exercised via integration tests
            errors.append(f"{name}:{exc}")
            continue
        if present:
            return value, [], errors
        missing.append(name)
    if required:
        return None, missing or [name], errors
    return default, [], errors


def fetch_signal_bundle(target: Dict[str, Any]) -> Tuple[Dict[str, float], RestartContext]:
    pod_regex = SETTINGS.target_pod_regex
    namespace = target["namespace"]
    workload = target["workload"]
    prom_window = SETTINGS.prom_window
    restart_window = SETTINGS.prom_restart_window

    required_missing: List[str] = []
    query_errors: List[str] = []

    rps, missing, errors = _query_signal(
        name="rps",
        candidates=[f"sum(rate(loadgen_requests_total[{prom_window}]))"],
        required=True,
    )
    required_missing.extend(missing)
    query_errors.extend(errors)

    p95, missing, errors = _query_signal(
        name="p95",
        candidates=[
            f"histogram_quantile(0.95, sum(rate(loadgen_request_latency_seconds_bucket[{prom_window}])) by (le))"
        ],
        required=True,
    )
    required_missing.extend(missing)
    query_errors.extend(errors)

    http_5xx_rate, _, errors = _query_signal(
        name="http_5xx_rate",
        candidates=[
            f'sum(rate(http_requests_total{{code=~"5.."}}[{prom_window}]))',
            f'sum(rate(loadgen_requests_total{{status=~"5..|ERR"}}[{prom_window}]))',
        ],
        required=False,
        default=0.0,
    )
    query_errors.extend(errors)

    cpu_usage, missing, errors = _query_signal(
        name="cpu_usage",
        candidates=[
            f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}",pod=~"{pod_regex}",container!="POD"}}[{prom_window}]))'
        ],
        required=True,
    )
    required_missing.extend(missing)
    query_errors.extend(errors)

    cpu_limit, _, errors = _query_signal(
        name="cpu_limit",
        candidates=[
            f'sum(kube_pod_container_resource_limits{{namespace="{namespace}",pod=~"{pod_regex}",resource="cpu"}})',
            f'sum(kube_pod_container_resource_limits{{namespace="{namespace}",pod=~"{pod_regex}",resource="cpu",unit="core"}})',
        ],
        required=False,
        default=SETTINGS.cpu_limit_fallback,
    )
    query_errors.extend(errors)

    restart_evidence, _, errors = _query_signal(
        name="restart_evidence",
        candidates=[
            f'sum(increase(kube_pod_container_status_restarts_total{{namespace="{namespace}",pod=~"{pod_regex}"}}[{restart_window}]))'
        ],
        required=False,
        default=0.0,
    )
    query_errors.extend(errors)

    available_replicas, _, errors = _query_signal(
        name="available_replicas",
        candidates=[
            f'kube_deployment_status_replicas_available{{namespace="{namespace}",deployment="{workload}"}}'
        ],
        required=False,
        default=0.0,
    )
    query_errors.extend(errors)

    unavailable_replicas, _, errors = _query_signal(
        name="unavailable_replicas",
        candidates=[
            f'kube_deployment_status_replicas_unavailable{{namespace="{namespace}",deployment="{workload}"}}'
        ],
        required=False,
        default=0.0,
    )
    query_errors.extend(errors)

    desired_replicas, _, errors = _query_signal(
        name="desired_replicas",
        candidates=[
            f'kube_deployment_spec_replicas{{namespace="{namespace}",deployment="{workload}"}}'
        ],
        required=False,
        default=1.0,
    )
    query_errors.extend(errors)

    features = {
        "rps": float(rps or 0.0),
        "p95": float(p95 or 0.0),
        "http_5xx_rate": float(http_5xx_rate or 0.0),
        "cpu_sat": compute_cpu_saturation(cpu_usage, cpu_limit, SETTINGS.cpu_limit_fallback),
    }
    context = RestartContext(
        restart_evidence=float(restart_evidence or 0.0),
        available_replicas=float(available_replicas or 0.0),
        unavailable_replicas=float(unavailable_replicas or 0.0),
        desired_replicas=float(desired_replicas or 0.0),
        missing_metrics=required_missing,
        query_errors=query_errors,
    )
    return features, context


def autoscale_probability(features: Dict[str, float]) -> Optional[float]:
    if not MODEL_READY or MODEL is None:
        return None
    vector = build_autoscale_vector(features, FEATURE_ORDER)
    proba = MODEL.predict_proba([vector])[0]
    return float(proba[1])


def _positive_class_probability(
    *,
    model: Any,
    meta: Dict[str, Any],
    vector: List[float],
    positive_label: str,
    fallback_positive_index: int,
) -> float:
    proba = model.predict_proba([vector])[0]
    labels = meta.get("label_classes") or meta.get("classes")
    if labels and positive_label in labels:
        index = list(labels).index(positive_label)
    elif hasattr(model, "classes_") and positive_label in list(model.classes_):
        index = list(model.classes_).index(positive_label)
    else:
        index = fallback_positive_index

    if index >= len(proba):
        return 0.0
    return float(proba[index])


def restart_probability(features: Dict[str, float]) -> Optional[float]:
    if not RESTART_MODEL_READY or RESTART_MODEL is None:
        return None
    vector = build_feature_vector(features, RESTART_FEATURE_ORDER)
    return _positive_class_probability(
        model=RESTART_MODEL,
        meta=RESTART_META,
        vector=vector,
        positive_label="auto_restart",
        fallback_positive_index=1,
    )


def _cooldown_key(target: Dict[str, Any], decision: str) -> str:
    return f"{decision}:{target['namespace']}:{target['workload']}"


def _target_key(target: Dict[str, Any]) -> str:
    return f"{target['namespace']}/{target['workload']}"


def apply_consecutive_escalation(
    *,
    target: Dict[str, Any],
    decision_payload: Dict[str, Any],
) -> Dict[str, Any]:
    candidate_action = decision_payload["candidate_action"]

    if candidate_action not in {"auto_scale", "auto_restart"}:
        return decision_payload

    now = time.time()
    key = f"{_target_key(target)}:{candidate_action}"
    previous = CANDIDATE_STREAK.get(key, {})
    previous_at = float(previous.get("last_seen_at", 0.0))
    within_window = now - previous_at <= SETTINGS.consecutive_memory_seconds
    count = int(previous.get("count", 0)) + 1 if within_window else 1
    CANDIDATE_STREAK[key] = {
        "candidate_action": candidate_action,
        "count": count,
        "last_seen_at": now,
    }

    if count >= SETTINGS.consecutive_escalation_count:
        decision_payload["final_action"] = "notify_human"
        decision_payload["decision"] = "notify_human"
        decision_payload["reason"] = "repeated_action"
        decision_payload["escalation"] = {
            "candidate_action": candidate_action,
            "consecutive_count": count,
            "threshold": SETTINGS.consecutive_escalation_count,
            "memory_seconds": SETTINGS.consecutive_memory_seconds,
            "key": key,
        }

    return decision_payload


def apply_guardrails(
    *,
    target: Dict[str, Any],
    decision_payload: Dict[str, Any],
    restart_context: RestartContext,
) -> Dict[str, Any]:
    decision = decision_payload["final_action"]
    reason = decision_payload["reason"]

    if decision not in {"auto_scale", "auto_restart"}:
        return decision_payload

    if not target_in_scope(target):
        decision_payload["final_action"] = "notify_human"
        decision_payload["decision"] = "notify_human"
        decision_payload["reason"] = "out_of_scope"
        return decision_payload

    now = time.time()
    last_action = LAST_ACTION_AT.get(_cooldown_key(target, decision))
    if last_action is not None and now - last_action < SETTINGS.cooldown_seconds:
        decision_payload["final_action"] = "notify_human"
        decision_payload["decision"] = "notify_human"
        decision_payload["reason"] = "repeated_action"
        decision_payload["guardrail_blocked"] = {"reason": reason, "last_action_at": last_action}
        return decision_payload

    if decision == "auto_scale":
        current = int(restart_context.desired_replicas or 0)
        if current <= 0:
            decision_payload["final_action"] = "notify_human"
            decision_payload["decision"] = "notify_human"
            decision_payload["reason"] = "action_failed"
            decision_payload["guardrail_blocked"] = {"reason": "missing_current_replicas"}
            return decision_payload
        if current >= SETTINGS.max_replicas:
            decision_payload["final_action"] = "notify_human"
            decision_payload["decision"] = "notify_human"
            decision_payload["reason"] = "action_failed"
            decision_payload["guardrail_blocked"] = {"current_replicas": current, "max_replicas": SETTINGS.max_replicas}
            return decision_payload

    return decision_payload


def record_action_metrics(action_name: str, action_result: Dict[str, Any]) -> None:
    if action_name not in {"auto_scale", "auto_restart", "notify_human"}:
        return
    status = action_result.get("status", "unknown")
    ACTIONS.labels(action=action_name, status=status).inc()
    ACTION_DURATION_SECONDS.labels(action=action_name).observe(float(action_result.get("duration_seconds", 0.0)))
    if status == "failed":
        ACTION_FAILURES.labels(action=action_name).inc()
    if action_name == "notify_human":
        NOTIFY_HUMAN.inc()


@app.post("/alert")
async def alert_receiver(req: Request) -> Dict[str, Any]:
    ALERTS_RECEIVED.inc()

    try:
        payload = await req.json()
    except Exception:
        raw = await req.body()
        logger.warning("Received non-JSON alert body: %s", raw)
        DECISIONS.labels(decision="notify_human").inc()
        NOTIFY_HUMAN.inc()
        return {
            "status": "accepted",
            "candidate_action": "notify_human",
            "final_action": "notify_human",
            "decision": "notify_human",
            "reason": "missing_or_stale_metrics",
        }

    target = extract_target(payload)
    now = time.time()

    if not target_in_scope(target):
        decision_result = {
            "candidate_action": "no_action",
            "final_action": "no_action",
            "decision": "no_action",
            "reason": "out_of_scope",
            "p_autoscale": None,
            "p_restart": None,
            "signals": {"feature_order": list(AUTOSCALE_FEATURES), "alert_status": target["status"]},
        }
        audit = {
            "ts": now,
            "target": target,
            **decision_result,
            "features": None,
            "restart_context": None,
            "action_result": {"status": "skipped"},
        }
        DECISIONS.labels(decision="no_action").inc()
        logger.info("AUDIT %s", json.dumps(audit, ensure_ascii=False))
        return {"status": "accepted", "target": target, **decision_result}

    try:
        features, restart_context = fetch_signal_bundle(target)
        p_autoscale = autoscale_probability(features)
        p_restart = None
        if p_autoscale is not None and p_autoscale < SETTINGS.autoscale_threshold and RESTART_MODEL_READY:
            p_restart = restart_probability(features)
        if p_restart is not None:
            result_label = "above_threshold" if p_restart >= SETTINGS.restart_threshold else "below_threshold"
            RESTART_MODEL_PREDICTIONS.labels(result=result_label).inc()

        decision_result = decide_action(
            features=features,
            context=restart_context,
            p_autoscale=p_autoscale,
            p_restart=p_restart,
            autoscale_threshold=SETTINGS.autoscale_threshold,
            restart_threshold=SETTINGS.restart_threshold,
            alert_status=target["status"],
            autoscale_model_ready=MODEL_READY,
            restart_model_ready=RESTART_MODEL_READY,
        ).to_dict()

        decision_result = apply_consecutive_escalation(
            target=target,
            decision_payload=decision_result,
        )

        decision_result = apply_guardrails(
            target=target,
            decision_payload=decision_result,
            restart_context=restart_context,
        )

        action_target = ActionTarget(
            namespace=target["namespace"],
            workload=target["workload"],
            current_replicas=int(restart_context.desired_replicas or 0),
        )
        action_result = ACTION_EXECUTOR.execute(
            decision=decision_result["final_action"],
            target=action_target,
            max_replicas=SETTINGS.max_replicas,
        )

        action_metric_name = action_result.get("action", decision_result["final_action"])
        if decision_result["final_action"] in {"auto_scale", "auto_restart"} and action_result["status"] in {"success", "simulated"}:
            LAST_ACTION_AT[_cooldown_key(target, decision_result["final_action"])] = now
        elif decision_result["final_action"] in {"auto_scale", "auto_restart"} and action_result["status"] == "failed":
            decision_result["failed_action_result"] = action_result
            decision_result["final_action"] = "notify_human"
            decision_result["decision"] = "notify_human"
            decision_result["reason"] = "action_failed"

        DECISIONS.labels(decision=decision_result["decision"]).inc()
        record_action_metrics(action_metric_name, action_result)
        if decision_result["decision"] == "notify_human" and action_metric_name != "notify_human":
            NOTIFY_HUMAN.inc()

        audit = {
            "ts": now,
            "target": target,
            "features": features,
            "restart_context": restart_context.to_dict(),
            "candidate_action": decision_result["candidate_action"],
            "final_action": decision_result["final_action"],
            "decision": decision_result["decision"],
            "reason": decision_result["reason"],
            "p_autoscale": decision_result["p_autoscale"],
            "p_restart": decision_result["p_restart"],
            "signals": decision_result["signals"],
            "action_result": action_result,
            "alerts_count": len(payload.get("alerts", [])) if isinstance(payload.get("alerts"), list) else None,
        }
        if "guardrail_blocked" in decision_result:
            audit["guardrail_blocked"] = decision_result["guardrail_blocked"]
        if "escalation" in decision_result:
            audit["escalation"] = decision_result["escalation"]
        if "failed_action_result" in decision_result:
            audit["failed_action_result"] = decision_result["failed_action_result"]

        logger.info("AUDIT %s", json.dumps(audit, ensure_ascii=False))

        return {
            "status": "accepted",
            "target": target,
            "features": features,
            "restart_context": restart_context.to_dict(),
            **decision_result,
            "action_result": action_result,
        }
    except Exception as exc:  # pragma: no cover - covered by manual verification path
        logger.exception("Failed to process alert: %s", exc)
        DECISIONS.labels(decision="notify_human").inc()
        NOTIFY_HUMAN.inc()
        return {
            "status": "accepted",
            "candidate_action": "notify_human",
            "final_action": "notify_human",
            "decision": "notify_human",
            "reason": "action_failed",
            "error": str(exc),
            "target": target,
        }
