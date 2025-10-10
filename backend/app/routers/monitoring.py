"""Monitoring and metrics router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from ..config import settings
from ..utils.metrics import metrics_response

router = APIRouter(tags=["monitoring"])


@router.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
async def prometheus_metrics() -> PlainTextResponse:
    """Expose Prometheus-compatible metrics."""

    if not settings.METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="Metrics disabled")

    payload, content_type = metrics_response()
    return PlainTextResponse(content=payload.decode("utf-8"), media_type=content_type)
