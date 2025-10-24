"""Utility helpers for loading retrieval configuration from manifest.json."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional, Literal, Dict

from pydantic import BaseModel, Field

from ..config import settings


class GraphExpansionConfig(BaseModel):
    """Graph-based expansion options sourced from the manifest."""

    enabled: bool = False
    max_per_hit: int = Field(default=0, ge=0, le=50)
    weight: float = Field(default=0.0, ge=0.0)


class FusionConfig(BaseModel):
    """Fusion strategy configuration for hybrid retrieval."""

    method: Literal["rrf", "weighted_sum"] = "rrf"
    k: int = Field(default=60, ge=1)
    weight_vector: Optional[Dict[str, float]] = None
    graph_expansion: GraphExpansionConfig = Field(
        default_factory=GraphExpansionConfig
    )


class HybridConfig(BaseModel):
    """Hybrid retrieval configuration from the manifest."""

    vector_k: int = Field(default=50, ge=1)
    fts_k: int = Field(default=50, ge=1)
    fusion: FusionConfig = Field(default_factory=FusionConfig)


class IndexPlanConfig(BaseModel):
    """Subset of manifest index plan required by the API."""

    hybrid: HybridConfig = Field(default_factory=HybridConfig)


class ManifestConfig(BaseModel):
    """Minimal manifest representation for retrieval configuration."""

    index_plan: IndexPlanConfig = Field(default_factory=IndexPlanConfig)


@lru_cache(maxsize=1)
def load_manifest(path: Optional[str] = None) -> ManifestConfig:
    """Load and validate the manifest file, caching the parsed model."""

    manifest_path = Path(path or settings.MANIFEST_PATH)
    with manifest_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return ManifestConfig.model_validate(data)


def get_hybrid_config() -> HybridConfig:
    """Convenience accessor for the manifest hybrid configuration."""

    return load_manifest().index_plan.hybrid
