-- DivineHaven — Production-Ready Init Script (v2)
-- Postgres 17 + TimescaleDB + pgvector + pgvectorscale
--
-- This script consolidates:
--   - Original 00_init.sql baseline schema
--   - Migration 002: simple_unaccent text search configuration
--   - Migration 007: verse_abs_index for sequential ordering
--   - Migration 009: verse_bucket tables for grouping
--   - Migration 011: search_log TimescaleDB hypertable
--
-- Idempotent: Safe to run multiple times (uses IF NOT EXISTS, CREATE OR REPLACE)

-------------------------------
-- Extensions
-------------------------------
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-------------------------------
-- Core Schema
-------------------------------

-- Translations
CREATE TABLE IF NOT EXISTS translation (
  translation_code TEXT PRIMARY KEY,
  language         TEXT,
  format           TEXT NOT NULL,
  source_version   TEXT NOT NULL,
  created_at       TIMESTAMPTZ DEFAULT now()
);

-- Books
CREATE TABLE IF NOT EXISTS book (
  translation_code TEXT REFERENCES translation(translation_code),
  book_number      INT,
  name             TEXT NOT NULL,
  testament        TEXT CHECK (testament IN ('Old','New')),
  PRIMARY KEY (translation_code, book_number)
);

-- Chapters
CREATE TABLE IF NOT EXISTS chapter (
  translation_code TEXT,
  book_number      INT,
  chapter_number   INT,
  PRIMARY KEY (translation_code, book_number, chapter_number),
  FOREIGN KEY (translation_code, book_number) REFERENCES book(translation_code, book_number)
);

-- Verses
-- Note: If table exists from a previous run, DROP it to ensure clean state
-- (This is safe for fresh deployments; remove DROP in production migrations)
DROP TABLE IF EXISTS verse CASCADE;

CREATE TABLE verse (
  translation_code TEXT NOT NULL,
  book_number      INT  NOT NULL,
  chapter_number   INT  NOT NULL,
  verse_number     INT  NOT NULL,
  suffix           TEXT NOT NULL DEFAULT '',

  -- Generated canonical verse ID
  verse_id         TEXT GENERATED ALWAYS AS (
    translation_code || ':' || book_number || ':' || chapter_number || ':' ||
    verse_number || CASE WHEN suffix = '' THEN '' ELSE '|' || suffix END
  ) STORED,

  text             TEXT NOT NULL,
  words_json       JSONB,
  source_version   TEXT NOT NULL,
  ingest_run_id    TEXT,
  checksum         TEXT,
  created_at       TIMESTAMPTZ DEFAULT now(),

  -- ✨ NEW (from migration 007): Sequential index within translation
  verse_abs_index  BIGINT,

  PRIMARY KEY (translation_code, book_number, chapter_number, verse_number, suffix),
  UNIQUE (verse_id)
);

-- Lexical search indexes
CREATE INDEX IF NOT EXISTS verse_text_gin
  ON verse USING GIN (to_tsvector('simple', text));

CREATE INDEX IF NOT EXISTS verse_text_trgm
  ON verse USING GIN (text gin_trgm_ops);

-- ✨ NEW (from migration 007): Absolute index for sequential verse navigation
CREATE UNIQUE INDEX IF NOT EXISTS verse_abs_index_unq
  ON verse (translation_code, verse_abs_index)
  WHERE verse_abs_index IS NOT NULL;

-- ✨ NEW (from migration 007): Composite locator index
CREATE INDEX IF NOT EXISTS verse_loc_idx
  ON verse (translation_code, book_number, chapter_number, verse_number, suffix);

-------------------------------
-- Text Search Configuration
-- ✨ NEW (from migration 002): Unaccent + simple dictionary
-------------------------------
DO $$
BEGIN
  -- Create custom text search config that applies unaccent
  IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'simple_unaccent') THEN
    CREATE TEXT SEARCH CONFIGURATION simple_unaccent (COPY = simple);
  END IF;
END$$;

-- Clear and recreate mappings to ensure idempotency
DO $$
BEGIN
  DELETE FROM pg_ts_config_map m
  USING pg_ts_config c
  WHERE c.oid = m.mapcfg AND c.cfgname = 'simple_unaccent';

  ALTER TEXT SEARCH CONFIGURATION simple_unaccent
    ADD MAPPING FOR asciiword, asciihword, hword_asciipart, word, hword, hword_part,
                    numhword, numword, email, url, host, sfloat, float, version, file
    WITH unaccent, simple;
END$$;

-- Advanced FTS index with diacritics-friendly search
CREATE INDEX IF NOT EXISTS verse_text_simple_unaccent_gin
  ON verse USING GIN (to_tsvector('simple_unaccent', text));

-- Helpful verse lookup index
CREATE INDEX IF NOT EXISTS verse_lookup_btree
  ON verse (translation_code, book_number, chapter_number);

-------------------------------
-- Accounts & Profiles
-------------------------------

CREATE TABLE IF NOT EXISTS app_user (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  display_name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('member', 'admin')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_profile (
  user_id UUID PRIMARY KEY REFERENCES app_user(id) ON DELETE CASCADE,
  bio TEXT,
  spiritual_background TEXT,
  denominational_identity TEXT,
  study_focus_topics TEXT[] DEFAULT ARRAY[]::TEXT[],
  study_rhythm TEXT,
  guidance_preferences TEXT[] DEFAULT ARRAY[]::TEXT[],
  preferred_translations TEXT[] DEFAULT ARRAY[]::TEXT[],
  prayer_interests TEXT[] DEFAULT ARRAY[]::TEXT[],
  ai_journal_opt_in BOOLEAN DEFAULT TRUE,
  share_preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS user_profile_ai_opt_in_idx
  ON user_profile (ai_journal_opt_in);

-------------------------------
-- AI Conversation History
-------------------------------

CREATE TABLE IF NOT EXISTS ai_conversation (
  conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ai_conversation_user_idx
  ON ai_conversation (user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS ai_message (
  message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES ai_conversation(conversation_id) ON DELETE CASCADE,
  sender_role TEXT NOT NULL CHECK (sender_role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now(),
  sequence BIGSERIAL
);

CREATE INDEX IF NOT EXISTS ai_message_conversation_idx
  ON ai_message (conversation_id, sequence);

-------------------------------
-- Embeddings: Verse-level (768-D)
-------------------------------
CREATE TABLE IF NOT EXISTS verse_embedding (
  verse_id        TEXT PRIMARY KEY REFERENCES verse(verse_id) ON DELETE CASCADE,
  embedding       vector(768),
  embedding_model TEXT NOT NULL,
  embedding_dim   INT  NOT NULL,
  embedding_ts    TIMESTAMPTZ DEFAULT now(),
  labels          SMALLINT[],   -- For filtered ANN (lang, testament, book)
  metadata        JSONB
);

-------------------------------
-- Embeddings: Sliding Chunks (768-D)
-------------------------------
CREATE TABLE IF NOT EXISTS chunk_embedding (
  chunk_id         TEXT PRIMARY KEY,
  translation_code TEXT NOT NULL,
  book_number      INT  NOT NULL,
  chapter_start    INT  NOT NULL,
  verse_start      INT  NOT NULL,
  chapter_end      INT  NOT NULL,
  verse_end        INT  NOT NULL,
  text             TEXT NOT NULL,
  embedding        vector(768),
  embedding_model  TEXT NOT NULL,
  embedding_dim    INT  NOT NULL,
  window_size      INT,
  stride           INT,
  embedding_ts     TIMESTAMPTZ DEFAULT now(),
  labels           SMALLINT[],
  metadata         JSONB
);

-------------------------------
-- Assets & Embeddings (768-D)
-------------------------------
CREATE TABLE IF NOT EXISTS asset (
  asset_id     TEXT PRIMARY KEY,
  media_type   TEXT,
  title        TEXT,
  description  TEXT,
  text_payload TEXT,
  payload_json JSONB,
  license      TEXT,
  origin_url   TEXT,
  created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS asset_embedding (
  asset_id        TEXT PRIMARY KEY REFERENCES asset(asset_id),
  embedding       vector(768),
  embedding_model TEXT NOT NULL,
  embedding_dim   INT  NOT NULL,
  embedding_ts    TIMESTAMPTZ DEFAULT now(),
  metadata        JSONB
);

-- Linking assets to verses/chunks
CREATE TABLE IF NOT EXISTS asset_link (
  asset_id  TEXT REFERENCES asset(asset_id) ON DELETE CASCADE,
  verse_id  TEXT REFERENCES verse(verse_id) ON DELETE CASCADE,
  chunk_id  TEXT,
  relation  TEXT,
  PRIMARY KEY (asset_id, verse_id, chunk_id)
);

-------------------------------
-- Run Manifest Registry
-------------------------------
CREATE TABLE IF NOT EXISTS run_manifest (
  run_id     TEXT PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT now(),
  manifest   JSONB NOT NULL
);

-------------------------------
-- ✨ NEW: Verse Buckets (from migration 009)
-- Groups verses into semantic units (chapters, pericopes, etc.)
-------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'bucket_level') THEN
    CREATE TYPE bucket_level AS ENUM ('chapter', 'paragraph', 'pericope', 'section', 'custom');
  END IF;
END$$;

CREATE TABLE IF NOT EXISTS verse_bucket (
  bucket_id        BIGSERIAL PRIMARY KEY,
  translation_code TEXT NOT NULL,
  level            bucket_level NOT NULL,
  book_number      INT NOT NULL,
  chapter_number   INT,           -- nullable for non-chapter buckets
  label            TEXT,          -- e.g., "John 3", or pericope title
  created_at       TIMESTAMPTZ DEFAULT now(),
  UNIQUE (translation_code, level, book_number, chapter_number)
);

CREATE TABLE IF NOT EXISTS verse_bucket_member (
  bucket_id BIGINT NOT NULL REFERENCES verse_bucket(bucket_id) ON DELETE CASCADE,
  verse_id  TEXT   NOT NULL REFERENCES verse(verse_id) ON DELETE CASCADE,
  ord       INT    NOT NULL,   -- position inside bucket
  PRIMARY KEY (bucket_id, verse_id)
);

CREATE INDEX IF NOT EXISTS vbm_bucket_ord_idx ON verse_bucket_member (bucket_id, ord);
CREATE INDEX IF NOT EXISTS vbm_verse_idx      ON verse_bucket_member (verse_id);

-------------------------------
-- ✨ NEW: Search Logs (from migration 011)
-- TimescaleDB hypertable for search analytics
-------------------------------
CREATE TABLE IF NOT EXISTS search_log (
  ts               TIMESTAMPTZ NOT NULL DEFAULT now(),
  user_id          TEXT,
  translation_code TEXT,
  query            TEXT NOT NULL,
  mode             TEXT,        -- 'ann' | 'fts' | 'hybrid'
  topk             INT,
  latency_ms       INT,
  results          JSONB        -- store ids/scores for offline evals
);

-- Convert to hypertable (safe if already exists)
SELECT create_hypertable(
  'search_log',
  by_range('ts'),
  if_not_exists => TRUE
);

-- Helpful index on recent usage
CREATE INDEX IF NOT EXISTS search_log_ts_idx ON search_log (ts DESC);

-------------------------------
-- ANN Indexes (vectorscale > pgvector HNSW > IVFFlat)
-- Automatically selects best available method
-------------------------------
DO $$
DECLARE
  have_vectorscale BOOLEAN := EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vectorscale');
  have_hnsw        BOOLEAN := EXISTS (SELECT 1 FROM pg_am WHERE amname = 'hnsw');
BEGIN
  IF have_vectorscale THEN
    -- DiskANN with SBQ compression + labels column for pre-filtering
    EXECUTE $I$
      CREATE INDEX IF NOT EXISTS verse_embedding_embedding_ann_idx
      ON verse_embedding USING diskann (embedding vector_cosine_ops, labels)
      WITH (storage_layout = 'memory_optimized');
    $I$;

    EXECUTE $I$
      CREATE INDEX IF NOT EXISTS chunk_embedding_embedding_ann_idx
      ON chunk_embedding USING diskann (embedding vector_cosine_ops, labels)
      WITH (storage_layout = 'memory_optimized');
    $I$;

    EXECUTE $I$
      CREATE INDEX IF NOT EXISTS asset_embedding_embedding_ann_idx
      ON asset_embedding USING diskann (embedding vector_cosine_ops)
      WITH (storage_layout = 'memory_optimized');
    $I$;

  ELSIF have_hnsw THEN
    -- pgvector >= 0.6.0 HNSW
    EXECUTE $I$
      CREATE INDEX IF NOT EXISTS verse_embedding_embedding_hnsw
      ON verse_embedding USING hnsw (embedding vector_cosine_ops)
      WITH (m = 32, ef_construction = 200);
    $I$;

    EXECUTE $I$
      CREATE INDEX IF NOT EXISTS chunk_embedding_embedding_hnsw
      ON chunk_embedding USING hnsw (embedding vector_cosine_ops)
      WITH (m = 32, ef_construction = 200);
    $I$;

    EXECUTE $I$
      CREATE INDEX IF NOT EXISTS asset_embedding_embedding_hnsw
      ON asset_embedding USING hnsw (embedding vector_cosine_ops)
      WITH (m = 32, ef_construction = 200);
    $I$;

  ELSE
    -- Fallback: IVFFlat (older pgvector)
    EXECUTE $I$
      CREATE INDEX IF NOT EXISTS verse_embedding_embedding_ivfflat
      ON verse_embedding USING ivfflat (embedding vector_cosine_ops)
      WITH (lists = 100);
    $I$;

    EXECUTE $I$
      CREATE INDEX IF NOT EXISTS chunk_embedding_embedding_ivfflat
      ON chunk_embedding USING ivfflat (embedding vector_cosine_ops)
      WITH (lists = 100);
    $I$;

    EXECUTE $I$
      CREATE INDEX IF NOT EXISTS asset_embedding_embedding_ivfflat
      ON asset_embedding USING ivfflat (embedding vector_cosine_ops)
      WITH (lists = 100);
    $I$;
  END IF;
END $$;

-------------------------------
-- Gather Statistics
-------------------------------
ANALYZE verse;
ANALYZE verse_embedding;
ANALYZE chunk_embedding;
ANALYZE asset_embedding;
ANALYZE verse_bucket;
ANALYZE verse_bucket_member;
ANALYZE search_log;

-- Success message
DO $$
BEGIN
  RAISE NOTICE '✅ DivineHaven schema initialized successfully';
  RAISE NOTICE '   - Extensions: timescaledb, vector, vectorscale, unaccent, pg_trgm';
  RAISE NOTICE '   - Core tables: translation, book, chapter, verse';
  RAISE NOTICE '   - Embeddings: verse_embedding, chunk_embedding, asset_embedding';
  RAISE NOTICE '   - Features: verse_abs_index, verse_bucket, search_log (hypertable)';
  RAISE NOTICE '   - Text search: simple_unaccent configuration';
  RAISE NOTICE '   - Vector indexes: DiskANN/HNSW/IVFFlat (auto-selected)';
END$$;
