# Makefile for divine_data_infra

STACK_NAME ?= divinehaven-backend
COMPOSE_FILE := docker-compose.backend.yml
SCRIPT_DIR := scripts/db_extras_scripts/bash
COPY_SCRIPT := $(SCRIPT_DIR)/copy_volumes.sh

# Database connection (host mode - outside container)
DB_HOST ?= localhost
DB_PORT ?= 5432
DB_NAME ?= divinehaven
DB_USER ?= postgres
DB_PASSWORD ?= Fr00pzPlz
DSN := postgresql://$(DB_USER):$(DB_PASSWORD)@$(DB_HOST):$(DB_PORT)/$(DB_NAME)

# Ollama settings
OLLAMA_HOST ?= http://localhost:11434
EMBEDDING_MODEL ?= embeddinggemma
EMBEDDING_DIM ?= 768

# Manifest and CLI
MANIFEST_CLI := python3 manifest_cli.py
MANIFEST_FILE := manifest.json
BIBLE_DIR := unified_json_bibles

# Translations to ingest
TRANSLATIONS := ASV ESV KJV NASB NASU NET NIRV NIV NKJV NLT TNK LXX NVI RVR1960

.PHONY: up down build copy restart logs
.PHONY: db-setup db-init db-check db-ingest db-ingest-all db-register-manifest db-embed db-embed-translation db-embed-missing db-full-setup
.PHONY: help

help:
	@echo "Divine Data Infrastructure - Makefile Commands"
	@echo ""
	@echo "Docker Stack:"
	@echo "  make build              Build all Docker images"
	@echo "  make copy               Copy volumes using copy_volumes.sh"
	@echo "  make up                 Start the stack (DB auto-initialized on first run)"
	@echo "  make down               Stop the stack"
	@echo "  make restart            Restart the stack"
	@echo "  make logs               Follow logs"
	@echo ""
	@echo "Database Setup (complete workflow):"
	@echo "  make db-full-setup      Complete DB setup: check → ingest all → register → embed → verify"
	@echo ""
	@echo "Database Setup (individual steps):"
	@echo "  make db-check           Run sanity checks on DB"
	@echo "  make db-ingest-all      Ingest all Bible translations"
	@echo "  make db-register-manifest Register manifest.json into DB"
	@echo "  make db-embed           Generate embeddings for all verses"
	@echo "  make db-embed-missing   Generate embeddings for NKJV, NLT, NVI, RVR1960 only"
	@echo ""
	@echo "Database Helpers:"
	@echo "  make db-ingest TRANS=<code>  Ingest a specific translation (e.g., TRANS=NIV)"
	@echo "  make db-embed-translation TRANS=<code>  Embed a specific translation (e.g., TRANS=NKJV)"
	@echo "  make db-shell           Open psql shell"
	@echo "  make db-wait            Wait for database to be ready"
	@echo "  make db-init-manifest   Create a new manifest.json"
	@echo ""
	@echo "Variables (override with make VAR=value ...):"
	@echo "  DB_HOST=$(DB_HOST)"
	@echo "  DB_PORT=$(DB_PORT)"
	@echo "  DB_USER=$(DB_USER)"
	@echo "  OLLAMA_HOST=$(OLLAMA_HOST)"
	@echo "  EMBEDDING_MODEL=$(EMBEDDING_MODEL)"

# ==========================================
# Docker Stack
# ==========================================

build:
	docker-compose -f $(COMPOSE_FILE) build

copy:
	bash $(COPY_SCRIPT)

up: copy
	docker-compose -f $(COMPOSE_FILE) up -d

down:
	docker-compose -f $(COMPOSE_FILE) down

restart:
	make down && make up

logs:
	docker-compose -f $(COMPOSE_FILE) logs -f

# ==========================================
# Database Setup - Complete Workflow
# ==========================================

db-full-setup: db-wait db-check db-ingest-all db-register-manifest db-migrate-pk db-embed db-check
	@echo ""
	@echo "✅ Complete database setup finished!"
	@echo "   - Database verified ready"
	@echo "   - All translations ingested"
	@echo "   - Manifest registered"
	@echo "   - Primary key migrated"
	@echo "   - Embeddings generated"
	@echo ""
	@echo "💡 Note: Database schema is auto-initialized via Docker entrypoint"
	@echo "   (see scripts/db_init/00_init.v2.sql)"

# ==========================================
# Database Setup - Individual Steps
# ==========================================

db-wait:
	@echo "⏳ Waiting for database container to be healthy..."
	@timeout=60; \
	while [ $$timeout -gt 0 ]; do \
		if docker exec divinehaven-backend-db pg_isready -U $(DB_USER) -d $(DB_NAME) >/dev/null 2>&1; then \
			echo "✅ Database is ready"; \
			exit 0; \
		fi; \
		echo "  Still waiting... ($$timeout seconds left)"; \
		sleep 2; \
		timeout=$$((timeout - 2)); \
	done; \
	echo "❌ Database not ready after 60 seconds"; \
	exit 1

db-check:
	@echo "🔍 Running database sanity checks..."
	$(MANIFEST_CLI) check-ingest --dsn "$(DSN)"
	@echo "✅ Database checks complete"

db-register-manifest:
	@echo "📝 Registering manifest into run_manifest table..."
	@if [ ! -f "$(MANIFEST_FILE)" ]; then \
		echo "❌ Error: $(MANIFEST_FILE) not found. Run 'make db-init-manifest' first or create one manually."; \
		exit 1; \
	fi
	$(MANIFEST_CLI) register-run $(MANIFEST_FILE) "$(DSN)"
	@echo "✅ Manifest registered"

db-ingest-all:
	@echo "📚 Ingesting all Bible translations from $(BIBLE_DIR)..."
	@for trans in $(TRANSLATIONS); do \
		trans_lower=$$(echo "$$trans" | tr '[:upper:]' '[:lower:]'); \
		if [ "$$trans" = "TNK" ]; then \
			pattern="tanakh"; \
		else \
			pattern="$$trans_lower"; \
		fi; \
		file=$$(find $(BIBLE_DIR) -maxdepth 1 -type f -iname "*$$pattern*.json" 2>/dev/null | head -1); \
		if [ -n "$$file" ]; then \
			echo "  Ingesting $$trans from $$file..."; \
			$(MANIFEST_CLI) ingest \
				--json "$$file" \
				--translation "$$trans" \
				--source-version "divine_haven.universal_v1" \
				--dsn "$(DSN)" \
				--batch-size 1000; \
		else \
			echo "  ⚠️  No file found for translation: $$trans (searched for *$$pattern*.json)"; \
		fi; \
	done
	@echo "✅ All translations ingested"

db-ingest:
	@if [ -z "$(TRANS)" ]; then \
		echo "❌ Error: Please specify TRANS=<translation_code> (e.g., make db-ingest TRANS=NIV)"; \
		exit 1; \
	fi
	@trans_lower=$$(echo "$(TRANS)" | tr '[:upper:]' '[:lower:]'); \
	if [ "$(TRANS)" = "TNK" ]; then \
		pattern="tanakh"; \
	else \
		pattern="$$trans_lower"; \
	fi; \
	file=$$(find $(BIBLE_DIR) -maxdepth 1 -type f -iname "*$$pattern*.json" 2>/dev/null | head -1); \
	if [ -z "$$file" ]; then \
		echo "❌ Error: No file found for translation $(TRANS) in $(BIBLE_DIR) (searched for *$$pattern*.json)"; \
		exit 1; \
	fi; \
	echo "📖 Ingesting $(TRANS) from $$file..."; \
	$(MANIFEST_CLI) ingest \
		--json "$$file" \
		--translation "$(TRANS)" \
		--source-version "divine_haven.universal_v1" \
		--dsn "$(DSN)" \
		--batch-size 1000; \
	echo "✅ $(TRANS) ingested"

db-embed:
	@echo "🔮 Generating embeddings for all verses..."
	@echo "   Using model: $(EMBEDDING_MODEL) (dim=$(EMBEDDING_DIM))"
	@echo "   Ollama host: $(OLLAMA_HOST)"
	$(MANIFEST_CLI) embed-verses \
		--dsn "$(DSN)" \
		--model "$(EMBEDDING_MODEL)" \
		--dim $(EMBEDDING_DIM) \
		--api-base "$(OLLAMA_HOST)" \
		--batch 32 \
		--workers 6 \
		--keep-alive 5m \
		--labels \
		--write-mode staging-copy
	@echo "✅ Embeddings generated"

db-embed-translation:
	@if [ -z "$(TRANS)" ]; then \
		echo "❌ Error: Please specify TRANS=<translation_code> (e.g., make db-embed-translation TRANS=NKJV)"; \
		exit 1; \
	fi
	@echo "🔮 Generating embeddings for $(TRANS)..."
	@echo "   Using model: $(EMBEDDING_MODEL) (dim=$(EMBEDDING_DIM))"
	$(MANIFEST_CLI) embed-verses \
		--dsn "$(DSN)" \
		--model "$(EMBEDDING_MODEL)" \
		--dim $(EMBEDDING_DIM) \
		--api-base "$(OLLAMA_HOST)" \
		--translation $(TRANS) \
		--batch 32 \
		--workers 6 \
		--keep-alive 5m \
		--labels \
		--write-mode staging-copy
	@echo "✅ Embeddings generated for $(TRANS)"

db-embed-missing:
	@echo "🔮 Generating embeddings for missing translations only..."
	@echo "   Translations: NKJV NLT NVI RVR1960"
	@echo "   Using model: $(EMBEDDING_MODEL) (dim=$(EMBEDDING_DIM))"
	@echo ""
	@for trans in NKJV NLT NVI RVR1960; do \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		echo "📖 Processing $$trans..."; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		$(MANIFEST_CLI) embed-verses \
			--dsn "$(DSN)" \
			--model "$(EMBEDDING_MODEL)" \
			--dim $(EMBEDDING_DIM) \
			--api-base "$(OLLAMA_HOST)" \
			--translation $$trans \
			--batch 32 \
			--workers 6 \
			--keep-alive 5m \
			--labels \
			--write-mode staging-copy || { \
				echo "❌ Error: Failed to embed $$trans"; \
				exit 1; \
			}; \
		echo "✅ Completed $$trans"; \
		echo ""; \
	done
	@echo "✅ All missing embeddings generated"

# ==========================================
# Database Utilities
# ==========================================

db-shell:
	@echo "🐚 Opening psql shell..."
	@export PGPASSWORD=$(DB_PASSWORD); psql -h $(DB_HOST) -p $(DB_PORT) -U $(DB_USER) -d $(DB_NAME)

db-validate-manifest:
	@if [ ! -f "$(MANIFEST_FILE)" ]; then \
		echo "❌ Error: $(MANIFEST_FILE) not found"; \
		exit 1; \
	fi
	@echo "✅ Validating $(MANIFEST_FILE)..."
	$(MANIFEST_CLI) validate $(MANIFEST_FILE)

db-init-manifest:
	@echo "📋 Initializing a new manifest.json..."
	$(MANIFEST_CLI) init manifest.json \
		--translations NIV ESV NLT KJV NKJV ASV NASU NIRV RVR1960 NVI LXX TNK NASB NET \
		--languages en es el he \
		--embedding-model "$(EMBEDDING_MODEL)" \
		--embedding-dim $(EMBEDDING_DIM) \
		--overwrite
	@echo "✅ Manifest created: manifest.json"

db-migrate-pk:
	@echo "🔧 Migrating verse_embedding to composite primary key..."
	$(MANIFEST_CLI) migrate-embeddings-pk \
		"$(DSN)" \
		--truncate
	@echo "✅ Primary key migrated"