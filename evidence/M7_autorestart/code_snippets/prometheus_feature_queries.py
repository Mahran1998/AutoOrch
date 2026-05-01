def fetch_signal_bundle(target):
    rps = 'sum(rate(http_requests_total{exported_endpoint="/api/test"}[1m]))'
    p95 = "histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[1m])) by (le))"
    http_5xx_rate = 'sum(rate(http_requests_total{exported_endpoint="/api/test",status=~"5.."}[1m]))'
    cpu_usage = (
        'sum(rate(container_cpu_usage_seconds_total{namespace="default",'
        'pod=~"controllable-backend-.*",container!="POD"}[1m]))'
    )

    features = {
        "rps": rps,
        "p95": p95,
        "http_5xx_rate": http_5xx_rate,
        "cpu_sat": f"({cpu_usage}) / cpu_limit",
    }
    return features
