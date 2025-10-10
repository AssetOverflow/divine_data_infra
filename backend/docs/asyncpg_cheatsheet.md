# Pool sizing & server settings (cheat sheet)

- Uvicorn workers: start with workers = CPU cores (e.g., 4–8). Each process creates its own pool. For asyncpg, a pool of 8–16 per process is usually enough.

- DB timeouts: set statement_timeout (5–10s) and idle_in_transaction_session_timeout in the init callback.

- pgbouncer (optional): for very spiky traffic, put pgbouncer (transaction pooling) in front of Postgres; set pool sizes smaller in the app (e.g., 4–8 per worker).

- TimescaleDB: keep timescaledb.pre/post_restore in mind for restores; no special consideration for read concurrency—Postgres handles it well.
