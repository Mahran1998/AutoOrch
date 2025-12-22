#!/usr/bin/env python3
"""
run_schedule.py

Run a schedule (ramp, spike, diurnal) by updating loadgen via kubectl-run curl pods.
Writes results into --result-dir/csv/schedule.csv with columns:
ts,pattern,req_rps,req_concurrency,observed_rps,p95

Usage examples:
  python3 run_schedule.py --pattern ramp --start 10 --end 200 --steps 10 --step-duration 60 --result-dir /path/to/dir
  python3 run_schedule.py --pattern spike --base 20 --spike 300 --spike-duration 60 --interval 15 --result-dir /path/to/dir
  python3 run_schedule.py --pattern diurnal --base 20 --amp 80 --period 3600 --duration 7200 --interval 15 --result-dir /path/to/dir
"""
import argparse, time, subprocess, json
from math import sin, pi
from datetime import datetime

PROM_HOST = "http://localhost:9090"
LOADGEN_SVC = "loadgenerator-metrics.default.svc.cluster.local:8080"

def kcurl_post_rps(rps, concurrency):
    # use kubectl run to perform in-cluster POST (keeps script simple & no port-forward required)
    data = json.dumps({"rps": int(rps), "concurrency": int(concurrency)})
    cmd = [
        "kubectl","run","-n","default","--rm","-it","--restart=Never","curlctrl",
        "--image=radial/busyboxplus:curl","--command","--",
        "sh","-c",
        f"curl -sS -X POST -H 'Content-Type: application/json' -d '{data}' http://{LOADGEN_SVC}/control"
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        # best-effort; ignore failures
        pass

def query_prom(prom_query):
    import requests
    try:
        r = requests.get(PROM_HOST + "/api/v1/query", params={"query": prom_query}, timeout=10)
        j = r.json()
        return j.get("data", {}).get("result", [])
    except Exception:
        return []

def instant_observed():
    res = query_prom("sum(rate(loadgen_requests_total[1m]))")
    obs = res[0]["value"][1] if res else "0"
    q = query_prom("histogram_quantile(0.95, sum(rate(loadgen_request_latency_seconds_bucket[1m])) by (le))")
    p95 = q[0]["value"][1] if q else "NaN"
    return str(obs), str(p95)

def write_row(csvfile, cols):
    csvfile.write(",".join(cols) + "\n")
    csvfile.flush()

def ramp(args, csvfile):
    start = args.start
    end = args.end
    steps = args.steps
    step_dur = args.step_duration
    concurrency = args.concurrency
    for i in range(steps+1):
        req = start + (end-start) * (i/steps)
        kcurl_post_rps(int(req), concurrency)
        obs,p95 = instant_observed()
        write_row(csvfile, [str(int(time.time())), "ramp", str(int(req)), str(concurrency), obs, p95])
        print(f"[{datetime.now().isoformat()}] ramp step {i}/{steps} req={int(req)} obs={obs} p95={p95}")
        time.sleep(step_dur)

def spike(args, csvfile):
    base = args.base
    spike = args.spike
    spike_dur = args.spike_duration
    interval = args.interval
    concurrency = args.concurrency
    # baseline
    kcurl_post_rps(int(base), concurrency)
    obs,p95 = instant_observed()
    write_row(csvfile, [str(int(time.time())), "spike_base", str(int(base)), str(concurrency), obs, p95])
    print("baseline set:", base)
    # spike
    kcurl_post_rps(int(spike), concurrency)
    t0 = time.time()
    while time.time() - t0 < spike_dur:
        obs,p95 = instant_observed()
        write_row(csvfile, [str(int(time.time())), "spike", str(int(spike)), str(concurrency), obs, p95])
        time.sleep(interval)
    # return to base
    kcurl_post_rps(int(base), concurrency)
    obs,p95 = instant_observed()
    write_row(csvfile, [str(int(time.time())), "spike_end", str(int(base)), str(concurrency), obs, p95])

def diurnal(args, csvfile):
    base = args.base
    amp = args.amp
    period = args.period
    duration = args.duration
    interval = args.interval
    concurrency = args.concurrency
    t0 = time.time()
    while time.time() - t0 < duration:
        t = time.time() - t0
        # sinusoidal flow: base + amp * 0.5*(1+sin(...))
        req = base + amp * 0.5 * (1 + sin(2 * pi * (t / period)))
        kcurl_post_rps(int(req), concurrency)
        obs,p95 = instant_observed()
        write_row(csvfile, [str(int(time.time())), "diurnal", str(int(req)), str(concurrency), obs, p95])
        print(f"diurnal req={int(req)} obs={obs} p95={p95}")
        time.sleep(interval)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern", required=True, choices=["ramp","spike","diurnal"])
    parser.add_argument("--result-dir", required=True)
    # common
    parser.add_argument("--concurrency", type=int, default=25)
    # ramp args
    parser.add_argument("--start", type=int, default=10)
    parser.add_argument("--end", type=int, default=200)
    parser.add_argument("--steps", type=int, default=10)
    parser.add_argument("--step-duration", type=int, default=60)
    # spike args
    parser.add_argument("--base", type=int, default=20)
    parser.add_argument("--spike", type=int, default=300)
    parser.add_argument("--spike-duration", type=int, default=60)
    parser.add_argument("--interval", type=int, default=15)
    # diurnal
    parser.add_argument("--amp", type=int, default=80)
    parser.add_argument("--period", type=int, default=3600)
    parser.add_argument("--duration", type=int, default=7200)
    args = parser.parse_args()

    import os
    os.makedirs(os.path.join(args.result_dir, "csv"), exist_ok=True)
    csvf = open(os.path.join(args.result_dir, "csv", "schedule.csv"), "a", buffering=1)
    if csvf.tell() == 0:
        csvf.write("ts,pattern,req_rps,req_concurrency,observed_rps,p95_latency_seconds\n")

    if args.pattern == "ramp":
        ramp(args, csvf)
    elif args.pattern == "spike":
        spike(args, csvf)
    elif args.pattern == "diurnal":
        diurnal(args, csvf)

if __name__ == "__main__":
    main()
