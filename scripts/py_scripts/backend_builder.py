#!/usr/bin/env python3
"""
Divine Haven Backend Infrastructure Builder
Generates complete backend structure with all files and configurations.
"""

import os
from pathlib import Path
from typing import Dict, List


class BackendBuilder:
    """Builds complete backend infrastructure from specifications."""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.structure = {"backend": ["app", "etl", "scripts/db_init"]}

    def create_directory_structure(self):
        """Create all necessary directories."""
        print("[BUILD] Creating directory structure...")

        # Root directories
        for root_dir, subdirs in self.structure.items():
            root_path = self.base_path / root_dir
            root_path.mkdir(exist_ok=True)

            for subdir in subdirs:
                (root_path / subdir).mkdir(parents=True, exist_ok=True)

        print("✓ Directory structure created")

    def write_file(self, path: Path, content: str):
        """Write content to file with proper formatting."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.strip() + "\n", encoding="utf-8")
        print(f"✓ Created: {path}")

    def build_docker_compose(self):
        """Generate docker-compose.yml"""
        content = """version: "3.9"

services:
  db:
    image: timescale/timescaledb-ha:pg17
    container_name: divinehaven-db
    environment:
      POSTGRES_DB: divinehaven
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - db_data:/var/lib/postgresql/data
      - ./scripts/db_init:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d divinehaven"]
      interval: 5s
      timeout: 3s
      retries: 20

  neo4j:
    image: neo4j:5
    container_name: divinehaven-neo4j
    environment:
      NEO4J_AUTH: neo4j/password
      # Enable APOC and (optionally) algorithms if you add the GDS image later
      NEO4J_dbms_security_procedures_unrestricted: apoc.*
      NEO4J_PLUGINS: '["apoc"]'
      # Helpful defaults for dev — tune for prod
      NEO4J_server_memory_heap_initial__size: 1G
      NEO4J_server_memory_heap_max__size: 2G
      NEO4J_dbms_memory_pagecache_size: 1G
    ports:
      - "7474:7474"   # HTTP UI
      - "7687:7687"   # Bolt
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: divinehaven-backend
    depends_on:
      db:
        condition: service_healthy
      neo4j:
        condition: service_started
    environment:
      # Postgres
      DATABASE_URL: postgresql+psycopg://postgres:postgres@db:5432/divinehaven
      # If you use asyncpg, switch to: postgresql+asyncpg://...
      PGVECTOR_DIM: "768"
      # Neo4j
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_USER: neo4j
      NEO4J_PASSWORD: password
      # CORS / App
      APP_ENV: development
      CORS_ORIGINS: http://localhost:5173,http://127.0.0.1:5173
    ports:
      - "8000:8000"
    volumes:
      # Hot-reload in dev; mount backend directory
      - ./backend:/app/backend
    command: >
      uv run uvicorn backend.app.main:app
      --host 0.0.0.0
      --port 8000
      --reload

volumes:
  db_data:
  neo4j_data:
  neo4j_logs:
"""
        self.write_file(self.base_path / "docker-compose.yml", content)

    def build_backend_dockerfile(self):
        """Generate Dockerfile in root directory for backend service"""
        content = """# Slim Python base
FROM python:3.12-slim

WORKDIR /app

# System deps (psycopg, build)
RUN apt-get update && apt-get install -y build-essential curl libpq-dev && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    mv /root/.local/bin/uvx /usr/local/bin/uvx

# Copy project files
COPY uv.lock pyproject.toml ./
COPY backend/ ./backend/

# Install dependencies using uv sync (reads uv.lock properly)
# --frozen = don't update lockfile
# --no-dev = skip dev dependencies
RUN uv sync --frozen --no-dev

EXPOSE 8000

# Use uv run to execute with the virtual environment
CMD ["uv", "run", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
        self.write_file(self.base_path / "Dockerfile.backend", content)

    def build_pyproject_toml(self):
        """Generate pyproject.toml for uv package manager"""
        content = """[project]
name = "divinehaven-backend"
version = "0.1.0"
description = "Biblical text exploration platform with graph and vector search"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "SQLAlchemy>=2.0.35",
    "psycopg[binary]>=3.2.1",
    "neo4j>=5.23.0",
    "python-dotenv>=1.0.1",
    "pydantic>=2.5.3",
    "pydantic-settings>=2.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "httpx>=0.25.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = ["backend"]

[tool.setuptools.package-data]
backend = ["py.typed"]

[tool.black]
line-length = 100
target-version = ["py312"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]
"""
        self.write_file(self.base_path / "pyproject.toml", content)

    def build_etl_requirements(self):
        """Generate backend/etl/requirements.txt (still needed for standalone ETL)"""
        content = """# Note: For Docker, dependencies come from uv.lock in project root
# This file is for running ETL standalone outside Docker

SQLAlchemy>=2.0.35
psycopg[binary]>=3.2.1
neo4j>=5.23.0
python-dotenv>=1.0.1
"""
        self.write_file(
            self.base_path / "backend" / "etl" / "requirements.txt", content
        )

    def build_etl_config(self):
        """Generate backend/etl/config.py"""
        content = """import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/divinehaven",
)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Optional: path to a manifest.json produced by your ingestion runs
MANIFEST_JSON = os.getenv("MANIFEST_JSON", "./manifest.json")
"""
        self.write_file(self.base_path / "backend" / "etl" / "config.py", content)

    def build_pg_client(self):
        """Generate backend/etl/pg_client.py"""
        content = '''from typing import Iterable, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

class PgClient:
    def __init__(self, url: str):
        self.engine: Engine = create_engine(url, future=True)

    def iter_verses(self, batch_size: int = 5000) -> Iterable[Dict[str, Any]]:
        """
        Streams canonical verse records. Assumes your schema:
        translation(id, code, name), book(id, number, name, testament),
        chapter(id, book_id, number), verse(id, chapter_id, number, suffix, text, translation_id)
        AND a generated 'verse_id' (stable string or bigint) surfaced via a view or computed col.
        """
        sql = text("""
            SELECT
              v.id AS verse_pk,
              v.verse_id,                 -- generated stable id
              t.code AS translation,
              b.name AS book_name,
              b.number AS book_number,
              b.testament AS testament,
              c.number AS chapter_number,
              v.number AS verse_number,
              v.suffix,
              v.text
            FROM verse v
            JOIN chapter c ON v.chapter_id = c.id
            JOIN book b ON c.book_id = b.id
            JOIN translation t ON v.translation_id = t.id
            ORDER BY b.number, c.number, v.number, v.suffix
        """)

        with self.engine.connect() as conn:
            result = conn.execution_options(stream_results=True).execute(sql)
            batch = []
            for row in result.mappings():
                batch.append(dict(row))
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
            if batch:
                yield batch

    def list_distinct_references(self) -> Iterable[Dict[str, Any]]:
        """
        Returns canonical references (e.g., 'John 3:16') across translations to build PARALLEL_TO.
        You can also compute reference in Neo4j, but doing it here keeps Cypher simpler.
        """
        sql = text("""
          SELECT DISTINCT
            CONCAT(b.name, ' ', c.number, ':', v.number, COALESCE(NULLIF(v.suffix,''), '')) AS reference
          FROM verse v
          JOIN chapter c ON v.chapter_id = c.id
          JOIN book b ON c.book_id = b.id
          ORDER BY b.number, c.number, v.number, v.suffix
        """)
        with self.engine.connect() as conn:
            return [r[0] for r in conn.execute(sql).all()]
'''
        self.write_file(self.base_path / "backend" / "etl" / "pg_client.py", content)

    def build_neo4j_client(self):
        """Generate backend/etl/neo4j_client.py"""
        content = '''from typing import Dict, Any, Iterable, Tuple
from neo4j import GraphDatabase, Driver

class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self.driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def init_constraints(self):
        cy = [
            "CREATE CONSTRAINT verse_id_unique IF NOT EXISTS FOR (v:Verse) REQUIRE v.verse_id IS UNIQUE",
            "CREATE CONSTRAINT book_unq IF NOT EXISTS FOR (b:Book) REQUIRE (b.name, b.number) IS UNIQUE",
            "CREATE CONSTRAINT chapter_unq IF NOT EXISTS FOR (c:Chapter) REQUIRE (c.book_name, c.number) IS UNIQUE",
            "CREATE INDEX verse_ref IF NOT EXISTS FOR (v:Verse) ON (v.reference)",
            "CREATE INDEX concept_name IF NOT EXISTS FOR (c:Concept) ON (c.name)"
        ]
        with self.driver.session() as s:
            for stmt in cy:
                s.run(stmt)

    def merge_book_chapter_verse_batch(self, batch: Iterable[Dict[str, Any]]):
        """
        Upsert a batch of B/C/V with a single Cypher UNWIND for speed.
        """
        cypher = """
        UNWIND $rows AS r
        MERGE (b:Book {name: r.book_name, number: r.book_number, testament: r.testament})
        MERGE (c:Chapter {book_name: r.book_name, number: r.chapter_number})
          MERGE (b)-[:HAS_CHAPTER]->(c)
        WITH r, c
        MERGE (v:Verse {verse_id: r.verse_id})
          ON CREATE SET v.reference = r.reference,
                        v.translation = r.translation,
                        v.text = r.text
          ON MATCH  SET v.reference = r.reference,
                        v.translation = r.translation,
                        v.text = r.text
        MERGE (c)-[:HAS_VERSE]->(v)
        """
        rows = []
        for r in batch:
            # e.g., "John 3:16a" if suffix exists
            suffix = r.get("suffix") or ""
            reference = f'{r["book_name"]} {r["chapter_number"]}:{r["verse_number"]}{suffix}'
            rows.append({
                "book_name": r["book_name"],
                "book_number": r["book_number"],
                "testament": r["testament"],
                "chapter_number": r["chapter_number"],
                "verse_id": r["verse_id"],
                "translation": r["translation"],
                "text": r["text"],
                "reference": reference
            })
        with self.driver.session() as s:
            s.run(cypher, rows=rows)

    def link_parallels_for_reference(self, reference: str):
        """
        Create PARALLEL_TO edges among all Verse nodes sharing the same canonical reference.
        """
        cypher = """
        MATCH (v:Verse {reference: $ref})
        WITH collect(v) AS vv
        UNWIND vv AS a
        UNWIND vv AS b
        WITH a,b WHERE id(a) < id(b)
        MERGE (a)-[:PARALLEL_TO {basis: 'canonical_ref'}]->(b)
        """
        with self.driver.session() as s:
            s.run(cypher, ref=reference)
'''
        self.write_file(self.base_path / "backend" / "etl" / "neo4j_client.py", content)

    def build_seed_graph(self):
        """Generate backend/etl/seed_graph.py"""
        content = """import json
from pathlib import Path
from typing import Optional

from config import DATABASE_URL, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, MANIFEST_JSON
from pg_client import PgClient
from neo4j_client import Neo4jClient

def read_manifest(path: str) -> Optional[dict]:
    p = Path(path)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None

def main():
    manifest = read_manifest(MANIFEST_JSON)
    if manifest:
        print(f"[seed] Using manifest summary: {manifest.get('summary','(no summary)')}")

    pg = PgClient(DATABASE_URL)
    g = Neo4jClient(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    print("[seed] Ensuring constraints & indexes…")
    g.init_constraints()

    print("[seed] Upserting Books/Chapters/Verses in batches…")
    for i, batch in enumerate(pg.iter_verses(batch_size=5000), start=1):
        g.merge_book_chapter_verse_batch(batch)
        print(f"[seed] Upserted batch {i} ({len(batch)} rows)")

    print("[seed] Linking cross-translation PARALLEL_TO edges…")
    for ref in pg.list_distinct_references():
        g.link_parallels_for_reference(ref)

    g.close()
    print("[seed] Done.")

if __name__ == "__main__":
    main()
"""
        self.write_file(self.base_path / "backend" / "etl" / "seed_graph.py", content)

    def build_app_main(self):
        """Generate backend/app/main.py (minimal FastAPI skeleton)"""
        content = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="Divine Haven API",
    description="Biblical text exploration with graph and vector search",
    version="0.1.0"
)

# CORS configuration
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Divine Haven API",
        "version": "0.1.0",
        "status": "running"
    }

@app.get("/healthz")
async def health_check():
    return {"status": "healthy"}

# TODO: Add routes for:
# - GET /translations
# - GET /verses/{ref}
# - POST /search/semantic
# - POST /search/graph
# - POST /search/hybrid
"""
        self.write_file(self.base_path / "backend" / "app" / "main.py", content)

    def build_app_init(self):
        """Generate backend/app/__init__.py"""
        content = '''"""Divine Haven FastAPI Application"""
'''
        self.write_file(self.base_path / "backend" / "app" / "__init__.py", content)

    def build_etl_init(self):
        """Generate backend/etl/__init__.py"""
        content = '''"""ETL modules for Divine Haven"""
'''
        self.write_file(self.base_path / "backend" / "etl" / "__init__.py", content)

    def build_env_example(self):
        """Generate .env.example"""
        content = """# Database Configuration
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/divinehaven
PGVECTOR_DIM=768

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Application Configuration
APP_ENV=development
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# ETL Configuration
MANIFEST_JSON=./manifest.json
"""
        self.write_file(self.base_path / ".env.example", content)

    def build_gitignore(self):
        """Generate .gitignore"""
        content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/
env/
.venv/

# uv
.uv/
uv.lock

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Environment variables
.env
.env.local

# Docker
docker-compose.override.yml

# Logs
*.log
logs/

# Database
*.db
*.sqlite3

# Neo4j
neo4j_data/
neo4j_logs/

# OS
.DS_Store
Thumbs.db
"""
        self.write_file(self.base_path / ".gitignore", content)

    def build_readme(self):
        """Generate README.md"""
        content = """# Divine Haven Backend

Biblical text exploration platform with graph and vector search capabilities.

## Architecture

- **FastAPI** - REST API backend
- **TimescaleDB (PostgreSQL 17)** - Relational storage with pgvector for semantic search
- **Neo4j 5** - Graph database for relationship analysis
- **uv** - Ultra-fast Python package manager

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for local development)
- uv package manager (for local development)

### Setup

1. **Clone and navigate to project:**
   ```bash
   cd divine-haven
   ```

2. **Copy environment variables:**
   ```bash
   cp .env.example .env
   ```

3. **Start services:**
   ```bash
   docker compose up -d
   ```

4. **Run ETL to seed graph database:**
   ```bash
   docker exec -it divinehaven-backend bash
   python etl/seed_graph.py
   ```

### Access Points

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474
- **PostgreSQL**: localhost:5432

## Development

### Local Development Setup with uv

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies from uv.lock
uv pip install -r uv.lock

# Or sync the entire environment
uv sync
```

### Run API locally

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Run ETL locally

```bash
cd backend/etl
# If uv is installed globally, dependencies come from project root
python seed_graph.py

# Otherwise, use standalone requirements
pip install -r requirements.txt
python seed_graph.py
```

### Adding Dependencies

```bash
# Add a package
uv add <package-name>

# Add a dev dependency
uv add --dev <package-name>

# Update all dependencies
uv lock --upgrade
```

## Project Structure

```
.
├── pyproject.toml          # Project metadata and dependencies
├── uv.lock                 # Locked dependencies (auto-generated)
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py           # FastAPI application
│   ├── etl/
│   │   ├── __init__.py
│   │   ├── config.py         # ETL configuration
│   │   ├── pg_client.py      # PostgreSQL client
│   │   ├── neo4j_client.py   # Neo4j client
│   │   ├── seed_graph.py     # Main ETL script
│   │   └── requirements.txt  # Standalone ETL deps
│   └── Dockerfile
├── scripts/
│   └── db_init/              # Database initialization scripts
├── docker-compose.yml
├── .env.example
└── README.md
```

## Why uv?

uv is 10-100x faster than pip and provides:
- **Lightning-fast** dependency resolution and installation
- **Reliable** lockfile-based dependency management
- **Compatible** with pip and existing Python tooling
- **Built-in** virtual environment management

## ETL Process

The ETL pipeline:

1. Reads verses from PostgreSQL (with translations, books, chapters)
2. Creates Neo4j nodes: `Book`, `Chapter`, `Verse`
3. Creates relationships: `HAS_CHAPTER`, `HAS_VERSE`
4. Links parallel verses across translations with `PARALLEL_TO` edges

The process is **idempotent** - safe to run multiple times.

## Docker Notes

The Dockerfile uses uv for dependency installation, which dramatically speeds up image builds:
- First build: Installs uv and all dependencies
- Subsequent builds: Layer caching keeps builds fast
- Production: Uses `uv pip install --system` for system-wide packages

## Next Steps

- [ ] Add FastAPI routes for translations, verses, search
- [ ] Implement semantic search with pgvector
- [ ] Add graph traversal queries
- [ ] Create hybrid search combining vector + graph
- [ ] Add Strong's concordance and lexicon integration
- [ ] Implement timeline events and places

## License

Proprietary - All rights reserved
"""
        self.write_file(self.base_path / "README.md", content)

    def build_makefile(self):
        """Generate Makefile for common operations"""
        content = """.PHONY: help build up down restart logs etl clean

help:
	@echo "Divine Haven - Available Commands:"
	@echo "  make build    - Build Docker images"
	@echo "  make up       - Start all services"
	@echo "  make down     - Stop all services"
	@echo "  make restart  - Restart all services"
	@echo "  make logs     - Follow logs"
	@echo "  make etl      - Run ETL seed script"
	@echo "  make clean    - Remove volumes and containers"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

etl:
	docker exec -it divinehaven-backend python etl/seed_graph.py

clean:
	docker compose down -v
	rm -rf neo4j_data neo4j_logs
"""
        self.write_file(self.base_path / "Makefile", content)

    def build_all(self):
        """Execute complete build process."""
        print("\n" + "=" * 60)
        print("Divine Haven Backend Infrastructure Builder")
        print("=" * 60 + "\n")

        self.create_directory_structure()

        print("\n[BUILD] Generating configuration files...")
        self.build_docker_compose()
        self.build_env_example()
        self.build_gitignore()
        self.build_pyproject_toml()

        print("\n[BUILD] Generating backend files...")
        self.build_backend_dockerfile()
        self.build_app_init()
        self.build_app_main()

        print("\n[BUILD] Generating ETL files...")
        self.build_etl_init()
        self.build_etl_requirements()
        self.build_etl_config()
        self.build_pg_client()
        self.build_neo4j_client()
        self.build_seed_graph()

        print("\n[BUILD] Generating documentation...")
        self.build_readme()
        self.build_makefile()

        print("\n" + "=" * 60)
        print("✓ BUILD COMPLETE!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Ensure uv.lock exists in project root (or run 'uv lock')")
        print("  2. Review generated files")
        print("  3. Copy .env.example to .env and customize")
        print("  4. Run: docker compose up -d")
        print("  5. Run: make etl")
        print("\nFor help: make help")
        print("\nNote: The Dockerfile expects uv.lock in the project root.")
        print("=" * 60 + "\n")


def main():
    """Entry point for the builder script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Build Divine Haven backend infrastructure"
    )
    parser.add_argument(
        "--path",
        "-p",
        default=".",
        help="Base path for project (default: current directory)",
    )

    args = parser.parse_args()

    builder = BackendBuilder(base_path=args.path)
    builder.build_all()


if __name__ == "__main__":
    main()
