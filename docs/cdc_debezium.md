# Debezium CDC Feasibility Assessment

## Target Architecture

1. **Source Database**: PostgreSQL 14 (Aurora or RDS) with logical replication enabled.
2. **Connector**: Debezium PostgreSQL connector deployed via Kafka Connect on Kubernetes.
3. **Transport**: Kafka topics partitioned by table (`personalization_events`, `user_profile`, etc.) feeding stream processors and Redis updaters.
4. **Sink Consumers**: Flink jobs for feature rollups, microservices for cache invalidation, lakehouse ingestion for audit.

## Operational Requirements

- Enable `rds.logical_replication` parameter group and ensure tables use `REPLICA IDENTITY FULL` where primary keys are absent.
- Provision write-ahead log (WAL) retention to cover peak outage windows (~6 hours) to prevent slot overflow.
- Manage secrets via Kubernetes secrets/HashiCorp Vault for database credentials.
- Configure dead-letter queue (DLQ) topics to capture serialization issues.

## Pros

- Near real-time propagation (<5s lag) of personalization updates to streaming consumers.
- Schema history topic ensures downstream services track DDL changes.
- Supports filtering by publication to limit noise to high-signal tables.
- Mature ecosystem with Kubernetes + Strimzi operators for simplified ops.

## Risks & Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| High WAL generation during bulk backfills | Storage pressure, slot overflow | Schedule bulk loads during maintenance windows, temporarily pause connector. |
| Connector downtime leading to lag | Stale personalization data | Enable auto-restart policies, monitor lag metrics, and provision buffer in Redis caches. |
| Security/compliance for PII streams | Regulatory exposure | Encrypt topics at rest, restrict ACLs, scrub sensitive fields before publishing. |
| Operational complexity of Kafka Connect | Increased on-call load | Use managed Kafka (e.g., MSK) with Connect support or run via Strimzi for declarative management. |

## Next Steps

1. Spin up sandbox PostgreSQL with logical replication and sample personalization tables.
2. Deploy Debezium connector via Docker Compose to validate throughput targets (>1k events/sec).
3. Define monitoring dashboards (lag, throughput, error rate) and alert thresholds.
4. Run failure injection tests (pause connector, drop network) to validate recovery procedures.
