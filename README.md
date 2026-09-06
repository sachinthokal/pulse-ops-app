# Pulse-Ops: High-Resilience Cloud-Native Observability Stack

An enterprise-grade observability and distributed logging platform deployed on Azure Kubernetes Service (AKS). The architecture instruments a custom microservice (`pulse-ops`) with real-time metrics telemetry and centralized log aggregation, validated under a sustained 100,000-request stress test achieving a 0% error rate and sub-200ms tail latency.

---

## 🏗️ System Architecture

```
                                  [ Azure Load Balancer ]
                                             │
                                             ▼
                               [ pulse-ops Pods (Dual Replica) ]
                                  │                     │
                    (HTTP Telemetry /metrics)       (stdout/stderr)
                                  │                     │
                                  ▼                     ▼
                       [ Prometheus Server ]     [ FluentBit DaemonSet ]
                                  │               (containerd CRI Parser)
                                  ▼                     │
                        [ Grafana Dashboard ]           ▼
                                                 [ OpenSearch Cluster ]
                                                        │
                                                        ▼
                                             [ OpenSearch Dashboards ]

```

### Components

| Layer | Technology | Role / Specification |
| --- | --- | --- |
| **Compute** | Azure Kubernetes Service (AKS) | Managed Kubernetes host with dual-node worker pools. |
| **Workload** | Python / Flask (`pulse-ops`) | Dual-replica deployment handling HTTP requests, latency profiling, and dynamic event injection. |
| **Ingress** | Azure Standard Load Balancer | External traffic ingress and Layer 4 load balancing across pods. |
| **Metrics Pipeline** | Prometheus | Scrapes application runtime metrics and node metrics every 15s. |
| **Visualization** | Grafana | Custom dashboard tracking RPS, p50/p95/p99 latencies, pod load balancing, and node saturation. |
| **Log Collector** | FluentBit (DaemonSet) | Uses `cri` parsing for containerd logs, extracts Kubernetes metadata, and ships structured JSON. |
| **Log Engine** | OpenSearch | Single-node distributed log indexer with disabled security plugins for streamlined lab access. |
| **Log Discovery** | OpenSearch Dashboards | Visual analytics and DQL-based querying for high-cardinality log streams. |

---

## 🚀 Key Configurations

### 1. FluentBit Collector (`fluent-bit-values.yaml`)

Configured to handle AKS `containerd` CRI formatted logs and ship them to the OpenSearch index `pulse-ops-logs`.

```yaml
config:
  service: |
    [SERVICE]
        Flush         1
        Log_Level     info
        Daemon        off
        Parsers_File  parsers.conf
        HTTP_Server   On
        HTTP_Port     2020

  inputs: |
    [INPUT]
        Name              tail
        Tag               kube.*
        Path              /var/log/containers/*pulse-ops*.log
        Parser            cri
        DB                /var/log/flb_kube.db
        Mem_Buf_Limit     5MB
        Skip_Long_Lines   On

  filters: |
    [FILTER]
        Name                kubernetes
        Match               kube.*
        Kube_URL            https://kubernetes.default.svc:443
        Merge_Log           On
        Merge_Log_Key       log_processed
        Keep_Log            Off
        K8S-Logging.Parser  On
        K8S-Logging.Exclude On

  outputs: |
    [OUTPUT]
        Name            opensearch
        Match           kube.*
        Host            opensearch-cluster-master
        Port            9200
        Index           pulse-ops-logs
        Type            _doc
        tls             Off
        tls.verify      Off
        Suppress_Type_Name On

```

### 2. OpenSearch Dashboards (`dashboards-values.yaml`)

Allocated dedicated memory limits to avoid NodeJS startup throttling and configured in no-auth mode.

```yaml
opensearchHosts: "http://opensearch-cluster-master:9200"

resources:
  requests:
    cpu: "300m"
    memory: "768Mi"
  limits:
    cpu: "1000m"
    memory: "1536Mi"

config:
  opensearch_dashboards.yml: |
    server.host: "0.0.0.0"
    opensearch.hosts: ["http://opensearch-cluster-master:9200"]
    opensearch.ssl.verificationMode: none

opensearchAccount:
  security:
    disabled: true

extraEnvs:
  - name: DISABLE_SECURITY_DASHBOARDS_PLUGIN
    value: "true"

startupProbe:
  tcpSocket:
    port: 5601
  initialDelaySeconds: 20
  periodSeconds: 10
  failureThreshold: 30

```

---

## ⚡ Stress Testing & System Verification

The infrastructure was subjected to a high-volume load test using ApacheBench to validate concurrency management, resource ceilings, and metric/log correlation under heavy load.

```bash
ab -l -n 100000 -c 10 http://<EXTERNAL-IP>/

```

### Benchmark Results

| Metric | Result |
| --- | --- |
| **Total Completed Requests** | **100,000** |
| **Failed Requests** | **0 (0.00% Error Rate)** |
| **Test Duration** | **1,423.48 seconds (~23.7 minutes)** |
| **Throughput (Sustained)** | **70.25 req/sec** |
| **Total Network Transfer** | **1.70 GB** (1,702,142,073 bytes) |
| **Median Latency (50%)** | **118 ms** |
| **P95 Latency** | **151 ms** |
| **P99 Tail Latency** | **175 ms** |

---

## 📊 Telemetry & Observability Verification

### 1. Real-Time Grafana Metrics

* **Traffic Balancing:** The Azure Load Balancer divided traffic equally across both pods (~35 req/s per replica).
* **Resource Stability:** Memory consumption remained flat at ~27 MiB per pod across the 24-minute stress run, confirming zero memory leaks. Peak CPU utilization stayed within 0.12 cores per pod.
* **Service Levels:** Zero 5xx responses observed; `pulse_ops_requests_total` reflected cumulative increments up to 265K+.

### 2. Centralized Logging (OpenSearch)

* **Ingestion Throughput:** FluentBit parsed and indexed 124,000+ business HTTP access logs and diagnostic events during the benchmark without backpressure.
* **Field Indexing:** Full metadata enrichment for `kubernetes.pod_name`, `kubernetes.host`, `status`, and `timestamp`.
* **Noise Isolation Query (DQL):**
```text
message: *HTTP* and not message: *metrics* and not message: *ready*

```



---

## 🛠️ Deployment Instructions

### Prerequisites

* Azure CLI configured with an active AKS cluster.
* Helm v3 and `kubectl` connected to your cluster context.

### 1. Deploy the Application Workload

```bash
kubectl apply -f k8s/pulse-ops-deployment.yaml
kubectl apply -f k8s/pulse-ops-service.yaml

```

### 2. Deploy Metrics Pipeline (Prometheus & Grafana)

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace

```

### 3. Deploy OpenSearch & Dashboards

```bash
helm repo add opensearch https://opensearch-project.github.io/helm-charts
helm repo update

# Install OpenSearch Cluster
helm install opensearch-cluster opensearch/opensearch \
  --namespace logging --create-namespace \
  --set singleNode=true \
  --set config."plugins\.security\.disabled"=true

# Install OpenSearch Dashboards
helm install opensearch-dashboards opensearch/opensearch-dashboards \
  --namespace logging \
  -f dashboards-values.yaml

```

### 4. Deploy FluentBit DaemonSet

```bash
helm repo add fluent https://fluent.github.io/helm-charts
helm repo update

helm install fluent-bit fluent/fluent-bit \
  --namespace logging \
  -f fluent-bit-values.yaml

```

---

## 🧹 Resource Teardown

To avoid unnecessary cloud consumption, tear down the deployed resources:

```bash
# Remove Helm charts
helm uninstall fluent-bit -n logging
helm uninstall opensearch-dashboards -n logging
helm uninstall opensearch-cluster -n logging
helm uninstall monitoring -n monitoring

# Delete application resources
kubectl delete -f k8s/pulse-ops-service.yaml
kubectl delete -f k8s/pulse-ops-deployment.yaml

# Delete namespaces
kubectl delete namespace logging monitoring

```