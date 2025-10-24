# Data Infrastructure Assessment

## Storage & Data Models
- **Relational core (PostgreSQL 17 + pgvector/vectorscale)** — Async connection pooling and DSN normalization in `backend/app/db/postgres_async.py` enable FastAPI request lifecycles to reuse pooled connections while preparing for advanced ANN indexes. Verse content, embeddings, and metadata live in normalized tables orchestrated via the manifest SQL emitters (`manifest_cli.py`).
- **Knowledge graph (Neo4j)** — The ETL client (`backend/etl/neo4j_client.py`) materializes a canonical verse graph with Translation → Book → Chapter → Verse hierarchies, canonical verse (CV) nodes, and bidirectional `PARALLEL_TO` edges for cross-translation linkage. Constraints are idempotently managed to keep ingestion reproducible.
- **Corpus layer** — The `unified_json_bibles/` directory aggregates per-translation JSON payloads that provide a denormalized source of truth spanning English, Spanish, Greek (LXX), and Hebrew (TNK) texts for ingestion.

## Data Pipelines & Manifest Governance
- **ETL sequencing** — `backend/etl/seed_graph.py` streams verse batches from PostgreSQL to Neo4j using asyncpg server-side cursors and thread-pooled Cypher execution. Batch linking and optional post-processing support large-scale replays without exhausting memory, making iterative graph enrichment feasible.
- **Manifest-driven control plane** — `manifest.json` captures embedding recipe metadata (model, dimensionality, chunking strategy, filters) and index planning parameters (DiskANN HNSW, hybrid RRF fusion). `manifest_cli.py` validates, emits SQL DDL, and tracks per-batch hashes to guarantee reproducible vector + FTS indexes.
- **Embedding services** — `backend/app/services/embeddings.py` and the FastAPI service layer coordinate Ollama-based embedding generation, aligning runtime inference with the manifest-declared model.

## Serving Layer & Query Patterns
- **FastAPI service tier** — `backend/app/main.py` wires dependency-injected search, verse, and analytics routers that consume async services. Caching, metrics, and rate limiting hooks exist in configuration but need production hardening.
- **Search primitives** — `backend/app/services/search.py` implements semantic, lexical, and hybrid search with label filtering, DiskANN vector search, ts_rank FTS, and reciprocal rank fusion. Context window retrieval is anchored on absolute verse indexing for narrative-aware retrieval.
- **Graph access** — Although the ETL constructs a rich Neo4j graph, there are no dedicated query services yet that expose canonical verse traversal or edge analytics through the API.

## Strengths
- Clear separation between relational, vector, and graph concerns with reusable service abstractions.
- Manifest-led governance tightly couples embedding generation with index configuration, aiding audits and automated regeneration.
- ETL batch patterns are idempotent and support both incremental updates and full rebuilds without manual cleanup.

## Gaps & Risks
- Missing orchestration glue (e.g., Dagster, Prefect, Temporal) to schedule and monitor manifest → embedding → ETL workflows, limiting automation.
- Neo4j graph is write-populated but underutilized at query time; agentic graph traversal APIs and KG analytics are absent.
- No explicit data quality validation layer (schema drift checks, verse alignment audits) before seeding search indexes and the graph.
- Redis + rate limiting scaffolding exists in configuration yet lacks concrete caching strategy definitions (e.g., verse detail caching, embedding reuse caches).
- Lacks observability wiring (structured logs, traces, metrics exporters) despite configuration hints, making SLO governance difficult.
