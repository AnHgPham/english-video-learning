# Testing & Utilities Quick Reference

Complete guide for testing and utility scripts in the English Video Learning Platform backend.

## Files Created

### Test Files
1. **tests/conftest.py** - Pytest configuration with fixtures
2. **tests/test_integration.py** - Comprehensive integration tests
3. **tests/__init__.py** - Test package marker
4. **tests/README.md** - Detailed testing documentation
5. **pytest.ini** - Pytest configuration file

### Utility Scripts
1. **scripts/check_services.py** - Service health check script
2. **scripts/seed_data.py** - Database seeding script
3. **scripts/__init__.py** - Scripts package marker
4. **scripts/README.md** - Scripts documentation

## Quick Start

### 1. Install Dependencies
```bash
cd /home/user/english-video-learning/backend
pip install -r requirements.txt
```

### 2. Check All Services
```bash
python scripts/check_services.py
```

Expected output:
```
============================================================
  English Video Learning Platform - Service Health Check
============================================================

Core Infrastructure:
✓ MySQL Database          [HEALTHY] - MySQL 8.0.36
✓ Redis Cache             [HEALTHY] - Redis 7.2.3
✓ RabbitMQ Broker         [HEALTHY] - RabbitMQ broker
✓ MinIO Storage           [HEALTHY] - 5 buckets
✓ Elasticsearch           [HEALTHY] - Elasticsearch 8.12.0

Backend API:
✓ FastAPI Backend         [HEALTHY] - API status: ok
```

### 3. Seed Test Data
```bash
python scripts/seed_data.py
```

Creates:
- 2 users (1 admin, 1 regular)
- 3 categories
- 5 sample videos
- 10 subtitles (English + Vietnamese)

### 4. Run Tests
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_integration.py

# Run specific test category
pytest -m integration
pytest -m auth
```

## Test Coverage

### Integration Tests (test_integration.py)

#### TestDatabaseConnection
- `test_database_connection` - Basic MySQL connectivity
- `test_database_tables_exist` - Verify all tables created
- `test_user_crud_operations` - Basic CRUD on User model

#### TestRedisConnection
- `test_redis_ping` - Redis connectivity
- `test_redis_set_get` - Redis operations

#### TestMinIOConnection
- `test_minio_connection` - MinIO connectivity
- `test_minio_bucket_operations` - Bucket operations

#### TestCeleryConnection
- `test_celery_broker_connection` - RabbitMQ/Celery broker check

#### TestAPIHealthEndpoints
- `test_root_endpoint` - Root API endpoint
- `test_health_check_endpoint` - Health check endpoint
- `test_api_docs_accessible` - API documentation access

#### TestAuthenticationFlow
- `test_user_registration` - User registration endpoint
- `test_user_login_with_open_id` - OAuth-style login
- `test_user_login_with_email` - Email-based login
- `test_get_current_user_profile` - Protected endpoint access
- `test_authentication_required` - Auth requirement enforcement
- `test_invalid_token` - Invalid token handling
- `test_auth_check_endpoint` - Auth status check

#### TestVideoCRUDOperations
- `test_list_videos_public` - Public video listing
- `test_get_video_by_id` - Get video by ID
- `test_get_video_by_slug` - Get video by slug
- `test_create_video_requires_auth` - Auth requirement for video creation
- `test_filter_videos_by_level` - Filter by difficulty level
- `test_filter_videos_by_category` - Filter by category

#### TestPresignedURLGeneration
- `test_generate_video_presigned_url` - Generate presigned URLs
- `test_presigned_url_requires_auth` - Auth requirement for presigned URLs

#### TestAdminOperations
- `test_admin_dashboard_requires_admin_role` - Admin role enforcement
- `test_admin_dashboard_accessible_by_admin` - Admin access
- `test_admin_can_list_users` - Admin user listing

## Available Fixtures

From `conftest.py`:

### Database Fixtures
- `test_engine` - Database engine (session scope)
- `test_db` - Database session with auto-rollback (function scope)

### Client Fixture
- `client` - FastAPI TestClient with test database

### User Fixtures
- `test_user` - Regular user (role: USER)
- `test_admin` - Admin user (role: ADMIN)

### Authentication Fixtures
- `user_token` - JWT token for regular user
- `admin_token` - JWT token for admin
- `auth_headers` - Authorization headers for regular user
- `admin_headers` - Authorization headers for admin

### Data Fixtures
- `test_category` - Sample category
- `test_video` - Single sample video
- `sample_videos` - Multiple videos with different levels (A1-C1)

## Service Health Check Details

### Checks Performed
1. **MySQL Database**
   - Connection test
   - Version detection
   - Query execution

2. **Redis Cache**
   - Connection test
   - PING command
   - Version info

3. **RabbitMQ Broker**
   - Connection test
   - Channel creation
   - Broker validation

4. **MinIO Storage**
   - Connection test
   - Bucket listing
   - Required buckets verification (videos, subtitles, thumbnails, audio, clips)

5. **Elasticsearch**
   - Connection test
   - PING command
   - Version info

6. **FastAPI Backend**
   - HTTP health endpoint check
   - Status validation

7. **AI Microservices** (optional)
   - WhisperX STT service
   - Semantic Chunker service
   - Smart Clipper service

### Exit Codes
- `0` - All core services healthy
- `1` - One or more services failed
- `130` - Interrupted by user (Ctrl+C)

## Test Data Details

### Users Created
```
Admin:
  Email: admin@englishvideo.com
  OpenID: admin_openid_123
  Role: ADMIN

Regular User:
  Email: user@englishvideo.com
  OpenID: user_openid_456
  Role: USER
```

### Categories Created
1. Movies & TV Shows - `movies-tv-shows`
2. TED Talks - `ted-talks`
3. Podcasts - `podcasts`

### Videos Created
1. **Friends - The One Where It All Began** (A2, 22min, 150 views)
2. **TED: The Power of Vulnerability** (B2, 20min, 320 views)
3. **BBC Documentary: Planet Earth** (C1, 49min, 89 views)
4. **Simple English Conversations for Beginners** (A1, 10min, 450 views)
5. **Business English: Job Interview Tips** (B1, 15min, 210 views)

Each video includes:
- English subtitle (default)
- Vietnamese subtitle
- Thumbnail URL
- MinIO storage references

## Troubleshooting

### Services Not Running
```bash
# Check Docker services
docker-compose ps

# Start services
docker-compose up -d

# Check logs
docker-compose logs [service-name]
```

### Database Issues
```bash
# Run migrations
alembic upgrade head

# Drop and recreate test database
mysql -u root -p -e "DROP DATABASE IF EXISTS english_video_learning_test; CREATE DATABASE english_video_learning_test;"
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or install specific packages
pip install pytest pytest-asyncio pika
```

### Permission Issues
```bash
# Make scripts executable
chmod +x scripts/*.py
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: password
          MYSQL_DATABASE: english_video_learning_test
        ports:
          - 3306:3306

      redis:
        image: redis:7
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt

      - name: Run tests
        env:
          DATABASE_URL: mysql://root:password@localhost:3306/english_video_learning_test
          REDIS_URL: redis://localhost:6379/0
        run: |
          cd backend
          pytest -v --tb=short
```

## Development Workflow

### Daily Development
```bash
# 1. Start services
docker-compose up -d

# 2. Check health
python scripts/check_services.py

# 3. Seed data (first time or after DB reset)
python scripts/seed_data.py

# 4. Start backend
python main.py

# 5. Run tests (in another terminal)
pytest -v
```

### Before Committing
```bash
# Run all tests
pytest

# Check code style (if using)
black .
flake8 .

# Run specific test categories
pytest -m integration
pytest -m auth
```

### Before Deployment
```bash
# Check all services
python scripts/check_services.py

# Run full test suite
pytest -v --tb=short

# Check coverage
pytest --cov=. --cov-report=term-missing
```

## Additional Resources

- **Full Test Documentation**: `/home/user/english-video-learning/backend/tests/README.md`
- **Scripts Documentation**: `/home/user/english-video-learning/backend/scripts/README.md`
- **Pytest Configuration**: `/home/user/english-video-learning/backend/pytest.ini`
- **API Documentation**: http://localhost:8000/docs (when running)

## Support

For issues or questions:
1. Check service logs: `docker-compose logs [service]`
2. Verify environment variables in `.env`
3. Review error messages from test output
4. Check README files in tests/ and scripts/ directories
