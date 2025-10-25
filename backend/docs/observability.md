# Observability Guide

This document outlines the core dashboards, alerts, and service level objectives (SLOs) for DivineHaven.

## Service Map

* **API (`divinehaven-api`)** – FastAPI service serving search, analytics, and monitoring routes.
* **ETL (`divinehaven-api-etl`)** – Offline pipeline that hydrates Neo4j from PostgreSQL.

Both services emit JSON logs enriched with OpenTelemetry trace metadata, expose Prometheus metrics, and can
export distributed traces to OTLP or Jaeger backends.

## Key Metrics

| Metric | Description | Source |
| --- | --- | --- |
| `divinehaven_requests_total` | HTTP request throughput by method/path/status | FastAPI middleware |
| `divinehaven_request_latency_seconds` | Histogram of request latency | FastAPI middleware |
| `divinehaven_request_errors_total` | 5xx error counter | FastAPI middleware |
| `divinehaven_db_query_duration_seconds` | Summary of DB query latency | Repository layer |
| `divinehaven_etl_rows_processed_total` | Total Neo4j rows processed | ETL pipeline |
| `divinehaven_etl_batch_latency_seconds` | Histogram of ETL batch duration | ETL pipeline |
| `divinehaven_etl_batches_total` | Number of batches processed | ETL pipeline |

## Dashboards

### 1. API Golden Signals (Grafana)

* **Panel 1 – Request Rate:** `sum(rate(divinehaven_requests_total[5m])) by (method)`
* **Panel 2 – Error Rate:** `sum(rate(divinehaven_request_errors_total[5m])) by (path)`
* **Panel 3 – Latency (p50/p90/p99):** `histogram_quantile(0.99, sum(rate(divinehaven_request_latency_seconds_bucket[5m])) by (le))`
* **Panel 4 – Database Time:** `sum(increase(divinehaven_db_query_duration_seconds_sum[5m])) / sum(increase(divinehaven_db_query_duration_seconds_count[5m]))`
* **Panel 5 – Cache Health:** `rate(divinehaven_cache_hits_total[5m])` vs `rate(divinehaven_cache_misses_total[5m])`

### 2. ETL Throughput Dashboard

* **Panel 1 – Rows/sec:** `rate(divinehaven_etl_rows_processed_total[5m])`
* **Panel 2 – Batch Duration:** `histogram_quantile(0.95, sum(rate(divinehaven_etl_batch_latency_seconds_bucket[5m])) by (le, link_mode))`
* **Panel 3 – In-flight Batches:** `sum(increase(divinehaven_etl_batches_total[5m])) by (link_mode)`
* **Panel 4 – Error Logs:** Explore logs filtered by `service="divinehaven-api-etl"` in the logging backend.

### 3. Tracing Overview

* **Jaeger/Tempo Search:** Filter by `service.name` to view API or ETL traces.
* **Slowest Requests:** Use trace duration filters to identify requests exceeding latency SLOs.

## SLOs & Alerts

| Objective | Target | Alert Rule |
| --- | --- | --- |
| Availability | 99.5% of requests return <500 over 30d | `increase(divinehaven_request_errors_total[1h]) / increase(divinehaven_requests_total[1h]) > 0.005` (multi-window burn alerts) |
| Latency | p95 latency < 750ms for search endpoints | `histogram_quantile(0.95, sum(rate(divinehaven_request_latency_seconds_bucket{path=~"/v1/search.*"}[5m])) by (le)) > 0.75` |
| ETL Freshness | 95% of batches finish < 30s | `histogram_quantile(0.95, sum(rate(divinehaven_etl_batch_latency_seconds_bucket[5m])) by (le)) > 30` |
| ETL Throughput | Minimum 10k verses/minute | `rate(divinehaven_etl_rows_processed_total[5m]) < 10000` |

Alerting should use multi-window, multi-burn rate strategies where possible to reduce noise. Traces generated for
request IDs breaching latency SLOs should be cross-linked in the alert payload to speed incident triage.

## Deployment Checklist

1. **Logging:** Ensure `LOG_LEVEL` and `OTEL_SERVICE_NAME` are set per environment.
2. **Tracing:** Set `TRACING_EXPORTER` (`otlp` or `jaeger`), the relevant endpoint, and optional headers.
3. **Metrics:** Confirm `METRICS_ENABLED=true` for the API, and start the ETL metrics HTTP server (default `:9001`).
4. **Dashboards:** Import the Grafana JSON definitions or recreate panels using the PromQL snippets above.
5. **Alerting:** Configure Prometheus alert rules using the SLO thresholds listed above.

With these components deployed, DivineHaven gains end-to-end observability across the request path and the data ingestion pipeline.
