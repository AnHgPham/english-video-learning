# Backend Utility Scripts

Utility scripts for development and deployment of the English Video Learning Platform.

## Available Scripts

### 1. check_services.py

Health check script that verifies all Docker services are running correctly.

**Usage:**
```bash
python scripts/check_services.py
# or
./scripts/check_services.py
```

**Checks:**
- MySQL Database connection and version
- Redis Cache connection and version
- RabbitMQ Broker connection
- MinIO Storage connection and bucket status
- Elasticsearch connection and version
- FastAPI Backend health endpoint
- AI Microservices (WhisperX, Semantic Chunker, Smart Clipper)

**Output:**
- Color-coded status for each service (green = healthy, red = failed)
- Detailed error messages for failed services
- Summary of overall system health

**Exit Codes:**
- `0`: All core services healthy
- `1`: Some services failed
- `130`: Interrupted by user

**Example:**
```bash
$ python scripts/check_services.py

============================================================
  English Video Learning Platform - Service Health Check
============================================================

Core Infrastructure:

✓ MySQL Database          [HEALTHY] - MySQL 8.0.36
✓ Redis Cache             [HEALTHY] - Redis 7.2.3
✓ RabbitMQ Broker         [HEALTHY] - RabbitMQ broker
✓ MinIO Storage           [HEALTHY] - 5 buckets (all required buckets exist)
✓ Elasticsearch           [HEALTHY] - Elasticsearch 8.12.0

Backend API:

✓ FastAPI Backend         [HEALTHY] - API status: ok

AI Microservices:

✓ WhisperX                [HEALTHY] - Responding
✓ Semantic Chunker        [HEALTHY] - Responding
✓ Smart Clipper           [HEALTHY] - Responding

============================================================
✓ All core services are healthy!
System is ready for operation.
```

---

### 2. seed_data.py

Database seeding script that populates the database with test data for development.

**Usage:**
```bash
python scripts/seed_data.py
# or
./scripts/seed_data.py
```

**Creates:**
- **2 Users:**
  - Admin: `admin@englishvideo.com` (open_id: `admin_openid_123`)
  - User: `user@englishvideo.com` (open_id: `user_openid_456`)

- **3 Categories:**
  - Movies & TV Shows
  - TED Talks
  - Podcasts

- **5 Sample Videos:**
  - Various levels (A1, A2, B1, B2, C1)
  - Different durations and categories
  - Pre-configured view counts

- **Subtitles:**
  - English and Vietnamese subtitles for each video
  - AI-generated source type

**Features:**
- Idempotent: Can be run multiple times safely
- Warns about existing data
- Creates URLs pointing to MinIO storage
- Colorful output with status indicators

**Example:**
```bash
$ python scripts/seed_data.py

============================================================
  Database Seeding Script - Test Data Population
============================================================

ℹ Connecting to database: localhost:3306/english_video_learning

Creating Users...
✓ Created user: admin@englishvideo.com (admin)
✓ Created user: user@englishvideo.com (user)

Creating Categories...
✓ Created category: Movies & TV Shows
✓ Created category: TED Talks
✓ Created category: Podcasts

Creating Videos...
✓ Created video: Friends - The One Where It All Began (A2)
✓ Created video: TED: The Power of Vulnerability (B2)
✓ Created video: BBC Documentary: Planet Earth (C1)
✓ Created video: Simple English Conversations for Beginners (A1)
✓ Created video: Business English: Job Interview Tips (B1)

Creating Subtitles...
✓ Created 10 subtitles

============================================================
✓ Database seeding completed successfully!

Summary:
  • Users: 2 (1 admin, 1 regular user)
  • Categories: 3
  • Videos: 5
  • Subtitles: 10

Test Credentials:
  Admin: admin@englishvideo.com (open_id: admin_openid_123)
  User:  user@englishvideo.com (open_id: user_openid_456)

Note: These are URLs only. Actual video files need to be uploaded to MinIO.
```

---

## Environment Variables

Both scripts use settings from `core/config.py`, which reads from environment variables or `.env` file.

**Key Variables:**
- `DATABASE_URL`: MySQL connection string
- `REDIS_URL`: Redis connection string
- `CELERY_BROKER_URL`: RabbitMQ connection string
- `MINIO_ENDPOINT`: MinIO server endpoint
- `MINIO_ROOT_USER`: MinIO access key
- `MINIO_ROOT_PASSWORD`: MinIO secret key
- `ELASTICSEARCH_URL`: Elasticsearch endpoint
- `API_URL`: FastAPI backend URL

## Docker Integration

These scripts work with the Docker Compose setup:

```bash
# Start all services
docker-compose up -d

# Wait for services to start
sleep 10

# Check service health
python scripts/check_services.py

# Seed database
python scripts/seed_data.py
```

## Troubleshooting

### "Connection refused" errors
- Ensure Docker services are running: `docker-compose ps`
- Check service logs: `docker-compose logs [service-name]`
- Verify port mappings in `docker-compose.yml`

### "Table doesn't exist" errors
- Run migrations first: `alembic upgrade head`
- Or use FastAPI startup to create tables automatically

### Permission denied when running scripts
```bash
chmod +x scripts/*.py
```

## Development Workflow

1. **Start services:**
   ```bash
   docker-compose up -d
   ```

2. **Check health:**
   ```bash
   python scripts/check_services.py
   ```

3. **Seed data:**
   ```bash
   python scripts/seed_data.py
   ```

4. **Run tests:**
   ```bash
   pytest
   ```

5. **Start development server:**
   ```bash
   python main.py
   ```

## CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml
- name: Check services
  run: python scripts/check_services.py

- name: Seed test data
  run: python scripts/seed_data.py

- name: Run tests
  run: pytest -v
```

## Adding New Scripts

When creating new utility scripts:

1. Add to `scripts/` directory
2. Add shebang: `#!/usr/bin/env python3`
3. Add docstring explaining purpose
4. Make executable: `chmod +x scripts/your_script.py`
5. Update this README with usage instructions
6. Use colored output for better UX (see existing scripts for examples)
