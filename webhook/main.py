from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
import logging, json, sys, os, time
from pathlib import Path
from typing import Dict, Any, Optional, List

import joblib
import requests
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST


logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("autoorch")

app = FastAPI(title="AutoOrch Webhook")

# --- Prometheus metrics for AutoOrch itself ---
DECISIONS = Counter(
    "autoorch_decisions_total",
    "Total decisions made by AutoOrch",
    ["decision"],
)
PROM_QUERY_SECONDS = Histogram(
    "autoorch_prometheus_query_seconds",
    "Time spent querying Prometheus",
)

# --- Model globals (loaded once) ---
MODEL = None
META: Dict[str, Any] = {}
FEATURES: List[str] = []
THRESHOLD: float = 0.90

# --- Prometheus config ---
# In-cluster you will use a service DNS (e.g. http://prometheus-stack-kube-prom-prometheus.monitoring:9090)
# For local testing you can set PROM_BASE_URL=http://127.0.0.1:9090 with port-forward
PROM_BASE_URL = os.getenv("PROM_BASE_URL", "http://127.0.0.1:9090")
PROM_WINDOW = os.getenv("PROM_WINDOW", "60s")  # used in queries
PROM_TIMEOUT = float(os.getenv("PROM_TIMEOUT", "5"))

# Target config (keep simple for now: demo-backend only)
TARGET_POD_REGEX = os.getenv("TARGET_POD_REGEX", "demo-backend-.*")


class Alert(BaseModel):
    receiver: Optional[str] = None
    status: Optional[str] = None


@app.on_event("startup")
def load_model() -> None:
    global MODEL, META, FEATURES, THRESHOLD
    model_path = Path("models/autoscale_classifier.joblib")
    meta_path = Path("models/autoscale_classifier_meta.json")

    if not model_path.exists() or not meta_path.exists():
        logger.warning("Model files not found. Expect inference to fail until models/ is mounted.")
        return

    MODEL = joblib.load(model_path)
    META = json.loads(meta_path.read_text())
    FEATURES = META.get("features", ["rps", "p95", "http_5xx_rate", "cpu_sat"])
    THRESHOLD = float(META.get("threshold", 0.90))

    logger.info("Loaded model: %s", str(model_path))
    logger.info("Loaded meta: features=%s threshold=%.2f", FEATURES, THRESHOLD)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    data = generate_latest()
    # Correct usage: Response(...)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


def prom_query(query: str) -> float:
    """
    Instant query via Prometheus HTTP API.
    Returns float value if present, else 0.0.
    """
    url = f"{PROM_BASE_URL}/api/v1/query"
    with PROM_QUERY_SECONDS.time():
        r = requests.get(url, params={"query": query}, timeout=PROM_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    result = data.get("data", {}).get("result", [])
    if not result:
        return 0.0
    # result is a list of time series; use first for now
    value = result[0].get("value", [None, "0"])[1]
    try:
        return float(value)
    except Exception:
        return 0.0


def fetch_features() -> Dict[str, float]:
    """
    Compute the features over a recent window (PROM_WINDOW).
    NOTE: Metric names must match your environment.
    """
    # Loadgen metrics (you used these in dataset build)
    q_rps = f'rate(loadgen_requests_total[{PROM_WINDOW}])'
    q_p95 = (
        f'histogram_quantile(0.95, sum(rate(loadgen_request_latency_seconds_bucket[{PROM_WINDOW}])) by (le))'
    )

    # 5xx may be missing (often 0 in your dataset) — return 0.0 when absent
    q_5xx = f'sum(rate(http_requests_total{{code=~"5.."}}[{PROM_WINDOW}]))'

    # CPU saturation: usage / limit
    # usage in cores: sum(rate(container_cpu_usage_seconds_total[...] )) by pod regex
    q_cpu_usage = (
        f'sum(rate(container_cpu_usage_seconds_total{{pod=~"{TARGET_POD_REGEX}",container!="POD"}}[{PROM_WINDOW}]))'
    )
    # limit in cores (kube-state-metrics); may be missing in some setups -> fallback handled below
    q_cpu_limit = (
        f'sum(kube_pod_container_resource_limits{{pod=~"{TARGET_POD_REGEX}",resource="cpu"}})'
    )

    rps = prom_query(q_rps)
    p95 = prom_query(q_p95)
    http_5xx_rate = prom_query(q_5xx)
    cpu_usage = prom_query(q_cpu_usage)
    cpu_limit = prom_query(q_cpu_limit)

    # If kube_pod_container_resource_limits is missing, fallback to 0.3 cores (300m) as your configured limit
    if cpu_limit <= 0.0:
        cpu_limit = float(os.getenv("CPU_LIMIT_FALLBACK", "0.3"))

    cpu_sat = cpu_usage / cpu_limit if cpu_limit > 0 else 0.0

    return {
        "rps": rps,
        "p95": p95,
        "http_5xx_rate": http_5xx_rate,
        "cpu_sat": cpu_sat,
    }


def decide_autoscale(features: Dict[str, float]) -> Dict[str, Any]:
    """
    Inference-only decision for autoscale vs no_action.
    """
    if MODEL is None:
        raise RuntimeError("MODEL is not loaded")

    x = [[features[name] for name in FEATURES]]
    proba = MODEL.predict_proba(x)[0]
    p_autoscale = float(proba[1])

    decision = "auto_scale" if p_autoscale >= THRESHOLD else "no_action"
    return {"decision": decision, "p_autoscale": p_autoscale}


@app.post("/alert")
async def alert_receiver(req: Request):
    """
    Receive Alertmanager payloads, compute features, run inference, log decision.
    """
    try:
        payload = await req.json()
    except Exception:
        text = await req.body()
        logger.warning("Received non-json alert body: %s", text)
        return {"status": "accepted", "note": "non-json"}

    # Fetch features and decide
    now = time.time()
    try:
        feats = fetch_features()
        result = decide_autoscale(feats)
        DECISIONS.labels(decision=result["decision"]).inc()

        audit = {
            "ts": now,
            "decision": result["decision"],
            "p_autoscale": result["p_autoscale"],
            "features": feats,
            "alert_receiver": payload.get("receiver"),
            "alert_status": payload.get("status"),
            "alerts_count": len(payload.get("alerts", [])) if isinstance(payload.get("alerts"), list) else None,
        }
        logger.info("AUDIT %s", json.dumps(audit, ensure_ascii=False))

        return {"status": "accepted", **result, "features": feats}
    except Exception as e:
        logger.exception("Failed to process alert: %s", str(e))
        DECISIONS.labels(decision="error").inc()
        return {"status": "accepted", "note": "error", "error": str(e)}
