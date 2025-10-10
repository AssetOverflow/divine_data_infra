"""Analytics endpoints exposing query telemetry metrics."""

from __future__ import annotations

from datetime import datetime

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from ..db.postgres_async import get_pg
from ..models import AnalyticsOverview, QueryCounts, QueryTrends, UsageStats
from ..services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _service(conn: asyncpg.Connection) -> AnalyticsService:
    """Factory helper returning a configured analytics service."""

    return AnalyticsService(conn)


@router.get("/overview", response_model=AnalyticsOverview)
async def analytics_overview(
    start: datetime | None = None,
    end: datetime | None = None,
    interval: str | None = None,
    conn: asyncpg.Connection = Depends(get_pg),
) -> AnalyticsOverview:
    """Return comprehensive analytics over the requested window.

    Example:
        ```bash
        curl "http://localhost:8000/v1/analytics/overview?start=2024-01-01T00:00:00Z&end=2024-01-08T00:00:00Z"
        ```

    Response:
        ```json
        {
          "window_start": "2024-01-01T00:00:00+00:00",
          "window_end": "2024-01-08T00:00:00+00:00",
          "query_counts": {
            "total": 12843,
            "unique_users": 542,
            "average_latency_ms": 18.4,
            "mode_breakdown": [
              {"mode": "hybrid", "count": 6210, "percentage": 48.3}
            ],
            "top_queries": [
              {"query": "love", "count": 412, "last_seen": "2024-01-07T23:59:10+00:00"}
            ]
          },
          "trends": {
            "interval": "day",
            "points": [
              {"bucket_start": "2024-01-01T00:00:00+00:00", "bucket_end": "2024-01-02T00:00:00+00:00", "count": 1902}
            ]
          },
          "usage": {
            "translations": [
              {"translation_code": "NIV", "count": 5210, "percentage": 40.6}
            ],
            "books": [
              {"book_number": 43, "book_name": "John", "count": 812, "percentage": 22.4}
            ]
          }
        }
        ```

    Performance:
        Runs a handful of aggregation queries (Timescale friendly) and typically
        completes in < 30ms on indexed search_log data.
    """

    service = _service(conn)
    try:
        return await service.overview(start=start, end=end, interval=interval)
    except ValueError as exc:  # pragma: no cover - FastAPI handles HTTP response
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/counts", response_model=QueryCounts)
async def analytics_counts(
    start: datetime | None = None,
    end: datetime | None = None,
    conn: asyncpg.Connection = Depends(get_pg),
) -> QueryCounts:
    """Return aggregate query counts and top search terms.

    Example:
        ```bash
        curl "http://localhost:8000/v1/analytics/counts?end=2024-02-01T00:00:00Z"
        ```

    Performance:
        Executes two lightweight aggregations (count + mode breakdown) and
        usually returns in < 15ms on a warm cache.
    """

    service = _service(conn)
    try:
        return await service.counts(start=start, end=end)
    except ValueError as exc:  # pragma: no cover - FastAPI handles HTTP response
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/trends", response_model=QueryTrends)
async def analytics_trends(
    start: datetime | None = None,
    end: datetime | None = None,
    interval: str | None = None,
    conn: asyncpg.Connection = Depends(get_pg),
) -> QueryTrends:
    """Return time-series query trends for dashboards.

    Example:
        ```bash
        curl "http://localhost:8000/v1/analytics/trends?start=2024-01-01T00:00:00Z&interval=hour"
        ```

    Performance:
        Single `date_trunc` aggregation over the `search_log` hypertable – tuned
        for Timescale chunking and expected to run in < 20ms for week-long ranges.
    """

    service = _service(conn)
    try:
        return await service.trends(start=start, end=end, interval=interval)
    except ValueError as exc:  # pragma: no cover - FastAPI handles HTTP response
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/usage", response_model=UsageStats)
async def analytics_usage(
    start: datetime | None = None,
    end: datetime | None = None,
    conn: asyncpg.Connection = Depends(get_pg),
) -> UsageStats:
    """Return translation and book usage statistics derived from logs.

    Example:
        ```bash
        curl "http://localhost:8000/v1/analytics/usage?start=2024-01-01T00:00:00Z&end=2024-01-31T23:59:59Z"
        ```

    Performance:
        Performs two grouped aggregations (translation + first-hit book) and
        should complete in roughly 20ms on indexed datasets.
    """

    service = _service(conn)
    try:
        return await service.usage(start=start, end=end)
    except ValueError as exc:  # pragma: no cover - FastAPI handles HTTP response
        raise HTTPException(status_code=400, detail=str(exc)) from exc
