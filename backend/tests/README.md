# DivineHaven API Test Suite

Comprehensive pytest test suite for all DivineHaven backend API endpoints.

## Test Coverage

### Endpoint Tests
- **test_verses.py** - Verse and metadata retrieval endpoints
  - GET `/v1/verses/{verse_id}` - Single verse retrieval
  - GET `/v1/verses` - List verses in chapter
  - GET `/v1/verses/translations` - List all translations
  - GET `/v1/verses/books` - List books in translation
  - GET `/v1/verses/chapters` - List chapters in book
  - Route ordering regression tests

- **test_search.py** - Search endpoints (FTS, vector, hybrid)
  - POST `/v1/search/fts` - Full-text search
  - POST `/v1/search/vector` - Semantic vector search
  - POST `/v1/search/hybrid` - Hybrid RRF search

- **test_chunks.py** - Chunk-based semantic search
  - POST `/v1/chunks/search` - Chunk search with filters
  - GET `/v1/chunks/{chunk_id}` - Get chunk by ID

- **test_batch.py** - Batch retrieval operations
  - POST `/v1/batch/verses` - Batch verse retrieval
  - POST `/v1/batch/translations/compare` - Translation comparison
  - POST `/v1/batch/embeddings` - Batch embedding lookup

- **test_assets.py** - Asset management
  - CRUD operations for assets
  - Asset semantic search
  - Asset embedding management
  - Asset-verse linking

- **test_graph.py** - Cross-translation graph queries
  - GET `/v1/graph/parallels/{verse_id}` - Parallel verses
  - GET `/v1/graph/cv/{cvk}/renditions` - Renditions by CVK

- **test_stats.py** - Statistics and analytics
  - GET `/v1/stats/embeddings` - Embedding coverage stats
  - GET `/v1/analytics/overview` - Analytics overview

- **test_health.py** - Health and monitoring
  - GET `/v1/healthz` - Health check
  - GET `/metrics` - Prometheus metrics

## Running Tests

### Install Dependencies
```bash
cd backend
pip install -r requirements.txt
# or with uv:
uv pip install -r requirements.txt
```

### Run All Tests
```bash
pytest tests/
```

### Run with Verbose Output
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_verses.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_verses.py::TestListTranslations -v
```

### Run Specific Test
```bash
pytest tests/test_verses.py::TestListTranslations::test_list_translations_success -v
```

### Run with Coverage Report
```bash
pytest tests/ --cov=backend.app --cov-report=html
```

### Run Tests Matching Pattern
```bash
pytest tests/ -k "translation" -v
```

### Run Tests by Marker
```bash
pytest tests/ -m routes -v
pytest tests/ -m "not slow" -v
```

## Test Organization

### Fixtures (conftest.py)
- `client` - Synchronous TestClient
- `async_client` - Asynchronous AsyncClient
- `db_conn` - Database connection with transaction rollback
- `override_get_pg` - Override dependency for testing
- Sample data fixtures for various models

### Test Classes
Tests are organized into classes by endpoint/functionality:
- Clear test names describing what is being tested
- Arrange-Act-Assert pattern
- Response structure validation
- Edge case testing
- Error handling verification

## Key Test Features

### Route Ordering Tests
Critical regression tests ensure specific routes (like `/translations`, `/books`) are not incorrectly matched by dynamic routes (like `/{verse_id}`).

### List Endpoint Contracts
All list endpoints are tested to ensure they:
- Always return arrays (never 404)
- Handle empty results gracefully
- Support pagination correctly
- Validate query parameters

### API Contract Validation
- Response schema validation
- HTTP status code verification
- Error message format checking
- Data type validation

## Test Database

Tests use transaction rollback to ensure isolation:
- Each test gets a fresh connection
- Changes are automatically rolled back
- No test pollution between runs

## Continuous Integration

These tests are designed to run in CI/CD pipelines:
- Fast execution (routes only)
- No external service mocking required (uses real services)
- Clear failure messages
- Exit codes for automation

## Adding New Tests

When adding new endpoints:
1. Create tests in appropriate file (or new file)
2. Test happy path first
3. Add edge cases and error conditions
4. Verify response structure
5. Test input validation
6. Test pagination if applicable
7. Add regression tests for bugs

## Test Markers

Use markers to organize test runs:
```python
@pytest.mark.unit
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.routes
```

Run marked tests:
```bash
pytest -m unit -v
pytest -m "not slow" -v
```
