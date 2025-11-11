# 🛠️ Development Guide - English Video Learning Platform

Complete guide for local development setup and workflow.

---

## 📋 Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Development Workflow](#development-workflow)
- [Running Tests](#running-tests)
- [Database Management](#database-management)
- [Debugging](#debugging)
- [Common Issues](#common-issues)

---

## ✅ Prerequisites

### Required
- **Docker Desktop** 4.25+ (with Docker Compose)
- **Git** 2.40+
- **Node.js** 20+ (for local frontend development)
- **Python** 3.11+ (for local backend development)

### Optional
- **NVIDIA GPU** with CUDA 11.8+ (for WhisperX GPU acceleration)
- **Gemini API Key** (for AI translation features)

---

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone <repository-url>
cd english-video-learning
```

### 2. Setup Environment Variables
```bash
cp .env.example .env
# Edit .env and add your API keys:
# - GEMINI_API_KEY (required for AI features)
# - JWT_SECRET (change in production)
```

### 3. Start All Services (Automated)
```bash
chmod +x scripts/start_dev.sh
./scripts/start_dev.sh
```

This will:
- ✅ Check Docker is running
- ✅ Stop existing containers
- ✅ Build all images
- ✅ Start 13 services
- ✅ Verify health status
- ✅ Display access URLs

**Services Started:**
- MySQL, Redis, RabbitMQ, MinIO, Elasticsearch
- Backend API, Celery Workers, Flower
- WhisperX, Semantic Chunker, Smart Clipper
- Frontend (Next.js dev server)

### 4. Verify Services
```bash
docker-compose exec backend-api python scripts/check_services.py
```

Expected output: Green checkmarks ✓ for all services

### 5. Seed Test Data
```bash
docker-compose exec backend-api python scripts/seed_data.py
```

This creates:
- 2 users (admin + regular user)
- 3 categories
- 5 sample videos
- 10 subtitles

**Test Credentials:**
- Admin: `admin@englishvideo.com` (OpenID: `admin_openid_123`)
- User: `user@englishvideo.com` (OpenID: `user_openid_456`)

### 6. Access Applications
- **Frontend:** http://localhost:3000
- **Backend API Docs:** http://localhost:8000/docs
- **Admin Dashboard:** http://localhost:3000/admin

---

## 🔄 Development Workflow

### Backend Development (FastAPI)

#### Local Development (Outside Docker)
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start dev server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Inside Docker (Hot Reload Enabled)
```bash
# Edit files in backend/
# Changes auto-reload thanks to volume mount

# View logs
docker-compose logs -f backend-api

# Run commands
docker-compose exec backend-api python scripts/seed_data.py
```

#### Database Migrations
```bash
# Create new migration
docker-compose exec backend-api alembic revision --autogenerate -m "description"

# Apply migrations
docker-compose exec backend-api alembic upgrade head

# Rollback migration
docker-compose exec backend-api alembic downgrade -1

# View migration history
docker-compose exec backend-api alembic history
```

### Frontend Development (Next.js)

#### Local Development (Outside Docker)
```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
# Access at http://localhost:3000
```

#### Inside Docker
```bash
# Edit files in frontend/src/
# Changes auto-reload via Next.js fast refresh

# View logs
docker-compose logs -f frontend

# Rebuild if needed
docker-compose build frontend
docker-compose restart frontend
```

### Celery Workers

#### View Worker Logs
```bash
docker-compose logs -f celery-worker
```

#### Monitor Tasks (Flower)
Open http://localhost:5555

#### Execute Task Manually
```bash
docker-compose exec backend-api python

>>> from workers.video_pipeline import process_video_pipeline
>>> result = process_video_pipeline.delay(video_id=1)
>>> result.status
'SUCCESS'
```

### AI Microservices

#### Check Service Health
```bash
# WhisperX
curl http://localhost:8001/health

# Semantic Chunker
curl http://localhost:8002/health

# Smart Clipper
curl http://localhost:8003/health
```

#### Test Transcription
```bash
curl -X POST http://localhost:8001/transcribe \
  -F "audio=@test_audio.mp3" \
  -F "language=en"
```

---

## 🧪 Running Tests

### Run All Tests
```bash
docker-compose exec backend-api pytest
```

### Run with Verbose Output
```bash
docker-compose exec backend-api pytest -v
```

### Run Specific Test File
```bash
docker-compose exec backend-api pytest tests/test_integration.py
```

### Run Tests by Category
```bash
# Integration tests only
docker-compose exec backend-api pytest -m integration

# Authentication tests
docker-compose exec backend-api pytest -m auth

# Video CRUD tests
docker-compose exec backend-api pytest -m video

# Slow tests
docker-compose exec backend-api pytest -m slow
```

### Run with Coverage Report
```bash
docker-compose exec backend-api pytest --cov=. --cov-report=html

# View report
open htmlcov/index.html
```

### Frontend Tests
```bash
cd frontend
npm test
```

---

## 💾 Database Management

### Access MySQL Shell
```bash
docker-compose exec mysql mysql -u root -p
# Password: password (from .env)

# Use database
USE english_video_learning;

# Show tables
SHOW TABLES;

# Query data
SELECT * FROM users;
SELECT * FROM videos WHERE status = 'published';
```

### Reset Database
```bash
# Drop all tables
docker-compose exec backend-api alembic downgrade base

# Recreate all tables
docker-compose exec backend-api alembic upgrade head

# Reseed data
docker-compose exec backend-api python scripts/seed_data.py
```

### Backup Database
```bash
docker-compose exec mysql mysqldump -u root -ppassword english_video_learning > backup.sql
```

### Restore Database
```bash
docker-compose exec -T mysql mysql -u root -ppassword english_video_learning < backup.sql
```

---

## 🐛 Debugging

### Backend API Debugging
```bash
# View logs
docker-compose logs -f backend-api

# Enter container shell
docker-compose exec backend-api bash

# Check Python environment
docker-compose exec backend-api python --version
docker-compose exec backend-api pip list

# Test database connection
docker-compose exec backend-api python -c "from core.database import engine; print(engine.connect())"
```

### Frontend Debugging
```bash
# View logs
docker-compose logs -f frontend

# Enter container
docker-compose exec frontend sh

# Check Node.js environment
docker-compose exec frontend node --version
docker-compose exec frontend npm list
```

### MinIO Debugging
```bash
# List buckets
docker-compose exec backend-api python

>>> from services.storage import storage_service
>>> storage_service.minio_client.list_buckets()
```

### Redis Debugging
```bash
docker-compose exec redis redis-cli

# Test connection
PING

# List all keys
KEYS *

# Get value
GET key_name
```

### RabbitMQ Debugging
- Open management UI: http://localhost:15672
- Username: `guest`
- Password: `guest`
- View queues, exchanges, connections

---

## ⚠️ Common Issues

### Issue: Services Won't Start

**Solution:**
```bash
# Check Docker resources
docker system df

# Clean up
docker-compose down -v
docker system prune -a

# Restart Docker Desktop
# Try again
./scripts/start_dev.sh
```

### Issue: Port Already in Use

**Solution:**
```bash
# Find process using port
lsof -i :3000  # or :8000, :3306, etc.

# Kill process
kill -9 <PID>

# Or change port in docker-compose.yml
```

### Issue: Database Connection Failed

**Solution:**
```bash
# Check MySQL is running
docker-compose ps mysql

# View MySQL logs
docker-compose logs mysql

# Restart MySQL
docker-compose restart mysql

# Wait for healthy
docker-compose exec mysql mysqladmin ping -h localhost
```

### Issue: Frontend Can't Connect to Backend

**Solution:**
```bash
# Check backend is running
curl http://localhost:8000/health

# Check CORS settings in backend/core/config.py
# Ensure CORS_ORIGINS includes http://localhost:3000

# Check frontend .env
cat frontend/.env.local
# Should have: NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Issue: Celery Tasks Not Running

**Solution:**
```bash
# Check worker is running
docker-compose ps celery-worker

# View worker logs
docker-compose logs -f celery-worker

# Check RabbitMQ
curl http://localhost:15672/api/overview -u guest:guest

# Restart worker
docker-compose restart celery-worker
```

### Issue: WhisperX Out of Memory

**Solution:**
```bash
# Use CPU fallback instead of GPU
# In ai-services/whisperx/api.py:
# device = "cpu"  # instead of "cuda"

# Or increase Docker memory limit
# Docker Desktop → Settings → Resources → Memory
```

### Issue: MinIO Access Denied

**Solution:**
```bash
# Recreate buckets
docker-compose exec backend-api python

>>> from services.storage import storage_service
>>> for bucket in ['videos', 'subtitles', 'thumbnails', 'audio', 'clips']:
...     storage_service._ensure_bucket_exists(bucket)
```

---

## 📚 Additional Resources

- **Main README:** [README.md](README.md)
- **Testing Guide:** [backend/tests/TESTING_GUIDE.md](backend/tests/TESTING_GUIDE.md)
- **Scripts Guide:** [backend/scripts/README.md](backend/scripts/README.md)
- **API Documentation:** http://localhost:8000/docs (when running)

---

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/amazing-feature`
2. Make changes and test locally
3. Run tests: `docker-compose exec backend-api pytest`
4. Run linter: `docker-compose exec backend-api black .`
5. Commit changes: `git commit -m 'Add amazing feature'`
6. Push branch: `git push origin feature/amazing-feature`
7. Create Pull Request

---

**Happy Development! 🚀**
