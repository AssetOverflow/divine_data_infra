"""
Async Neo4j connection management for FastAPI.

Provides async Neo4j driver initialization and session dependency injection
for FastAPI routes. The driver is initialized once at module load and reused
across all requests for optimal performance.

The session dependency handles automatic resource cleanup via async context
manager pattern, ensuring connections are properly returned to the pool.

Environment Variables (from config):
    NEO4J_URI: Neo4j bolt connection URI (e.g., bolt://localhost:7687)
    NEO4J_USER: Neo4j username for authentication
    NEO4J_PASSWORD: Neo4j password for authentication

Example Usage:
    ```python
    from fastapi import Depends
    from neo4j import AsyncSession
    from .db.neo4j import get_neo4j_session

    @router.get("/graph/verse/{verse_id}")
    async def get_verse_relationships(
        verse_id: str,
        session: AsyncSession = Depends(get_neo4j_session)
    ):
        query = '''
            MATCH (v:Verse {verse_id: $verse_id})-[r]->(related)
            RETURN v, r, related
        '''
        result = await session.run(query, verse_id=verse_id)
        records = await result.data()
        return records
    ```
"""

from typing import AsyncIterator
from neo4j import AsyncGraphDatabase, AsyncSession, AsyncDriver
from ..config import settings

# Global async driver instance (initialized at module load)
driver: AsyncDriver = AsyncGraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
)


async def get_neo4j_session() -> AsyncIterator[AsyncSession]:
    """
    FastAPI dependency for injecting Neo4j sessions.

    Acquires a session from the driver, yields it to the route handler,
    then automatically closes the session when the request completes.

    Yields:
        AsyncSession: Neo4j async session for the current request

    Example:
        ```python
        @router.get("/parallel-verses/{verse_id}")
        async def get_parallel_verses(
            verse_id: str,
            session: AsyncSession = Depends(get_neo4j_session)
        ):
            query = '''
                MATCH (v:Verse {verse_id: $verse_id})-[:PARALLEL_TO]-(parallel:Verse)
                RETURN parallel.verse_id AS verse_id,
                       parallel.translation AS translation,
                       parallel.text AS text
                ORDER BY parallel.translation
            '''
            result = await session.run(query, verse_id=verse_id)
            records = await result.data()
            return {"parallels": records}
        ```

    Note:
        The driver is initialized at module load time and shared across all
        requests. Individual sessions are created per request and automatically
        cleaned up via the async context manager.
    """
    async with driver.session() as session:
        yield session
