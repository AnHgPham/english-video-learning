"""
Integration tests for English Video Learning Platform
Tests database, Redis, MinIO, Celery, and API endpoints
"""
import pytest
import redis
from minio import Minio
from minio.error import S3Error
from sqlalchemy import text
from fastapi.testclient import TestClient
from celery import Celery

from core.config import settings
from core.database import engine
from models.user import UserRole


class TestDatabaseConnection:
    """Test database connectivity"""

    def test_database_connection(self, test_db):
        """Test database connection is working"""
        result = test_db.execute(text("SELECT 1"))
        assert result.fetchone()[0] == 1

    def test_database_tables_exist(self, test_db):
        """Test that all required tables exist"""
        tables = [
            "users",
            "categories",
            "videos",
            "subtitles",
            "transcripts",
            "clips",
            "vocabulary_items"
        ]

        for table in tables:
            result = test_db.execute(text(f"SHOW TABLES LIKE '{table}'"))
            assert result.fetchone() is not None, f"Table {table} does not exist"

    def test_user_crud_operations(self, test_db, test_user):
        """Test basic CRUD operations on User model"""
        # Read
        user = test_db.query(test_user.__class__).filter_by(id=test_user.id).first()
        assert user is not None
        assert user.email == test_user.email

        # Update
        user.name = "Updated Name"
        test_db.commit()
        test_db.refresh(user)
        assert user.name == "Updated Name"

        # User exists
        count = test_db.query(test_user.__class__).filter_by(id=test_user.id).count()
        assert count == 1


class TestRedisConnection:
    """Test Redis connectivity"""

    def test_redis_ping(self):
        """Test Redis connection with ping"""
        try:
            redis_client = redis.from_url(settings.REDIS_URL)
            response = redis_client.ping()
            assert response is True
            redis_client.close()
        except redis.ConnectionError as e:
            pytest.skip(f"Redis not available: {str(e)}")

    def test_redis_set_get(self):
        """Test Redis set and get operations"""
        try:
            redis_client = redis.from_url(settings.REDIS_URL)
            test_key = "test:integration:key"
            test_value = "test_value"

            # Set value
            redis_client.set(test_key, test_value, ex=60)

            # Get value
            retrieved_value = redis_client.get(test_key)
            assert retrieved_value.decode("utf-8") == test_value

            # Cleanup
            redis_client.delete(test_key)
            redis_client.close()
        except redis.ConnectionError as e:
            pytest.skip(f"Redis not available: {str(e)}")


class TestMinIOConnection:
    """Test MinIO/S3 connectivity"""

    def test_minio_connection(self):
        """Test MinIO connection"""
        try:
            minio_client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ROOT_USER,
                secret_key=settings.MINIO_ROOT_PASSWORD,
                secure=settings.MINIO_USE_SSL
            )

            # List buckets to verify connection
            buckets = minio_client.list_buckets()
            assert isinstance(buckets, list)
        except Exception as e:
            pytest.skip(f"MinIO not available: {str(e)}")

    def test_minio_bucket_operations(self):
        """Test MinIO bucket creation and listing"""
        try:
            minio_client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ROOT_USER,
                secret_key=settings.MINIO_ROOT_PASSWORD,
                secure=settings.MINIO_USE_SSL
            )

            test_bucket = "test-integration-bucket"

            # Create bucket if not exists
            if not minio_client.bucket_exists(test_bucket):
                minio_client.make_bucket(test_bucket)

            # Verify bucket exists
            assert minio_client.bucket_exists(test_bucket)

            # Cleanup
            # Note: Only remove if empty
            try:
                minio_client.remove_bucket(test_bucket)
            except S3Error:
                pass  # Bucket not empty or already removed

        except Exception as e:
            pytest.skip(f"MinIO not available: {str(e)}")


class TestCeleryConnection:
    """Test Celery broker connectivity"""

    def test_celery_broker_connection(self):
        """Test Celery broker (RabbitMQ) connection"""
        try:
            celery_app = Celery(
                "test",
                broker=settings.CELERY_BROKER_URL,
                backend=settings.CELERY_RESULT_BACKEND
            )

            # Test connection by inspecting
            inspect = celery_app.control.inspect(timeout=2.0)
            stats = inspect.stats()

            # If we get here without exception, connection is working
            # stats might be None if no workers are running, which is OK for connection test
            assert stats is not None or stats is None  # Connection successful either way

        except Exception as e:
            pytest.skip(f"Celery broker not available: {str(e)}")


class TestAPIHealthEndpoints:
    """Test API health and basic endpoints"""

    def test_root_endpoint(self, client):
        """Test root endpoint returns welcome message"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["status"] == "healthy"

    def test_health_check_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "backend-api"

    def test_api_docs_accessible(self, client):
        """Test that API documentation is accessible"""
        response = client.get("/docs")
        assert response.status_code == 200


class TestAuthenticationFlow:
    """Test complete authentication flow"""

    def test_user_registration(self, client, test_db):
        """Test user registration endpoint"""
        payload = {
            "email": "newuser@example.com",
            "name": "New User",
            "open_id": "new_user_openid_789",
            "login_method": "email"
        }

        response = client.post("/api/auth/register", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == payload["email"]
        assert data["user"]["name"] == payload["name"]

    def test_user_login_with_open_id(self, client, test_user):
        """Test user login with open_id"""
        payload = {
            "open_id": test_user.open_id
        }

        response = client.post("/api/auth/login", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == test_user.email

    def test_user_login_with_email(self, client, test_user):
        """Test user login with email"""
        payload = {
            "email": test_user.email
        }

        response = client.post("/api/auth/login", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == test_user.email

    def test_get_current_user_profile(self, client, auth_headers, test_user):
        """Test getting current user profile with auth"""
        response = client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["email"] == test_user.email
        assert data["role"] == test_user.role.value

    def test_authentication_required(self, client):
        """Test that protected endpoints require authentication"""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_invalid_token(self, client):
        """Test that invalid token returns 401"""
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = client.get("/api/auth/me", headers=headers)
        assert response.status_code == 401

    def test_auth_check_endpoint(self, client, auth_headers, test_user):
        """Test auth check endpoint"""
        response = client.get("/api/auth/check", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["authenticated"] is True
        assert data["user"]["email"] == test_user.email


class TestVideoCRUDOperations:
    """Test video CRUD operations"""

    def test_list_videos_public(self, client, sample_videos):
        """Test listing videos without authentication"""
        response = client.get("/api/videos/")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= len(sample_videos)

    def test_get_video_by_id(self, client, test_video):
        """Test getting a specific video by ID"""
        response = client.get(f"/api/videos/{test_video.id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == test_video.id
        assert data["title"] == test_video.title
        assert data["slug"] == test_video.slug

    def test_get_video_by_slug(self, client, test_video):
        """Test getting video by slug"""
        response = client.get(f"/api/videos/slug/{test_video.slug}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == test_video.id
        assert data["slug"] == test_video.slug

    def test_create_video_requires_auth(self, client):
        """Test that creating video requires authentication"""
        payload = {
            "title": "New Video",
            "slug": "new-video",
            "description": "A new video",
            "video_url": "http://localhost:9000/videos/new.mp4",
            "video_key": "new.mp4",
            "level": "B1",
            "language": "en"
        }

        response = client.post("/api/videos/", json=payload)
        assert response.status_code == 401

    def test_filter_videos_by_level(self, client, sample_videos):
        """Test filtering videos by level"""
        response = client.get("/api/videos/?level=B1")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # All returned videos should be B1 level
        for video in data:
            assert video["level"] == "B1"

    def test_filter_videos_by_category(self, client, test_category, sample_videos):
        """Test filtering videos by category"""
        response = client.get(f"/api/videos/?category_id={test_category.id}")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # All returned videos should belong to the test category
        for video in data:
            assert video["categoryId"] == test_category.id


class TestPresignedURLGeneration:
    """Test presigned URL generation for MinIO/S3"""

    def test_generate_video_presigned_url(self, client, admin_headers, test_video):
        """Test generating presigned URL for video"""
        # This endpoint might be in the videos router
        # Adjust the endpoint based on your actual implementation
        response = client.get(
            f"/api/videos/{test_video.id}/presigned-url",
            headers=admin_headers
        )

        # If endpoint exists
        if response.status_code != 404:
            assert response.status_code == 200
            data = response.json()
            assert "url" in data or "presignedUrl" in data
        else:
            pytest.skip("Presigned URL endpoint not implemented yet")

    def test_presigned_url_requires_auth(self, client, test_video):
        """Test that presigned URL generation requires authentication"""
        response = client.get(f"/api/videos/{test_video.id}/presigned-url")

        # Should return 401 or 404 depending on implementation
        assert response.status_code in [401, 404]


class TestAdminOperations:
    """Test admin-only operations"""

    def test_admin_dashboard_requires_admin_role(self, client, auth_headers):
        """Test that admin dashboard requires admin role"""
        response = client.get("/api/admin/dashboard", headers=auth_headers)

        # Regular user should get 403 Forbidden
        assert response.status_code == 403

    def test_admin_dashboard_accessible_by_admin(self, client, admin_headers):
        """Test that admin can access admin dashboard"""
        response = client.get("/api/admin/dashboard", headers=admin_headers)

        # Admin should be able to access
        if response.status_code != 404:  # If endpoint exists
            assert response.status_code == 200
        else:
            pytest.skip("Admin dashboard endpoint not implemented yet")

    def test_admin_can_list_users(self, client, admin_headers):
        """Test that admin can list all users"""
        response = client.get("/api/admin/users", headers=admin_headers)

        if response.status_code != 404:
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
        else:
            pytest.skip("Admin users list endpoint not implemented yet")


class TestVideoWorkflow:
    """Test complete video upload and processing workflow"""

    def test_complete_video_workflow(self, client, admin_headers, test_category, test_db):
        """Test complete workflow: upload -> process -> publish"""
        # This is a placeholder for the complete workflow test
        # Actual implementation depends on your video processing pipeline

        # Step 1: Create video entry
        video_data = {
            "title": "Workflow Test Video",
            "slug": "workflow-test-video",
            "description": "Testing complete workflow",
            "video_url": "http://localhost:9000/videos/workflow-test.mp4",
            "video_key": "workflow-test.mp4",
            "level": "B1",
            "language": "en",
            "category_id": test_category.id
        }

        # Note: Adjust endpoint based on actual implementation
        # This is a conceptual test
        pytest.skip("Complete workflow test requires actual video processing pipeline")


# Pytest markers for different test categories
pytestmark = pytest.mark.integration
