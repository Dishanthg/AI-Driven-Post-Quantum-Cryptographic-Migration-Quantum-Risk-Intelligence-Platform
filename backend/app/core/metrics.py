"""Prometheus instrumentation (design doc Section 49). Tracks API latency by
route, plus counters for the "real work" operations whose cost matters most
here - benchmark executions and quantum-lab runs - so Grafana can show
whether a benchmark/quantum run is slow because of the algorithm itself or
because of surrounding request overhead.
"""
from __future__ import annotations

import time

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_LATENCY = Histogram(
    "quantumshield_http_request_duration_seconds", "HTTP request latency", ["method", "path", "status"]
)
REQUEST_COUNT = Counter(
    "quantumshield_http_requests_total", "HTTP requests", ["method", "path", "status"]
)
BENCHMARK_RUNS = Counter(
    "quantumshield_benchmark_runs_total", "Cryptographic benchmark executions", ["provider_key", "operation"]
)
QUANTUM_RUNS = Counter(
    "quantumshield_quantum_runs_total", "Quantum lab executions", ["kind"]
)
MODEL_INFERENCE_LATENCY = Histogram(
    "quantumshield_model_inference_duration_seconds", "AI risk model inference latency", ["method"]
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        route_template = request.url.path
        for route in request.app.routes:
            if hasattr(route, "path_regex") and route.path_regex.match(request.url.path):
                route_template = route.path
                break
        start = time.perf_counter()
        response: Response = await call_next(request)
        duration = time.perf_counter() - start
        REQUEST_LATENCY.labels(request.method, route_template, response.status_code).observe(duration)
        REQUEST_COUNT.labels(request.method, route_template, response.status_code).inc()
        return response


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
