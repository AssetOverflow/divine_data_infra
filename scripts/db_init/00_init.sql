-- DivineHaven — one-shot init (Postgres 17 + TimescaleDB + pgvector + pgvectorscale optional)

-------------------------------
-- Extensions
-------------------------------
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-------------------------------
-- Core schema
-------------------------------

-- Translations
CREATE TABLE IF NOT EXISTS translation (
  translation_code TEXT PRIMARY KEY,
  language        TEXT,
  format          TEXT NOT NULL,
  source_version  TEXT NOT NULL,
  created_at      TIMESTAMPTZ DEFAULT now()
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

DROP TABLE IF EXISTS verse CASCADE;

-- Verses
CREATE TABLE verse (
  translation_code TEXT NOT NULL,
  book_number      INT  NOT NULL,
  chapter_number   INT  NOT NULL,
  verse_number     INT  NOT NULL,
  -- make suffix not null with empty default so it can be part of PK
  suffix           TEXT NOT NULL DEFAULT '',
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
  PRIMARY KEY (translation_code, book_number, chapter_number, verse_number, suffix),
  UNIQUE (verse_id)
);

-- -- Backfill guard: ensure UNIQUE(verse_id) exists even if table pre-existed
-- DO $$
-- BEGIN
--   IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'verse_verse_id_unique') THEN
--     ALTER TABLE verse ADD CONSTRAINT verse_verse_id_unique UNIQUE (verse_id);
--   END IF;
-- END $$;

-- Lexical search
CREATE INDEX IF NOT EXISTS verse_text_gin
  ON verse USING GIN (to_tsvector('simple', text));

-- Embeddings: verse-level (2560-D)
CREATE TABLE IF NOT EXISTS verse_embedding (
  verse_id        TEXT PRIMARY KEY REFERENCES verse(verse_id) ON DELETE CASCADE,
  embedding       vector(768),
  embedding_model TEXT NOT NULL,
  embedding_dim   INT  NOT NULL,
  embedding_ts    TIMESTAMPTZ DEFAULT now(),
  labels          SMALLINT[],   -- optional label set for filtered ANN (e.g., lang/testament/book/translation)
  metadata        JSONB
);

-- Embeddings: sliding chunks (2560-D)
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
  labels           SMALLINT[],  -- optional label set for filtered ANN
  metadata         JSONB
);

-- Assets + embeddings (2560-D)
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

-- Run manifest registry
CREATE TABLE IF NOT EXISTS run_manifest (
  run_id     TEXT PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT now(),
  manifest   JSONB NOT NULL
);

-------------------------------
-- trigram for substring/fuzzy search; unaccent at query-time or in an expression index
-------------------------------

CREATE INDEX IF NOT EXISTS verse_text_trgm ON verse USING GIN (text gin_trgm_ops);

-------------------------------
-- ANN indexes (vectorscale > pgvector HNSW > IVFFlat)
-------------------------------
DO $$
DECLARE
  have_vectorscale BOOLEAN := EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vectorscale');
  have_hnsw       BOOLEAN := EXISTS (SELECT 1 FROM pg_am WHERE amname = 'hnsw');
BEGIN
  IF have_vectorscale THEN
    -- DiskANN with SBQ; includes labels column for fast pre-filter (labels can be NULL)
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
    -- pgvector >= 0.6
    EXECUTE $I$
      CREATE INDEX IF NOT EXISTS verse_embedding_embedding_hnsw
      ON verse_embedding USING hnsw (embedding vector_cosine_ops);
    $I$;
    EXECUTE $I$
      CREATE INDEX IF NOT EXISTS chunk_embedding_embedding_hnsw
      ON chunk_embedding USING hnsw (embedding vector_cosine_ops);
    $I$;
    EXECUTE $I$
      CREATE INDEX IF NOT EXISTS asset_embedding_embedding_hnsw
      ON asset_embedding USING hnsw (embedding vector_cosine_ops);
    $I$;

  ELSE
    -- Fallback: IVFFlat (older pgvector). Tune lists as needed.
    EXECUTE $I$
      CREATE INDEX IF NOT EXISTS verse_embedding_embedding_ivfflat
      ON verse_embedding USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
    $I$;
    EXECUTE $I$
      CREATE INDEX IF NOT EXISTS chunk_embedding_embedding_ivfflat
      ON chunk_embedding USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
    $I$;
    EXECUTE $I$
      CREATE INDEX IF NOT EXISTS asset_embedding_embedding_ivfflat
      ON asset_embedding USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
    $I$;
  END IF;
END $$;

-- Helpful stats
ANALYZE verse;
ANALYZE verse_embedding;
ANALYZE chunk_embedding;
ANALYZE asset_embedding;
