import os
import time
import json
import logging
from flask import Flask, render_template, request, jsonify, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Configure JSON structured logging for FluentBit
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "pod_name": os.environ.get("POD_NAME", "local-pod"),
            "node_name": os.environ.get("NODE_NAME", "local-node")
        }
        return json.dumps(log_record)

logger = logging.getLogger("pulse-ops")
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.handlers = [handler]
logger.setLevel(logging.INFO)

app = Flask(__name__)

# Prometheus Metrics
REQUEST_COUNT = Counter(
    "pulse_ops_requests_total",
    "Total HTTP requests handled by pulse-ops-app",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "pulse_ops_request_duration_seconds",
    "HTTP request latency in seconds",
    ["endpoint"]
)
SIMULATED_ERRORS = Counter(
    "pulse_ops_simulated_errors_total",
    "Total simulated errors triggered from UI",
    ["type"]
)

@app.before_request
def start_timer():
    request._start_time = time.time()

@app.after_request
def record_metrics(response):
    if hasattr(request, "_start_time") and request.path != "/metrics":
        latency = time.time() - request._start_time
        REQUEST_LATENCY.labels(endpoint=request.path).observe(latency)
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.path,
            status=response.status_code
        ).inc()
    return response

@app.route("/")
def index():
    return render_template(
        "index.html",
        app_version=os.environ.get("APP_VERSION", "v1.0.0"),
        node_name=os.environ.get("NODE_NAME", "localhost"),
        pod_name=os.environ.get("POD_NAME", "pulse-ops-standalone")
    )

# Metrics endpoint for Prometheus Scraper
@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

# Health endpoints for Kubernetes Probes
@app.route("/healthz")
def healthz():
    return jsonify({"status": "healthy"}), 200

@app.route("/ready")
def ready():
    return jsonify({"status": "ready"}), 200

# Action: Generate custom logs for FluentBit & OpenSearch
@app.route("/api/log", methods=["POST"])
def generate_log():
    data = request.get_json() or {}
    level = data.get("level", "INFO").upper()
    message = data.get("message", "Triggered manual log event")

    if level == "WARN":
        logger.warning(message)
    elif level == "ERROR":
        SIMULATED_ERRORS.labels(type="runtime_error").inc()
        logger.error(message)
    else:
        logger.info(message)

    return jsonify({"status": "logged", "level": level, "message": message}), 200

# Action: Simulate CPU Spike for Prometheus Metrics demonstration
@app.route("/api/cpu-burn", methods=["POST"])
def cpu_burn():
    logger.warning("Simulating transient CPU spike for 4 seconds")
    start = time.time()
    while time.time() - start < 4:
        _ = 1000 * 1000
    return jsonify({"status": "completed", "message": "CPU burn finished"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)