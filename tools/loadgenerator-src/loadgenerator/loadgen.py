#!/usr/bin/env python3
"""
Async load generator that:
- issues requests to TARGET at approx RPS
- exposes Prometheus metrics on /metrics (METRICS_PORT)
- supports concurrency and optional duration

Env:
  TARGET (default http://frontend:80/)
  RPS (requests per second, default 50)
  CONCURRENCY (async tasks, default 25)
  METRICS_PORT (default 8080)
  DURATION_SECONDS (0 = run forever)
"""

import os
import asyncio
import aiohttp
import time
from prometheus_client import start_http_server, Counter, Histogram, Gauge

TARGET = os.getenv("TARGET", "http://frontend:80/")
RPS = float(os.getenv("RPS", "50"))
CONCURRENCY = int(os.getenv("CONCURRENCY", "25"))
METRICS_PORT = int(os.getenv("METRICS_PORT", "8080"))
DURATION = int(os.getenv("DURATION_SECONDS", "0"))

# Prometheus metrics
REQ_COUNT = Counter("loadgen_requests_total", "Total requests issued", ["method", "status"])
REQ_LATENCY = Histogram("loadgen_request_latency_seconds", "Request latency seconds", buckets=(0.005,0.01,0.025,0.05,0.1,0.25,0.5,1,2,5))
IN_FLIGHT = Gauge("loadgen_in_flight", "In-flight requests")

# Adaptive scheduling: interval per request per concurrency
# We'll distribute the RPS across concurrency workers: each worker will attempt requests at rate RPS / CONCURRENCY
async def worker(session, worker_id, rate_per_worker, stop_event):
    interval = 1.0 / max(rate_per_worker, 0.0001)
    # A small jitter to avoid lockstep
    jitter = (worker_id % 5) * 0.001
    await asyncio.sleep(jitter)
    while not stop_event.is_set():
        start = time.monotonic()
        IN_FLIGHT.inc()
        try:
            async with session.get(TARGET, timeout=10) as resp:
                status = resp.status
                # read some bytes to complete the request
                await resp.read()
                elapsed = time.monotonic() - start
                REQ_COUNT.labels(method="GET", status=str(status)).inc()
                REQ_LATENCY.observe(elapsed)
        except Exception:
            elapsed = time.monotonic() - start
            REQ_COUNT.labels(method="GET", status="ERR").inc()
            REQ_LATENCY.observe(elapsed)
        finally:
            IN_FLIGHT.dec()
        # wait until next tick
        elapsed = time.monotonic() - start
        to_wait = interval - elapsed
        if to_wait > 0:
            await asyncio.sleep(to_wait)

async def main():
    stop_event = asyncio.Event()
    # start prometheus metrics server
    start_http_server(METRICS_PORT)
    # calculate per-worker rate
    if CONCURRENCY <= 0:
        print("CONCURRENCY must be > 0")
        return
    rate_per_worker = RPS / CONCURRENCY
    # Setup aiohttp session with TCPConnector tuned for concurrency
    conn = aiohttp.TCPConnector(limit=CONCURRENCY*2)
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        tasks = [asyncio.create_task(worker(session, i, rate_per_worker, stop_event)) for i in range(CONCURRENCY)]
        if DURATION > 0:
            # stop after duration
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=DURATION)
            except asyncio.TimeoutError:
                stop_event.set()
        else:
            # run forever
            await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
