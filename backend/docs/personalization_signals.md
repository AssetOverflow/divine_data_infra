# Personalization Signal Schema Prototype

## Postgres Entities

```sql
-- Core user profile
CREATE TABLE user_profile (
    user_id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    denomination TEXT,
    spiritual_goal TEXT,
    preferred_translation TEXT,
    timezone TEXT,
    privacy_level TEXT DEFAULT 'standard'
);

-- Long-lived traits and preferences sourced from onboarding
CREATE TABLE user_traits (
    trait_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES user_profile(user_id) ON DELETE CASCADE,
    trait_type TEXT NOT NULL, -- e.g. "learning_style", "content_format"
    trait_value JSONB NOT NULL,
    confidence NUMERIC(3,2) NOT NULL DEFAULT 0.80,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Time-decayed interaction signals captured from product events
CREATE TABLE personalization_events (
    event_id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES user_profile(user_id) ON DELETE SET NULL,
    session_id UUID,
    content_id TEXT NOT NULL,
    content_type TEXT NOT NULL,
    signal_type TEXT NOT NULL, -- e.g. "bookmark", "share", "skip"
    signal_weight NUMERIC(4,3) NOT NULL,
    metadata JSONB,
    occurred_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX personalization_events_user_time_idx
    ON personalization_events (user_id, occurred_at DESC);

-- Rolling aggregates to support personalization models
CREATE MATERIALIZED VIEW user_signal_rollups AS
SELECT
    user_id,
    content_type,
    signal_type,
    COUNT(*) AS event_count,
    SUM(signal_weight) AS total_weight,
    MAX(occurred_at) AS last_seen_at
FROM personalization_events
GROUP BY 1,2,3;
```

## Redis Structures

| Key Pattern | Data Structure | Purpose | TTL |
| --- | --- | --- | --- |
| `session:{session_id}:recent_content` | List (max length 50) | Track the most recent passages viewed in a session for exclusion in recommendations. | 24h |
| `user:{user_id}:embedding` | String (binary/vector) | Cached personalized embedding for fast retrieval reranking. | 6h |
| `user:{user_id}:preferences` | Hash | Snapshot of high-confidence traits (language, tone, notification windows). | 7d |
| `user:{user_id}:signals` | Sorted Set | Event IDs with score = timestamp for deduplication before batch ETL. | 48h |
| `feature_flag:personalization:{user_id}` | String | Enables targeted rollout toggles. | 24h |

## ETL Considerations

1. CDC stream (see Debezium evaluation) publishes `personalization_events` inserts to Kafka for online learning consumers.
2. Nightly job refreshes `user_signal_rollups` and copies results into feature store tables.
3. Redis caches are pre-warmed on login and invalidated whenever profile or trait updates occur.
