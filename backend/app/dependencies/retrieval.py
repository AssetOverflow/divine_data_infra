"""FastAPI dependencies for orchestrated retrieval."""

from __future__ import annotations

import asyncpg
from fastapi import Depends
from neo4j import AsyncSession

from ..db.neo4j import get_neo4j_session
from ..db.postgres_async import get_pg
from ..services.graph_expansion import GraphExpansionService
from ..services.retrieval_orchestrator import (
    RetrievalOrchestrator,
    resolve_fusion_strategy,
)
from ..services.search_api import SearchApiService


async def get_retrieval_orchestrator(
    conn: asyncpg.Connection = Depends(get_pg),
    session: AsyncSession = Depends(get_neo4j_session),
) -> RetrievalOrchestrator:
    """Provide a retrieval orchestrator composed of search and graph services."""

    search_service = SearchApiService(conn)
    graph_service = GraphExpansionService(session)
    strategy = resolve_fusion_strategy()
    return RetrievalOrchestrator(search_service, graph_service, strategy)
