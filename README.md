# PulseOps Application

PulseOps is a lightweight, cloud-native Python/Flask application built to demonstrate and practice Kubernetes observability patterns:
- **Metrics Monitoring:** Prometheus & Grafana
- **Centralized Logging:** FluentBit & OpenSearch

---

## 🚀 Key Features

- **Prometheus Telemetry:** Exposes custom application and HTTP traffic metrics at `/metrics`.
- **Structured JSON Logging:** Emits JSON-formatted logs directly to `stdout` for fluent ingestion into FluentBit and OpenSearch.
- **Interactive UI Console:** Single-screen dashboard to trigger simulated CPU burn cycles, traffic surges, and custom log levels (`INFO`, `WARN`, `ERROR`).
- **Kubernetes Native:** Built-in `/healthz` (liveness) and `/ready` (readiness) endpoints.

---

## 🧭 Endpoints

| Path | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Interactive Control Center UI |
| `/metrics` | `GET` | Prometheus-compatible telemetry scraping endpoint |
| `/healthz` | `GET` | Health probe (Liveness) |
| `/ready` | `GET` | Readiness probe |
| `/api/log` | `POST` | Emit custom JSON log (`level`, `message`) |
| `/api/cpu-burn`| `POST` | Simulate a temporary CPU spike for metrics demonstration |

---

## 🛠️ Local Development

```bash
# Clone the repository
git clone [https://github.com/](https://github.com/)<your-username>/pulse-ops-app.git
cd pulse-ops-app

# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py