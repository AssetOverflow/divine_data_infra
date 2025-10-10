"""Test scaffolding helpers for service unit tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

from ..models import (
    Verse,
    VerseLite,
    Book,
    Chapter,
    Translation,
    EmbeddingCoverage,
)


@dataclass
class FakeVerseRepository:
    """In-memory stand-in for :class:`VerseRepository`."""

    verses: Dict[str, Verse] = field(default_factory=dict)
    chapter_verses: Dict[Tuple[str, int, int], List[VerseLite]] = field(default_factory=dict)
    translations: List[Translation] = field(default_factory=list)
    books: Dict[str, List[Book]] = field(default_factory=dict)
    chapters: Dict[Tuple[str, int], List[Chapter]] = field(default_factory=dict)

    async def get_by_id(self, verse_id: str) -> Verse | None:
        return self.verses.get(verse_id)

    async def list_chapter_verses(
        self,
        *,
        translation: str,
        book_number: int,
        chapter_number: int,
        limit: int,
        offset: int,
    ) -> List[VerseLite]:
        key = (translation, book_number, chapter_number)
        items = self.chapter_verses.get(key, [])
        return items[offset : offset + limit]

    async def list_translations(self) -> List[Translation]:
        return list(self.translations)

    async def list_books(self, *, translation: str) -> List[Book]:
        return list(self.books.get(translation, []))

    async def list_chapters(
        self,
        *,
        translation: str,
        book_number: int,
    ) -> List[Chapter]:
        return list(self.chapters.get((translation, book_number), []))


@dataclass
class FakeStatsRepository:
    """In-memory repository for stats service tests."""

    coverage: List[EmbeddingCoverage] = field(default_factory=list)

    async def embedding_coverage(self) -> List[EmbeddingCoverage]:
        return list(self.coverage)


@dataclass
class FakeSearchRepository:
    """In-memory repository for search service tests."""

    fts_total: int = 0
    fts_items: List[dict] = field(default_factory=list)
    vector_result: List[dict] = field(default_factory=list)
    hybrid_result: List[dict] = field(default_factory=list)

    async def search_fts(
        self,
        *,
        dictionary: str,
        query: str,
        translation: str | None,
        limit: int,
        offset: int,
    ) -> Tuple[int, List[dict]]:
        return self.fts_total, list(self.fts_items)

    async def search_vector(
        self,
        *,
        embedding: Sequence[float],
        model: str,
        dim: int,
        translation: str | None,
        limit: int,
    ) -> List[dict]:
        return list(self.vector_result)

    async def search_hybrid(
        self,
        *,
        embedding: Sequence[float] | None,
        model: str,
        dim: int,
        query: str | None,
        dictionary: str,
        translation: str | None,
        fts_k: int,
        vector_k: int,
        k_rrf: int,
        top_k: int,
    ) -> List[dict]:
        return list(self.hybrid_result)
