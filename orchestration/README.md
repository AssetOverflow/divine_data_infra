# DivineHaven Orchestration

This package contains the Dagster project responsible for coordinating the
manifest lifecycle, embedding generation, relational/vector maintenance, and
Neo4j seeding jobs that support the DivineHaven backend. The code is designed to
run locally or inside Docker alongside the existing `docker-compose.backend.yml`
services.

## Layout

```
orchestration/
  README.md              # Project overview and run instructions
  workspace.yaml         # Dagster workspace entrypoint
  dagster.yaml           # Dagster deployment defaults
  __init__.py            # Top-level Definitions for Dagster
  ops.py                 # Ops that call into domain-specific helpers/resources
  jobs.py                # Graph/job wiring for pipelines
  schedules.py           # Cron schedules and job run configuration
  resources.py           # Resource definitions aligned with Docker env vars
```

## Local development

1. Install orchestration dependencies (adds Dagster to the project):
   ```bash
   uv sync
   ```
2. Launch the Dagster webserver pointed at this project:
   ```bash
   uv run dagster dev -w orchestration/workspace.yaml
   ```
3. Use the UI to trigger jobs or inspect schedule status.

## Docker usage

The resources declared in `resources.py` default to the same environment
variables used in `docker-compose.backend.yml`, so the orchestration code can run
in a companion container with the backend stack. Mount this repository and
provide the following variables when running inside Docker:

- `DATABASE_URL` (defaults to the compose DSN)
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- `MANIFEST_PATH` (defaults to `/app/manifest.json`)
- `EMBEDDING_ENDPOINT` (HTTP endpoint for embedding generation service)

Schedules are defined to run in UTC and assume a daily cadence for embeddings,
weekly index maintenance, and nightly graph refreshes. Adjust the cron
expressions in `schedules.py` to match your deployment requirements.
