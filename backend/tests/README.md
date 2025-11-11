# Backend Tests

Integration and unit tests for the English Video Learning Platform backend.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up test database (optional, auto-created):
```bash
# The test suite will automatically create a test database
# Default: english_video_learning_test
```

3. Configure environment variables (if needed):
```bash
export TEST_DATABASE_URL="mysql://root:password@localhost:3306/english_video_learning_test"
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run with verbose output
```bash
pytest -v
```

### Run specific test file
```bash
pytest tests/test_integration.py
```

### Run specific test class
```bash
pytest tests/test_integration.py::TestDatabaseConnection
```

### Run specific test function
```bash
pytest tests/test_integration.py::TestDatabaseConnection::test_database_connection
```

### Run tests by marker
```bash
# Run only integration tests
pytest -m integration

# Run only unit tests
pytest -m unit

# Run auth-related tests
pytest -m auth
```

### Run with coverage
```bash
pytest --cov=. --cov-report=html --cov-report=term-missing
```

## Test Categories

- **Integration Tests** (`test_integration.py`):
  - Database connectivity
  - Redis connectivity
  - MinIO/S3 connectivity
  - RabbitMQ/Celery connectivity
  - Elasticsearch connectivity
  - API health endpoints
  - Authentication flow
  - Video CRUD operations
  - Presigned URL generation

## Test Fixtures

Available fixtures in `conftest.py`:

- `test_engine`: Database engine for entire test session
- `test_db`: Database session for each test (auto-rollback)
- `client`: FastAPI test client
- `test_user`: Regular user for testing
- `test_admin`: Admin user for testing
- `user_token`: JWT token for regular user
- `admin_token`: JWT token for admin user
- `auth_headers`: Authorization headers for regular user
- `admin_headers`: Authorization headers for admin user
- `test_category`: Sample category
- `test_video`: Sample video
- `sample_videos`: Multiple sample videos with different levels

## Writing Tests

### Example: Testing authenticated endpoint
```python
def test_protected_endpoint(client, auth_headers):
    response = client.get("/api/protected", headers=auth_headers)
    assert response.status_code == 200
```

### Example: Testing admin endpoint
```python
def test_admin_only_endpoint(client, admin_headers):
    response = client.get("/api/admin/dashboard", headers=admin_headers)
    assert response.status_code == 200
```

### Example: Testing database operations
```python
def test_create_video(test_db, test_user, test_category):
    video = Video(
        title="Test Video",
        slug="test-video",
        video_url="http://example.com/video.mp4",
        video_key="video.mp4",
        level=VideoLevel.B1,
        uploaded_by=test_user.id,
        category_id=test_category.id
    )
    test_db.add(video)
    test_db.commit()

    assert video.id is not None
```

## CI/CD Integration

For GitHub Actions or other CI systems:

```yaml
- name: Run tests
  env:
    DATABASE_URL: mysql://root:root@localhost:3306/test_db
    REDIS_URL: redis://localhost:6379/0
  run: |
    pytest -v --tb=short
```

## Troubleshooting

### Database connection issues
- Ensure MySQL is running
- Check database credentials
- Verify test database exists or can be created

### Redis connection issues
- Ensure Redis is running on port 6379
- Check REDIS_URL in settings

### MinIO connection issues
- Ensure MinIO is running on port 9000
- Verify MINIO_ROOT_USER and MINIO_ROOT_PASSWORD

### Test isolation issues
- Each test gets a fresh database session with auto-rollback
- Use fixtures to set up test data
- Avoid global state modifications
