#!/usr/bin/env python3
"""
Control-able async load generator:

- Exposes /metrics for Prometheus
- Exposes /control (POST) to change RPS and concurrency at runtime
- Exposes /health for readiness/liveness checks
- Workers adjust to new settings by restarting

Env:
  TARGET (default http://frontend:80/)
  RPS (default 50)
  CONCURRENCY (default 25)
  METRICS_PORT (default 8080)
  DURATION_SECONDS (0 = run forever)
"""
import os
import asyncio
import time
import logging
import aiohttp
from aiohttp import web
from prometheus_client import CollectorRegistry, Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

logging.basicConfig(level=logging.INFO)

# Config from env
TARGET = os.getenv("TARGET", "http://frontend:80/")
METRICS_PORT = int(os.getenv("METRICS_PORT", "8080"))
DURATION = int(os.getenv("DURATION_SECONDS", "0"))

# Shared mutable state protected by lock
_state = {
    "rps": float(os.getenv("RPS", "50")),
    "concurrency": int(os.getenv("CONCURRENCY", "25"))
}
_state_lock = asyncio.Lock()

# Prometheus registry and metrics
REG = CollectorRegistry()
REQ_COUNT = Counter("loadgen_requests_total", "Total requests issued", ["method", "status"], registry=REG)
REQ_LATENCY = Histogram(
    "loadgen_request_latency_seconds",
    "Request latency seconds",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
    registry=REG,
)
IN_FLIGHT = Gauge("loadgen_in_flight", "In-flight requests", registry=REG)

# Worker control
_worker_tasks = []
_worker_stop = None
_worker_session = None

async def worker(session, wid, stop_event, rate_per_worker):
    interval = 1.0 / max(rate_per_worker, 1e-6)
    jitter = (wid % 5) * 0.001
    await asyncio.sleep(jitter)
    while not stop_event.is_set():
        start = time.monotonic()
        IN_FLIGHT.inc()
        try:
            async with session.get(TARGET, timeout=10) as resp:
                await resp.read()  # consume body
                REQ_COUNT.labels(method="GET", status=str(resp.status)).inc()
                REQ_LATENCY.observe(time.monotonic() - start)
        except Exception:
            REQ_COUNT.labels(method="GET", status="ERR").inc()
            REQ_LATENCY.observe(time.monotonic() - start)
        finally:
            IN_FLIGHT.dec()
        elapsed = time.monotonic() - start
        to_wait = interval - elapsed
        if to_wait > 0:
            await asyncio.sleep(to_wait)

async def start_workers():
    global _worker_tasks, _worker_stop, _worker_session
    async with _state_lock:
        rps = float(_state["rps"])
        concurrency = max(1, int(_state["concurrency"]))
    rate_per_worker = rps / concurrency
    logging.info("Starting %d workers for %.2f RPS (%.4f per worker)", concurrency, rps, rate_per_worker)
    conn = aiohttp.TCPConnector(limit=concurrency * 2)
    timeout = aiohttp.ClientTimeout(total=15)
    # create a shared session
    _worker_session = aiohttp.ClientSession(connector=conn, timeout=timeout)
    _worker_stop = asyncio.Event()
    _worker_tasks = [asyncio.create_task(worker(_worker_session, i, _worker_stop, rate_per_worker)) for i in range(concurrency)]

async def stop_workers():
    global _worker_tasks, _worker_stop, _worker_session
    if _worker_stop:
        _worker_stop.set()
    tasks = _worker_tasks
    _worker_tasks = []
    _worker_stop = None
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    if _worker_session:
        try:
            await _worker_session.close()
        except Exception:
            pass
        _worker_session = None

async def restart_workers():
    await stop_workers()
    await start_workers()

# HTTP handlers
async def metrics_handler(request):
    data = generate_latest(REG)
    return web.Response(body=data, content_type=CONTENT_TYPE_LATEST)

async def control_handler(request):
    try:
        payload = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid json"}, status=400)
    changed = False
    async with _state_lock:
        if "rps" in payload:
            _state["rps"] = float(payload["rps"])
            changed = True
        if "concurrency" in payload:
            _state["concurrency"] = int(payload["concurrency"])
            changed = True
    if changed:
        # restart workers in background so the HTTP request returns fast
        asyncio.create_task(restart_workers())
    return web.json_response({"ok": True, "state": _state})

async def health(request):
    return web.Response(text="ok")

async def main():
    # start worker pool
    await start_workers()
    # aiohttp app for metrics + control + health on same port
    app = web.Application()
    app.add_routes([
        web.get('/metrics', metrics_handler),
        web.post('/control', control_handler),
        web.get('/health', health),
    ])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', METRICS_PORT)
    await site.start()
    logging.info("Loadgen running: TARGET=%s METRICS_PORT=%d", TARGET, METRICS_PORT)
    if DURATION > 0:
        logging.info("DURATION_SECONDS=%d: run will stop after duration", DURATION)
        await asyncio.sleep(DURATION)
        logging.info("Duration elapsed, shutting down")
        await stop_workers()
        return
    # run forever
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
