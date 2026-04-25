#!/usr/bin/env python3
"""
Controllable Flask backend for AutoOrch ML training.

Features:
- /api/test: Returns 200 by default, 500 if error injection enabled
- /inject-errors: Toggle error injection on/off (POST)
- /inject-latency?ms=N: Set latency injection (POST)
- /metrics: Prometheus metrics with per-status tracking
- /health: Health check endpoint

Metrics exported:
- http_requests_total[method, endpoint, status]: Request counts by status
- error_injection_enabled: Current injection state (0 or 1)
- latency_injection_enabled: Latency injection in milliseconds (0 = disabled)
- http_request_latency_seconds: Request latency histogram
- pod_uptime_seconds: Time since pod startup
"""

from flask import Flask, jsonify
from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, generate_latest
import threading
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Prometheus registry and metrics
registry = CollectorRegistry()

request_counter = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

error_injection_gauge = Gauge(
    'error_injection_enabled',
    'Error injection toggle (1=enabled, 0=disabled)',
    registry=registry
)

latency_injection_gauge = Gauge(
    'latency_injection_enabled',
    'Latency injection in milliseconds (0=disabled)',
    registry=registry
)

request_latency = Histogram(
    'http_request_latency_seconds',
    'HTTP request latency in seconds',
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
    registry=registry
)

pod_uptime = Gauge(
    'pod_uptime_seconds',
    'Seconds since pod started',
    registry=registry
)

# Shared state
_inject_errors = False
_inject_latency_ms = 0  # 0 means no latency injection
_state_lock = threading.Lock()
_start_time = time.time()

# Background task to update uptime
def update_uptime():
    while True:
        elapsed = time.time() - _start_time
        pod_uptime.set(elapsed)
        time.sleep(1)

_uptime_thread = threading.Thread(target=update_uptime, daemon=True)
_uptime_thread.start()


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'service': 'controllable-backend'}), 200


@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Main test endpoint that can be made to fail or have latency injected."""
    global _inject_errors, _inject_latency_ms
    start_time = time.time()
    
    try:
        with _state_lock:
            should_fail = _inject_errors
            latency_ms = _inject_latency_ms
        
        # Apply latency injection if enabled
        if latency_ms > 0:
            time.sleep(latency_ms / 1000.0)
        
        status = 500 if should_fail else 200
        elapsed = time.time() - start_time
        
        # Record metrics
        request_counter.labels(method='GET', endpoint='/api/test', status=status).inc()
        request_latency.observe(elapsed)
        
        if status == 500:
            return jsonify({'error': 'Internal server error'}), 500
        else:
            return jsonify({'message': 'OK', 'timestamp': time.time()}), 200
    
    except Exception as e:
        logger.exception("Error in test_endpoint: %s", e)
        request_counter.labels(method='GET', endpoint='/api/test', status='500').inc()
        return jsonify({'error': str(e)}), 500


@app.route('/inject-errors', methods=['POST'])
def toggle_errors():
    """Toggle error injection on/off."""
    global _inject_errors
    
    with _state_lock:
        _inject_errors = not _inject_errors
        new_state = _inject_errors
        error_injection_gauge.set(1 if new_state else 0)
    
    logger.info("Error injection toggled: %s", "ON" if new_state else "OFF")
    return jsonify({
        'error_injection_enabled': new_state,
        'message': 'Error injection is now ' + ('enabled' if new_state else 'disabled')
    }), 200


@app.route('/inject-latency', methods=['POST'])
def set_latency():
    """Set latency injection in milliseconds. Pass ms=0 to disable.
    
    Usage:
        POST /inject-latency?ms=500  # Enable 500ms latency
        POST /inject-latency?ms=0    # Disable latency
    """
    global _inject_latency_ms
    from flask import request as flask_request
    
    try:
        ms = int(flask_request.args.get('ms', 0))
        
        if ms < 0:
            return jsonify({'error': 'ms must be >= 0'}), 400
        
        with _state_lock:
            _inject_latency_ms = ms
            latency_injection_gauge.set(ms)
        
        logger.info("Latency injection set to: %dms", ms)
        return jsonify({
            'latency_injection_enabled': ms,
            'message': f'Latency injection is now {ms}ms' + (' (disabled)' if ms == 0 else ' (enabled)')
        }), 200
    
    except ValueError:
        return jsonify({'error': 'ms parameter must be an integer'}), 400
    except Exception as e:
        logger.exception("Error in set_latency: %s", e)
        return jsonify({'error': str(e)}), 500


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest(registry), 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/', methods=['GET'])
def root():
    """Root endpoint - basic info."""
    with _state_lock:
        error_state = _inject_errors
        latency_state = _inject_latency_ms
    return jsonify({
        'service': 'controllable-backend',
        'error_injection_enabled': error_state,
        'latency_injection_ms': latency_state,
        'endpoints': {
            '/api/test': 'GET - Main test endpoint (returns 200 or 500 based on injection)',
            '/inject-errors': 'POST - Toggle error injection on/off',
            '/inject-latency': 'POST?ms=N - Set latency injection (0 to disable)',
            '/metrics': 'GET - Prometheus metrics',
            '/health': 'GET - Health check'
        }
    }), 200


if __name__ == '__main__':
    logger.info("Starting controllable-backend Flask server...")
    app.run(host='0.0.0.0', port=5000, debug=False)
