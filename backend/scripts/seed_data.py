#!/usr/bin/env python3
"""
Database Seeding Script
Populates the database with test data for development
"""
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.config import settings
from models.user import User, UserRole
from models.video import Video, Category, Subtitle, VideoLevel, VideoStatus, SubtitleSource


# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header():
    """Print script header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  Database Seeding Script - Test Data Population{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}\n")


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓{Colors.RESET} {message}")


def print_info(message: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {message}")


def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {message}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}✗{Colors.RESET} {message}")


def create_users(session):
    """Create test users (1 admin, 1 regular user)"""
    print(f"\n{Colors.BOLD}Creating Users...{Colors.RESET}")

    users_data = [
        {
            "open_id": "admin_openid_123",
            "email": "admin@englishvideo.com",
            "name": "Admin User",
            "login_method": "email",
            "role": UserRole.ADMIN
        },
        {
            "open_id": "user_openid_456",
            "email": "user@englishvideo.com",
            "name": "Regular User",
            "login_method": "email",
            "role": UserRole.USER
        }
    ]

    created_users = []

    for user_data in users_data:
        # Check if user already exists
        existing = session.query(User).filter_by(email=user_data["email"]).first()

        if existing:
            print_warning(f"User already exists: {user_data['email']}")
            created_users.append(existing)
        else:
            user = User(**user_data)
            session.add(user)
            session.flush()
            created_users.append(user)
            print_success(f"Created user: {user_data['email']} ({user_data['role'].value})")

    session.commit()
    return created_users


def create_categories(session):
    """Create video categories"""
    print(f"\n{Colors.BOLD}Creating Categories...{Colors.RESET}")

    categories_data = [
        {
            "name": "Movies & TV Shows",
            "slug": "movies-tv-shows",
            "description": "Learn English through popular movies and TV series"
        },
        {
            "name": "TED Talks",
            "slug": "ted-talks",
            "description": "Inspiring talks and presentations from world experts"
        },
        {
            "name": "Podcasts",
            "slug": "podcasts",
            "description": "Engaging podcast episodes for language learning"
        }
    ]

    created_categories = []

    for cat_data in categories_data:
        # Check if category already exists
        existing = session.query(Category).filter_by(slug=cat_data["slug"]).first()

        if existing:
            print_warning(f"Category already exists: {cat_data['name']}")
            created_categories.append(existing)
        else:
            category = Category(**cat_data)
            session.add(category)
            session.flush()
            created_categories.append(category)
            print_success(f"Created category: {cat_data['name']}")

    session.commit()
    return created_categories


def create_videos(session, admin_user, categories):
    """Create sample videos with various levels"""
    print(f"\n{Colors.BOLD}Creating Videos...{Colors.RESET}")

    videos_data = [
        {
            "title": "Friends - The One Where It All Began",
            "slug": "friends-pilot-episode",
            "description": "The pilot episode of the iconic sitcom Friends. Perfect for beginners learning everyday English.",
            "video_key": "videos/friends-s01e01.mp4",
            "thumbnail_key": "thumbnails/friends-s01e01.jpg",
            "duration": 1320,  # 22 minutes
            "level": VideoLevel.A2,
            "language": "en",
            "category_id": categories[0].id,
            "status": VideoStatus.PUBLISHED,
            "view_count": 150
        },
        {
            "title": "TED: The Power of Vulnerability",
            "slug": "ted-brene-brown-vulnerability",
            "description": "Brené Brown discusses the power of vulnerability and human connection.",
            "video_key": "videos/ted-vulnerability.mp4",
            "thumbnail_key": "thumbnails/ted-vulnerability.jpg",
            "duration": 1220,  # 20 minutes
            "level": VideoLevel.B2,
            "language": "en",
            "category_id": categories[1].id,
            "status": VideoStatus.PUBLISHED,
            "view_count": 320
        },
        {
            "title": "BBC Documentary: Planet Earth",
            "slug": "bbc-planet-earth-intro",
            "description": "Stunning nature documentary with David Attenborough's narration.",
            "video_key": "videos/planet-earth-ep01.mp4",
            "thumbnail_key": "thumbnails/planet-earth.jpg",
            "duration": 2940,  # 49 minutes
            "level": VideoLevel.C1,
            "language": "en",
            "category_id": categories[0].id,
            "status": VideoStatus.PUBLISHED,
            "view_count": 89
        },
        {
            "title": "Simple English Conversations for Beginners",
            "slug": "simple-conversations-beginners",
            "description": "Basic everyday conversations to help you start speaking English confidently.",
            "video_key": "videos/simple-conversations.mp4",
            "thumbnail_key": "thumbnails/conversations.jpg",
            "duration": 600,  # 10 minutes
            "level": VideoLevel.A1,
            "language": "en",
            "category_id": categories[2].id,
            "status": VideoStatus.PUBLISHED,
            "view_count": 450
        },
        {
            "title": "Business English: Job Interview Tips",
            "slug": "business-english-interview",
            "description": "Professional English for job interviews and workplace communication.",
            "video_key": "videos/business-interview.mp4",
            "thumbnail_key": "thumbnails/business-interview.jpg",
            "duration": 900,  # 15 minutes
            "level": VideoLevel.B1,
            "language": "en",
            "category_id": categories[2].id,
            "status": VideoStatus.PUBLISHED,
            "view_count": 210
        }
    ]

    created_videos = []

    for video_data in videos_data:
        # Check if video already exists
        existing = session.query(Video).filter_by(slug=video_data["slug"]).first()

        if existing:
            print_warning(f"Video already exists: {video_data['title']}")
            created_videos.append(existing)
        else:
            # Construct URLs
            video_url = f"http://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET_VIDEOS}/{video_data['video_key']}"
            thumbnail_url = f"http://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET_THUMBNAILS}/{video_data['thumbnail_key']}"

            video = Video(
                title=video_data["title"],
                slug=video_data["slug"],
                description=video_data["description"],
                video_url=video_url,
                video_key=video_data["video_key"],
                thumbnail_url=thumbnail_url,
                duration=video_data["duration"],
                level=video_data["level"],
                language=video_data["language"],
                category_id=video_data["category_id"],
                uploaded_by=admin_user.id,
                status=video_data["status"],
                view_count=video_data["view_count"],
                published_at=datetime.utcnow() - timedelta(days=30)
            )

            session.add(video)
            session.flush()
            created_videos.append(video)
            print_success(f"Created video: {video_data['title']} ({video_data['level'].value})")

    session.commit()
    return created_videos


def create_subtitles(session, videos):
    """Create sample subtitles for videos"""
    print(f"\n{Colors.BOLD}Creating Subtitles...{Colors.RESET}")

    subtitle_count = 0

    for video in videos:
        # Add English subtitle
        existing_en = session.query(Subtitle).filter_by(
            video_id=video.id,
            language="en"
        ).first()

        if not existing_en:
            subtitle_key_en = f"subtitles/{video.slug}-en.vtt"
            subtitle_url_en = f"http://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET_SUBTITLES}/{subtitle_key_en}"

            subtitle_en = Subtitle(
                video_id=video.id,
                language="en",
                language_name="English",
                subtitle_url=subtitle_url_en,
                subtitle_key=subtitle_key_en,
                is_default=1,
                source=SubtitleSource.AI_GENERATED
            )
            session.add(subtitle_en)
            subtitle_count += 1

        # Add Vietnamese subtitle
        existing_vi = session.query(Subtitle).filter_by(
            video_id=video.id,
            language="vi"
        ).first()

        if not existing_vi:
            subtitle_key_vi = f"subtitles/{video.slug}-vi.vtt"
            subtitle_url_vi = f"http://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET_SUBTITLES}/{subtitle_key_vi}"

            subtitle_vi = Subtitle(
                video_id=video.id,
                language="vi",
                language_name="Tiếng Việt",
                subtitle_url=subtitle_url_vi,
                subtitle_key=subtitle_key_vi,
                is_default=0,
                source=SubtitleSource.AI_GENERATED
            )
            session.add(subtitle_vi)
            subtitle_count += 1

    session.commit()

    if subtitle_count > 0:
        print_success(f"Created {subtitle_count} subtitles")
    else:
        print_warning("All subtitles already exist")


def seed_database():
    """Main seeding function"""
    print_header()

    try:
        # Create database engine and session
        print_info(f"Connecting to database: {settings.DATABASE_URL.split('@')[-1]}")
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        # Seed data
        users = create_users(session)
        admin_user = next(u for u in users if u.role == UserRole.ADMIN)

        categories = create_categories(session)
        videos = create_videos(session, admin_user, categories)
        create_subtitles(session, videos)

        # Summary
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.GREEN}✓ Database seeding completed successfully!{Colors.RESET}\n")

        print(f"{Colors.BOLD}Summary:{Colors.RESET}")
        print(f"  • Users: {len(users)} (1 admin, 1 regular user)")
        print(f"  • Categories: {len(categories)}")
        print(f"  • Videos: {len(videos)}")
        print(f"  • Subtitles: {session.query(Subtitle).count()}")

        print(f"\n{Colors.BOLD}Test Credentials:{Colors.RESET}")
        print(f"  Admin: {Colors.CYAN}admin@englishvideo.com{Colors.RESET} (open_id: admin_openid_123)")
        print(f"  User:  {Colors.CYAN}user@englishvideo.com{Colors.RESET} (open_id: user_openid_456)")

        print(f"\n{Colors.YELLOW}Note: These are URLs only. Actual video files need to be uploaded to MinIO.{Colors.RESET}\n")

        session.close()
        engine.dispose()

    except Exception as e:
        print_error(f"Seeding failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Entry point"""
    try:
        seed_database()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Seeding interrupted by user.{Colors.RESET}\n")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
