"""Retrieval router exposing orchestrated search endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies.retrieval import get_retrieval_orchestrator
from ..models import RetrievalQuery, RetrievalResponse
from ..services.retrieval_orchestrator import RetrievalOrchestrator

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/query", response_model=RetrievalResponse)
async def orchestrated_retrieval(
    body: RetrievalQuery,
    orchestrator: RetrievalOrchestrator = Depends(get_retrieval_orchestrator),
) -> RetrievalResponse:
    """Execute hybrid search with manifest-driven fusion and graph expansion."""

    try:
        return await orchestrator.retrieve(body)
    except ValueError as exc:  # propagate validation errors as HTTP 400
        raise HTTPException(status_code=400, detail=str(exc)) from exc
