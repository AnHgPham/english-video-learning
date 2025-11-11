"""
Pytest configuration and fixtures
Provides test database, test client, and common test utilities
"""
import os
import sys
import pytest
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Add parent directory to path to import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from core.database import get_db, Base
from core.config import settings
from core.security import create_access_token
from models.user import User, UserRole
from models.video import Video, Category, VideoLevel, VideoStatus


# Test database URL (use separate test database)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "mysql://root:password@localhost:3306/english_video_learning_test"
)


@pytest.fixture(scope="session")
def test_engine():
    """
    Create test database engine for the entire test session
    """
    engine = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
        echo=False
    )

    # Create test database if it doesn't exist
    db_name = TEST_DATABASE_URL.split('/')[-1]
    temp_url = TEST_DATABASE_URL.rsplit('/', 1)[0]
    temp_engine = create_engine(temp_url)

    with temp_engine.connect() as conn:
        conn.execute(text("COMMIT"))  # Close any open transactions
        # Check if database exists
        result = conn.execute(text(f"SHOW DATABASES LIKE '{db_name}'"))
        if not result.fetchone():
            conn.execute(text(f"CREATE DATABASE {db_name}"))
            print(f"Created test database: {db_name}")

    temp_engine.dispose()

    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Test database tables created")

    yield engine

    # Cleanup: Drop all tables after tests
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    print("Test database cleaned up")


@pytest.fixture(scope="function")
def test_db(test_engine) -> Generator[Session, None, None]:
    """
    Create a new database session for each test
    Automatically rolls back after each test
    """
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(test_db: Session) -> Generator[TestClient, None, None]:
    """
    Create FastAPI test client with test database
    """
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_user(test_db: Session) -> User:
    """
    Create a test user (regular user)
    """
    user = User(
        open_id="test_user_openid_123",
        email="testuser@example.com",
        name="Test User",
        login_method="email",
        role=UserRole.USER
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_admin(test_db: Session) -> User:
    """
    Create a test admin user
    """
    admin = User(
        open_id="test_admin_openid_456",
        email="admin@example.com",
        name="Test Admin",
        login_method="email",
        role=UserRole.ADMIN
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)
    return admin


@pytest.fixture
def user_token(test_user: User) -> str:
    """
    Generate JWT token for test user
    """
    return create_access_token(data={"sub": test_user.id})


@pytest.fixture
def admin_token(test_admin: User) -> str:
    """
    Generate JWT token for test admin
    """
    return create_access_token(data={"sub": test_admin.id})


@pytest.fixture
def auth_headers(user_token: str) -> dict:
    """
    Generate authorization headers for regular user
    """
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(admin_token: str) -> dict:
    """
    Generate authorization headers for admin user
    """
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def test_category(test_db: Session) -> Category:
    """
    Create a test category
    """
    category = Category(
        name="Test Category",
        slug="test-category",
        description="A test category for unit tests"
    )
    test_db.add(category)
    test_db.commit()
    test_db.refresh(category)
    return category


@pytest.fixture
def test_video(test_db: Session, test_user: User, test_category: Category) -> Video:
    """
    Create a test video
    """
    video = Video(
        title="Test Video",
        slug="test-video",
        description="A test video for unit tests",
        video_url="http://localhost:9000/videos/test-video.mp4",
        video_key="test-video.mp4",
        thumbnail_url="http://localhost:9000/thumbnails/test-thumbnail.jpg",
        duration=300,
        level=VideoLevel.B1,
        language="en",
        category_id=test_category.id,
        uploaded_by=test_user.id,
        status=VideoStatus.PUBLISHED,
        view_count=0
    )
    test_db.add(video)
    test_db.commit()
    test_db.refresh(video)
    return video


@pytest.fixture
def sample_videos(test_db: Session, test_user: User, test_category: Category) -> list[Video]:
    """
    Create multiple test videos with different levels
    """
    levels = [VideoLevel.A1, VideoLevel.A2, VideoLevel.B1, VideoLevel.B2, VideoLevel.C1]
    videos = []

    for i, level in enumerate(levels, 1):
        video = Video(
            title=f"Sample Video {i}",
            slug=f"sample-video-{i}",
            description=f"Sample video {i} at level {level.value}",
            video_url=f"http://localhost:9000/videos/sample-{i}.mp4",
            video_key=f"sample-{i}.mp4",
            thumbnail_url=f"http://localhost:9000/thumbnails/sample-{i}.jpg",
            duration=180 + (i * 60),
            level=level,
            language="en",
            category_id=test_category.id,
            uploaded_by=test_user.id,
            status=VideoStatus.PUBLISHED,
            view_count=i * 10
        )
        test_db.add(video)
        videos.append(video)

    test_db.commit()

    for video in videos:
        test_db.refresh(video)

    return videos


# Helper functions for tests
def get_auth_header(token: str) -> dict:
    """Helper to create authorization header"""
    return {"Authorization": f"Bearer {token}"}


def create_test_user_in_db(db: Session, email: str, name: str, role: UserRole = UserRole.USER) -> User:
    """Helper to create a user in the database"""
    user = User(
        open_id=f"test_{email}",
        email=email,
        name=name,
        login_method="email",
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
