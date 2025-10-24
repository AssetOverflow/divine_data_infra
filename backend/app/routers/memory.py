"""HTTP routes for managing conversational session memory."""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..config import settings
from ..db.postgres_async import get_pg
from ..models import (
    SessionContextResponse,
    SessionMessage,
    SessionMessageAppendRequest,
    SessionMessageUpdate,
)
from ..services.memory import SessionMemoryService

router = APIRouter(prefix="/sessions", tags=["session-memory"])


async def get_session_memory_service(
    conn: asyncpg.Connection = Depends(get_pg),
) -> SessionMemoryService:
    """Provide a session memory service bound to the request scope.

    Parameters:
        conn: Dependency-injected PostgreSQL connection supplied by the
            application.

    Returns:
        A :class:`SessionMemoryService` configured for the active request.
    """

    return SessionMemoryService(conn)


@router.post(
    "/{session_id}/messages",
    response_model=SessionMessage,
    status_code=status.HTTP_201_CREATED,
)
async def append_session_message(
    session_id: str,
    payload: SessionMessageAppendRequest,
    service: SessionMemoryService = Depends(get_session_memory_service),
) -> SessionMessage:
    """Append a new message and optional citation trail to a session.

    Parameters:
        session_id: Identifier for the session that should receive the
            additional message.
        payload: Structured message payload supplied by the agent client.
        service: Session memory service instance scoped to the request.

    Returns:
        The persisted :class:`SessionMessage` record.
    """

    try:
        return await service.append_message(session_id, payload)
    except ValueError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{session_id}/messages", response_model=SessionContextResponse)
async def list_session_messages(
    session_id: str,
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
    service: SessionMemoryService = Depends(get_session_memory_service),
) -> SessionContextResponse:
    """Retrieve a paginated slice of memory for a conversation session.

    Parameters:
        session_id: Identifier for the session to query.
        limit: Maximum number of messages to return (bounded by configuration).
        offset: Number of messages to skip before returning results.
        service: Session memory service instance scoped to the request.

    Returns:
        A :class:`SessionContextResponse` containing paginated session memory.
    """

    limit = min(limit, settings.PAGE_MAX)
    return await service.list_session_context(
        session_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{session_id}/messages/{message_id}", response_model=SessionMessage)
async def get_session_message(
    session_id: str,
    message_id: int,
    service: SessionMemoryService = Depends(get_session_memory_service),
) -> SessionMessage:
    """Fetch a single session message with its citation context.

    Parameters:
        session_id: Identifier for the session that owns the message.
        message_id: Primary key of the message to retrieve.
        service: Session memory service instance scoped to the request.

    Returns:
        The requested :class:`SessionMessage` including citations.
    """

    try:
        return await service.get_message(session_id, message_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{session_id}/messages/{message_id}", response_model=SessionMessage)
async def update_session_message(
    session_id: str,
    message_id: int,
    payload: SessionMessageUpdate,
    service: SessionMemoryService = Depends(get_session_memory_service),
) -> SessionMessage:
    """Update message content, metadata, or citation trails.

    Parameters:
        session_id: Identifier for the session that owns the message.
        message_id: Primary key of the message to update.
        payload: Partial update payload describing the mutation.
        service: Session memory service instance scoped to the request.

    Returns:
        The updated :class:`SessionMessage` model.
    """

    try:
        return await service.update_message(session_id, message_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete(
    "/{session_id}/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_session_message(
    session_id: str,
    message_id: int,
    service: SessionMemoryService = Depends(get_session_memory_service),
) -> None:
    """Delete a single message from the conversation session.

    Parameters:
        session_id: Identifier for the session that owns the message.
        message_id: Primary key of the message to delete.
        service: Session memory service instance scoped to the request.
    """

    try:
        await service.delete_message(session_id, message_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{session_id}/messages", response_model=dict)
async def clear_session_messages(
    session_id: str,
    service: SessionMemoryService = Depends(get_session_memory_service),
) -> dict:
    """Remove all messages stored for the session and report the count removed.

    Parameters:
        session_id: Identifier for the session to clear.
        service: Session memory service instance scoped to the request.

    Returns:
        A mapping containing the session identifier and number of deleted
        messages.
    """

    deleted = await service.clear_session(session_id)
    return {"session_id": session_id, "deleted": deleted}
