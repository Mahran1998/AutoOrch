from fastapi import FastAPI, Request
from pydantic import BaseModel
import logging, json, sys

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("autoorch")

app = FastAPI(title="AutoOrch Webhook")

class Alert(BaseModel):
    # keep generic: Alertmanager payload varies; accept arbitrary dict
    receiver: str = None
    status: str = None

@app.get("/health")
async def health():
    """Kubernetes health endpoint"""
    return {"status": "ok"}

@app.post("/alert")
async def alert_receiver(req: Request):
    """Receive alertmanager or test payloads and log them."""
    try:
        payload = await req.json()
    except Exception:
        text = await req.body()
        logger.warning("Received non-json alert body: %s", text)
        return {"status":"accepted","note":"non-json"}

    # basic logging + store minimal info
    logger.info("Received alert payload: %s", json.dumps(payload, ensure_ascii=False))
    # TODO: extract features, call classifier, decide action, run ansible playbooks
    return {"status":"accepted"}
