"""
Application configuration using Pydantic Settings with .env file support.

This module provides type-safe configuration management for the DivineHaven API.
All settings are loaded from environment variables or the .env file, with
sensible defaults for local development.

Environment Variables:
    DATABASE_URL: PostgreSQL connection string (asyncpg format)
    NEO4J_URI: Neo4j bolt URI (e.g., bolt://localhost:7687)
    NEO4J_USER: Neo4j username
    NEO4J_PASSWORD: Neo4j password
    PGVECTOR_DIM: Embedding vector dimension
    FTS_DICTIONARY: Full-text search dictionary (simple/english)
    HYBRID_K: RRF fusion constant for hybrid search
    VECTOR_MODEL: Default embedding model name
    API_PREFIX: API route prefix
    PAGE_MAX: Maximum page size for pagination
    APP_ENV: Application environment (development/production)
    CORS_ORIGINS: Comma-separated list of allowed CORS origins

Example .env file:
    ```
    DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/divinehaven
    NEO4J_URI=bolt://localhost:7687
    NEO4J_USER=neo4j
    NEO4J_PASSWORD=password
    PGVECTOR_DIM=768
    APP_ENV=development
    ```
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment variable and .env file support.

    All settings have sensible defaults for local development. Override via
    environment variables or .env file for production deployments.

    Attributes:
        DATABASE_URL: PostgreSQL DSN in asyncpg format (postgresql+psycopg://...)
        NEO4J_URI: Neo4j connection URI
        NEO4J_USER: Neo4j authentication username
        NEO4J_PASSWORD: Neo4j authentication password
        PGVECTOR_DIM: Dimension of embedding vectors (must match model)
        FTS_DICTIONARY: PostgreSQL text search dictionary configuration
        HYBRID_K: Reciprocal Rank Fusion constant for hybrid search
        VECTOR_MODEL: Name of embedding model (for reference/validation)
        API_PREFIX: API route prefix (e.g., /v1)
        PAGE_MAX: Maximum number of results per page
        APP_ENV: Application environment identifier
        CORS_ORIGINS: List of allowed CORS origins (parsed from comma-separated string)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore extra environment variables
    )

    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/divinehaven",
        description="PostgreSQL connection string in asyncpg-compatible format",
    )

    # Neo4j Configuration
    NEO4J_URI: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j bolt protocol connection URI",
    )
    NEO4J_USER: str = Field(
        default="neo4j",
        description="Neo4j authentication username",
    )
    NEO4J_PASSWORD: str = Field(
        default="password",
        description="Neo4j authentication password",
    )

    # Vector/Search Configuration
    PGVECTOR_DIM: int = Field(
        default=768,
        description="Embedding vector dimension (must match model output)",
        ge=1,
        le=4096,
    )
    FTS_DICTIONARY: str = Field(
        default="simple",
        description="PostgreSQL text search dictionary (simple/english)",
    )
    HYBRID_K: int = Field(
        default=60,
        description="Reciprocal Rank Fusion constant for hybrid search",
        ge=1,
    )
    VECTOR_MODEL: str = Field(
        default="embeddinggemma",
        description="Embedding model identifier for reference",
    )

    MANIFEST_PATH: str = Field(
        default="manifest.json",
        description="Filesystem path to the active manifest configuration",
    )

    # Auth / Security Configuration
    JWT_SECRET_KEY: str = Field(
        default="",
        description="Secret key used to validate JWT signatures",
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT signing algorithm used for token validation",
    )
    JWT_AUDIENCE: str | None = Field(
        default=None,
        description="Expected JWT audience claim (optional)",
    )
    JWT_ISSUER: str | None = Field(
        default=None,
        description="Expected JWT issuer claim (optional)",
    )

    # Redis / Rate Limiting Configuration
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching and rate limiting",
    )
    REDIS_CLIENT_NAME: str = Field(
        default="divinehaven-backend",
        description="Client name for Redis connection tracking",
    )
    REDIS_MAX_CONNECTIONS: int = Field(
        default=64,
        description="Maximum connections in the Redis connection pool",
        ge=1,
    )
    REDIS_SOCKET_TIMEOUT: float | None = Field(
        default=1.5,
        description="Timeout in seconds for Redis socket operations (None to disable)",
        ge=0,
    )
    REDIS_SOCKET_CONNECT_TIMEOUT: float | None = Field(
        default=1.5,
        description="Timeout in seconds for establishing Redis connections",
        ge=0,
    )
    REDIS_RETRY_ON_TIMEOUT: bool = Field(
        default=True,
        description="Retry Redis commands that time out",
    )
    REDIS_HEALTH_CHECK_INTERVAL: int = Field(
        default=30,
        description="Interval in seconds for Redis health checks",
        ge=0,
    )
    REDIS_SOCKET_KEEPALIVE: bool = Field(
        default=True,
        description="Enable TCP keepalive for Redis connections",
    )
    RATE_LIMIT_ENABLED: bool = Field(
        default=True,
        description="Toggle to enable or disable rate limiting middleware",
    )
    RATE_LIMIT_REQUESTS: int = Field(
        default=100,
        description="Maximum number of requests allowed within the rate limit window",
        ge=1,
    )
    RATE_LIMIT_WINDOW_SECONDS: int = Field(
        default=60,
        description="Window size in seconds for rate limiting buckets",
        ge=1,
    )

    # Cache Configuration
    CACHE_TTL_SECONDS: int = Field(
        default=300,
        description="Default time-to-live for cached entries in seconds",
        ge=0,
    )
    CACHE_MAX_ITEMS: int = Field(
        default=1024,
        description="Maximum number of in-memory cache entries (L1 cache)",
        ge=1,
    )
    CACHE_NAMESPACE: str = Field(
        default="divinehaven",
        description="Namespace prefix for cache keys",
    )

    # Metrics / Observability Configuration
    METRICS_ENABLED: bool = Field(
        default=True,
        description="Toggle to enable Prometheus metrics endpoint and instrumentation",
    )
    METRICS_NAMESPACE: str = Field(
        default="divinehaven",
        description="Prometheus metrics namespace/prefix",
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Application log level for structured logging output",
    )

    # API Configuration
    API_PREFIX: str = Field(
        default="/v1",
        description="API route prefix for versioning",
    )
    PAGE_MAX: int = Field(
        default=200,
        description="Maximum page size for paginated endpoints",
        ge=1,
        le=1000,
    )

    # Application Environment
    APP_ENV: str = Field(
        default="development",
        description="Application environment (development/staging/production)",
    )
    CORS_ORIGINS: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        description="Comma-separated list of allowed CORS origins",
    )

    @field_validator("FTS_DICTIONARY")
    @classmethod
    def validate_fts_dictionary(cls, v: str) -> str:
        """Validate FTS dictionary is a supported type."""
        allowed = {"simple", "english"}
        if v not in allowed:
            raise ValueError(f"FTS_DICTIONARY must be one of {allowed}, got: {v}")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        """
        Normalize PostgreSQL DSN to ensure asyncpg compatibility.

        Converts postgresql:// to postgresql+psycopg:// if needed.
        """
        if v.startswith("postgresql://") and "+" not in v:
            # Plain postgresql:// -> add psycopg driver
            v = v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v

    def get_cors_origins_list(self) -> list[str]:
        """
        Parse CORS_ORIGINS into a list of origin strings.

        Returns:
            List of allowed origin URLs, with whitespace stripped
        """
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


# Global settings instance - import this in other modules
settings = Settings()
