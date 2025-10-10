"""
Neo4j Graph Seeding Script for DivineHaven

Seeds the Neo4j knowledge graph with biblical text data from PostgreSQL.
Creates Book, Chapter, and Verse nodes with relationships and cross-translation links.

This ETL script demonstrates async PostgreSQL streaming with synchronous Neo4j operations,
efficiently processing hundreds of thousands of verses without memory exhaustion.

Environment Variables:
    DATABASE_URL: PostgreSQL connection string
    NEO4J_URI: Neo4j bolt URI (default: bolt://localhost:7687)
    NEO4J_USER: Neo4j username (default: neo4j)
    NEO4J_PASSWORD: Neo4j password (default: password)
    MANIFEST_JSON: Optional path to manifest.json
    GRAPH_BATCH_SIZE: Verses per batch (default: 5000)
    GRAPH_LINK_MODE: Linking strategy - "per-batch" or "post" (default: per-batch)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Optional, Set

from dotenv import load_dotenv

from pg_client import PgClient
from neo4j_client import Neo4jClient

# Load environment variables from .env file
load_dotenv()

# Configuration from environment with sensible defaults
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:Fr00pzPlz@localhost:5432/divinehaven",
)
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
MANIFEST_JSON = os.getenv("MANIFEST_JSON", "./manifest.json")
BATCH_SIZE = int(os.getenv("GRAPH_BATCH_SIZE", "5000"))
LINK_MODE = os.getenv("GRAPH_LINK_MODE", "per-batch")


def read_manifest(path: str) -> Optional[dict]:
    """
    Load and parse the manifest JSON file if it exists.

    The manifest provides metadata about the embedding pipeline run,
    including model information, pipeline version, and data sources.

    Args:
        path: File system path to manifest.json

    Returns:
        Parsed manifest dictionary with pipeline metadata, or None if
        file doesn't exist or fails to parse

    Example manifest structure:
        ```json
        {
            "run_id": "2024-01-15T10:30:00Z",
            "embedding_recipe": {
                "embedding_model": "embeddinggemma",
                "embedding_dim": 768
            }
        }
        ```
    """
    p = Path(path)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


async def run_async(batch_size: int, link_mode: str) -> None:
    """
    Main async pipeline for seeding Neo4j graph from PostgreSQL.

    Pipeline Modes:
        per-batch: Link PARALLEL_TO edges after each batch (real-time, slower)
        post: Link all PARALLEL_TO edges after verse upsert (faster, higher memory)

    Args:
        batch_size: Number of verses to process per batch
        link_mode: Linking strategy ("per-batch" or "post")

    Performance Notes:
        - Uses async PostgreSQL with server-side cursors for streaming
        - Neo4j operations run in thread pool to keep event loop responsive
        - Expected throughput: 5,000-10,000 verses/second depending on hardware
    """
    manifest = read_manifest(MANIFEST_JSON)
    if manifest:
        run_id = manifest.get("run_id", "?")
        model = manifest.get("embedding_recipe", {}).get("embedding_model", "?")
        print(f"[seed] Manifest run_id: {run_id} | model: {model}")

    # Initialize async Postgres client
    async with PgClient(DATABASE_URL) as pg:
        # Initialize sync Neo4j client (will run in thread pool)
        g = Neo4jClient(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        loop = asyncio.get_running_loop()

        print("[seed] Ensuring constraints & indexes…")
        await loop.run_in_executor(None, g.init_constraints)

        total_rows = 0
        touched_cvks: Set[str] = set()

        print(f"[seed] Upserting Books/Chapters/Verses (batch size: {batch_size})…")
        batch_count = 0

        async for batch in pg.iter_verses(batch_size=batch_size):
            batch_count += 1
            # merge_batch returns Set[str] of canonical verse keys that were touched
            cvks = await loop.run_in_executor(None, g.merge_batch, batch)
            total_rows += len(batch)
            print(
                f"[seed] batch {batch_count:>5} upserted {len(batch):>5} rows (total {total_rows:,})"
            )

            if link_mode == "per-batch":
                await loop.run_in_executor(None, g.link_parallels_for_cvks, cvks)
            else:
                touched_cvks.update(cvks)

        if link_mode == "post" and touched_cvks:
            print(
                f"[seed] Linking PARALLEL_TO across {len(touched_cvks):,} canonical keys…"
            )
            await loop.run_in_executor(None, g.link_parallels_for_cvks, touched_cvks)

        # Clean shutdown
        g.close()

    print(f"[seed] ✓ Done. Total verses processed: {total_rows:,}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Seed Neo4j knowledge graph from PostgreSQL biblical text data"
    )
    ap.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help="Number of verses per batch (default: 5000)",
    )
    ap.add_argument(
        "--link-mode",
        choices=["per-batch", "post"],
        default=LINK_MODE,
        help="When to create PARALLEL_TO edges (default: per-batch)",
    )
    args = ap.parse_args()

    asyncio.run(run_async(args.batch_size, args.link_mode))
