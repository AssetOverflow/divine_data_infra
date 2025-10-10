"""
Graph database router for cross-translation verse relationships.

Provides endpoints for querying the Neo4j knowledge graph to find:
- Parallel verses across translations (renditions of same canonical verse)
- Canonical verse (CV) to rendition mappings

The graph schema links Translation -> Book -> Chapter -> Verse -> CV nodes,
enabling efficient cross-translation queries via the canonical verse key (CVK).

Example Usage:
    ```bash
    # Get all translations of John 3:16
    curl http://localhost:8000/v1/graph/parallels/NIV_43_3_16_

    # Get all renditions of a canonical verse
    curl http://localhost:8000/v1/graph/cv/43:3:16:/renditions
    ```

Graph Schema:
    - Translation nodes: {code}
    - Book nodes: {translation, number, name}
    - Chapter nodes: {translation, book_number, number}
    - Verse nodes: {verse_id, translation, reference, text}
    - CV nodes: {cvk, book_number, chapter_number, verse_number, suffix}

Relationships:
    Translation -[:HAS_BOOK]-> Book -[:HAS_CHAPTER]-> Chapter -[:HAS_VERSE]-> Verse
    Verse -[:RENDITION_OF]-> CV (canonical verse)
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from neo4j import AsyncSession, AsyncResult
from ..db.neo4j import get_neo4j_session
from ..models import ParallelsResponse, Rendition

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/parallels/{verse_id}", response_model=ParallelsResponse)
async def parallels_by_verse(
    verse_id: str,
    session: AsyncSession = Depends(get_neo4j_session)
) -> ParallelsResponse:
    """
    Find all parallel verse renditions across translations.

    Given a specific verse ID (e.g., "NIV_43_3_16_"), returns all translation
    renditions of the same canonical verse. This is useful for comparative
    Bible study and multi-translation viewing.

    Args:
        verse_id: Unique verse identifier (format: {translation}_{book}_{chapter}_{verse}_{suffix})
        session: Neo4j session (injected)

    Returns:
        ParallelsResponse with CVK and list of renditions

    Response Format:
        ```json
        {
          "cvk": "43:3:16:",
          "renditions": [
            {
              "verse_id": "ESV_43_3_16_",
              "translation": "ESV",
              "reference": "John 3:16",
              "text": "For God so loved the world..."
            },
            {
              "verse_id": "NIV_43_3_16_",
              "translation": "NIV",
              "reference": "John 3:16",
              "text": "For God so loved the world that..."
            }
          ]
        }
        ```

    Raises:
        HTTPException: 404 if verse not found or not linked in graph

    Graph Query:
        Traverses: Verse -> CV -> Verse (all renditions)
        Returns all verses sharing the same canonical verse (CV) node
    """
    cypher = """
    MATCH (v:Verse {verse_id: $vid})-[:RENDITION_OF]->(cv:CV)
    WITH cv
    MATCH (cv)<-[:RENDITION_OF]-(w:Verse)<-[:HAS_VERSE]-(ch:Chapter)<-[:HAS_CHAPTER]-(b:Book)<-[:HAS_BOOK]-(t:Translation)
    RETURN cv.cvk AS cvk,
           w.verse_id AS verse_id,
           t.code AS translation,
           w.reference AS reference,
           w.text AS text
    ORDER BY translation
    """
    result: AsyncResult = await session.run(cypher, vid=verse_id)
    records = await result.data()

    if not records:
        raise HTTPException(
            status_code=404,
            detail="verse not found or not linked in graph"
        )

    cvk: str = records[0]["cvk"]
    renditions: List[Rendition] = [
        Rendition(
            verse_id=r["verse_id"],
            translation=r["translation"],
            reference=r["reference"],
            text=r["text"],
        )
        for r in records
    ]
    return ParallelsResponse(cvk=cvk, renditions=renditions)


@router.get("/cv/{cvk}/renditions", response_model=ParallelsResponse)
async def renditions_by_cvk(
    cvk: str,
    session: AsyncSession = Depends(get_neo4j_session)
) -> ParallelsResponse:
    """
    Get all verse renditions for a canonical verse key (CVK).

    Retrieves all translation-specific verse renditions for a given canonical
    verse. The CVK format is: "{book}:{chapter}:{verse}:{suffix}"
    (e.g., "43:3:16:" for John 3:16 with no suffix).

    Args:
        cvk: Canonical verse key in format "book:chapter:verse:suffix"
        session: Neo4j session (injected)

    Returns:
        ParallelsResponse with CVK and list of renditions

    Response Format:
        ```json
        {
          "cvk": "1:1:1:",
          "renditions": [
            {
              "verse_id": "ESV_1_1_1_",
              "translation": "ESV",
              "reference": "Genesis 1:1",
              "text": "In the beginning, God created..."
            },
            {
              "verse_id": "NIV_1_1_1_",
              "translation": "NIV",
              "reference": "Genesis 1:1",
              "text": "In the beginning God created..."
            }
          ]
        }
        ```

    Raises:
        HTTPException: 404 if CVK not found in graph

    Graph Query:
        Starts at CV node, traverses to all connected Verse nodes
        Returns all renditions linked to the canonical verse

    Note:
        CVK suffix is empty string ("") for normal verses, or "a", "b", etc.
        for split verses (e.g., some translations split verses differently)
    """
    cypher = """
    MATCH (cv:CV {cvk: $cvk})
    MATCH (cv)<-[:RENDITION_OF]-(w:Verse)<-[:HAS_VERSE]-(ch:Chapter)<-[:HAS_CHAPTER]-(b:Book)<-[:HAS_BOOK]-(t:Translation)
    RETURN cv.cvk AS cvk,
           w.verse_id AS verse_id,
           t.code AS translation,
           w.reference AS reference,
           w.text AS text
    ORDER BY translation
    """
    result: AsyncResult = await session.run(cypher, cvk=cvk)
    records = await result.data()

    if not records:
        raise HTTPException(
            status_code=404,
            detail="cvk not found in graph"
        )

    renditions: List[Rendition] = [
        Rendition(
            verse_id=r["verse_id"],
            translation=r["translation"],
            reference=r["reference"],
            text=r["text"],
        )
        for r in records
    ]
    return ParallelsResponse(cvk=cvk, renditions=renditions)
