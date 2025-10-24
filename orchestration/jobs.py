"""Dagster job definitions for DivineHaven orchestration."""

from __future__ import annotations

from dagster import graph

from .ops import (
    embedding_generation_op,
    manifest_validation_op,
    neo4j_seeding_op,
    pgvector_index_build_op,
)


@graph(description="Validate the manifest.json payload")
def manifest_validation_graph():
    manifest_validation_op()


manifest_validation_job = manifest_validation_graph.to_job(name="manifest_validation_job")


@graph(description="Validate manifest and trigger embedding generation")
def embedding_generation_graph():
    manifest = manifest_validation_op()
    embedding_generation_op(manifest)


embedding_generation_job = embedding_generation_graph.to_job(name="embedding_generation_job")


@graph(description="Generate embeddings and build pgvector indexes")
def pgvector_index_graph():
    manifest = manifest_validation_op()
    embedded_manifest = embedding_generation_op(manifest)
    pgvector_index_build_op(embedded_manifest)


pgvector_index_job = pgvector_index_graph.to_job(name="pgvector_index_job")


@graph(description="Validate manifest and seed Neo4j metadata")
def neo4j_seeding_graph():
    manifest = manifest_validation_op()
    neo4j_seeding_op(manifest)


neo4j_seeding_job = neo4j_seeding_graph.to_job(name="neo4j_seeding_job")


@graph(description="End-to-end data refresh across validation, embeddings, indexes, and graph")
def full_data_refresh_graph():
    manifest = manifest_validation_op()
    embedded_manifest = embedding_generation_op(manifest)
    indexed_manifest = pgvector_index_build_op(embedded_manifest)
    neo4j_seeding_op(indexed_manifest)


full_data_refresh_job = full_data_refresh_graph.to_job(name="full_data_refresh_job")
