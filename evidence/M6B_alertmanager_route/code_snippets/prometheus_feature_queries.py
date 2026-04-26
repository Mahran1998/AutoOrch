def fetch_signal_bundle(target):
    prom_window = SETTINGS.prom_window
    namespace = target["namespace"]
    pod_regex = SETTINGS.target_pod_regex

    rps = query_first_present([
        f'sum(rate(http_requests_total{{exported_endpoint="/api/test"}}[{prom_window}]))',
        f'sum(rate(http_requests_total{{endpoint="/api/test"}}[{prom_window}]))',
    ])

    p95 = query_first_present([
        f"histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[{prom_window}])) by (le))",
    ])

    http_5xx_rate = query_first_present([
        f'sum(rate(http_requests_total{{exported_endpoint="/api/test",status=~"5.."}}[{prom_window}]))',
        f'sum(rate(http_requests_total{{endpoint="/api/test",status=~"5.."}}[{prom_window}]))',
    ], default=0.0)

    cpu_usage = query_first_present([
        f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}",pod=~"{pod_regex}",container!="POD"}}[{prom_window}]))',
    ])

    cpu_limit = query_first_present([
        f'sum(kube_pod_container_resource_limits{{namespace="{namespace}",pod=~"{pod_regex}",resource="cpu"}})',
    ], default=SETTINGS.cpu_limit_fallback)

    return {
        "rps": rps,
        "p95": p95,
        "http_5xx_rate": http_5xx_rate,
        "cpu_sat": cpu_usage / cpu_limit,
    }
