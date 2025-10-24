# Agentic RAG + Knowledge Graph Roadmap

## Vision Alignment
Position the platform as a **Bible Study deep-agent stack** where semantic retrieval, canonical graph traversal, and reasoning-aware metadata converge. Agent workflows should access three synchronized knowledge planes:

1. **Structured doctrine graph** (Neo4j) for canonical, thematic, and cross-translation navigation.
2. **Vector narrative space** (pgvector/vectorscale) for semantically aligned verse and commentary retrieval.
3. **Procedural memory** capturing agent traces, question/answer pairs, and citation chains for auditability.

## Immediate Enhancements (0-3 Months)
- **Operationalize KG querying** — Build FastAPI service modules that expose canonical verse neighbors, translation parallels, and pathfinding between theological concepts using the existing Neo4j schema (`backend/etl/neo4j_client.py`).
- **Hybrid retrieval broker** — Introduce an orchestration layer (e.g., a `RetrievalOrchestrator` service) that combines semantic scores (`backend/app/services/search.py`) with Neo4j neighborhood context to generate richer agent prompts (verse + cross-translation + graph-derived themes).
- **Data quality & lineage checks** — Add manifest-aware validation jobs ensuring every verse in PostgreSQL has a matching CV node and `PARALLEL_TO` edges, and flag translation gaps before refreshing ANN indexes.
- **Observability & governance** — Implement structured logging, Prometheus metrics, and tracing (e.g., OpenTelemetry) for both API and ETL flows to monitor latency, hit rates, and pipeline freshness.

## Mid-Term Build-Out (3-6 Months)
- **Workflow orchestration** — Adopt Dagster or Temporal to codify manifest ingestion, embedding generation, pgvector index builds, and Neo4j seeding into observable DAGs with retry semantics.
- **Knowledge graph enrichment** — Extend the graph schema with topic, entity, and intertextual link nodes by applying NLP tagging during ingestion. Store generated annotations back into Postgres for hybrid retrieval filters.
- **Agent memory store** — Create a Redis or Postgres-backed interaction log capturing agent prompts, sources, and outcomes. Enable Neo4j to store relationships between queries and verses to inform follow-up reasoning.
- **Evaluation harness** — Integrate pytest-based golden sets plus offline retrieval evaluation suites to benchmark hybrid relevance and graph coverage per manifest revision.

## Long-Term Differentiators (6-12 Months)
- **Multi-agent retrieval loops** — Coordinate specialized agents (lexical exegete, translation critic, thematic summarizer) that each query tailored indexes and then reconcile their findings via orchestrated reasoning steps.
- **Contextual caching & personalization** — Use Redis or a feature store to persist user study trails, favorite translations, and doctrinal preferences, feeding those signals into label-aware vector retrieval and graph traversal heuristics.
- **Streaming updates** — Implement CDC pipelines (e.g., Debezium) from Postgres into Neo4j and the vector store so that commentary additions or translation revisions instantly refresh downstream retrieval surfaces.
- **Trust & provenance layer** — Track verse/translation provenance, commentary licenses, and model versions directly in the manifest to meet theological scholarship rigor and support AI-generated citations.

Realizing this roadmap transforms the repository from a strong retrieval backend into an **agentic, citation-first Bible study intelligence** capable of powering deep spiritual inquiry and automated doctrinal synthesis.
