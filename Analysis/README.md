# Divine Data Infra — Repository Analysis Overview

This repository delivers a multi-modal Bible study data platform combining relational storage, vector search, and graph-based cross-translation knowledge. The stack centers on:

- **PostgreSQL + pgvector/vectorscale** for canonical verse storage, DiskANN-powered embeddings, and full-text search primitives exposed through the FastAPI search service (`backend/app/services/search.py`).
- **Neo4j knowledge graph** seeded by the `backend/etl` pipeline to capture translation, canonical verse, and cross-translation relationships optimized for parallel verse exploration (`backend/etl/neo4j_client.py`).
- **FastAPI backend** with async connection pools, manifest-aware configuration, and service layers that surface semantic, lexical, hybrid search, and analytics endpoints (`backend/app/main.py`, `backend/app/services`).
- **Embedding orchestration** driven by manifest metadata (`manifest.json` & `manifest_cli.py`) describing embedding recipes, index strategies, and translation coverage for auditability and reproducibility.
- **Unified JSON Bibles corpus** (`unified_json_bibles/`) providing multi-language verse payloads that backfill both relational and graph stores.

The codebase is structured with production-ready patterns (connection pooling, async I/O, dependency injection, manifest-driven metadata) but will require targeted enhancements to operate as a modern agentic-RAG knowledge graph backend. The following analysis files dive into the current architecture, data engineering posture, and roadmap recommendations.
