#!/usr/bin/env python3
"""
Service Health Check Script
Checks all Docker services are healthy and running correctly
"""
import sys
import os
from typing import Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
import redis
from minio import Minio
from elasticsearch import Elasticsearch
import requests
import pika
from core.config import settings


# ANSI color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header():
    """Print script header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  English Video Learning Platform - Service Health Check{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}\n")


def print_status(service: str, status: bool, message: str = ""):
    """Print colored status for a service"""
    icon = f"{Colors.GREEN}✓{Colors.RESET}" if status else f"{Colors.RED}✗{Colors.RESET}"
    status_text = f"{Colors.GREEN}HEALTHY{Colors.RESET}" if status else f"{Colors.RED}FAILED{Colors.RESET}"

    print(f"{icon} {Colors.BOLD}{service:<25}{Colors.RESET} [{status_text}]", end="")

    if message:
        print(f" - {message}")
    else:
        print()


def check_mysql() -> Tuple[bool, str]:
    """Check MySQL database connection"""
    try:
        engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            connect_args={'connect_timeout': 5}
        )

        with engine.connect() as conn:
            result = conn.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]
            engine.dispose()
            return True, f"MySQL {version}"

    except Exception as e:
        return False, f"Connection failed: {str(e)[:50]}"


def check_redis() -> Tuple[bool, str]:
    """Check Redis connection"""
    try:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=5
        )
        redis_client.ping()

        info = redis_client.info()
        version = info.get('redis_version', 'unknown')
        redis_client.close()

        return True, f"Redis {version}"

    except Exception as e:
        return False, f"Connection failed: {str(e)[:50]}"


def check_rabbitmq() -> Tuple[bool, str]:
    """Check RabbitMQ connection"""
    try:
        # Parse broker URL
        # Format: amqp://user:pass@host:port/
        broker_url = settings.CELERY_BROKER_URL

        if broker_url.startswith('amqp://'):
            # Extract connection parameters
            import urllib.parse
            parsed = urllib.parse.urlparse(broker_url)

            credentials = pika.PlainCredentials(
                parsed.username or 'guest',
                parsed.password or 'guest'
            )

            parameters = pika.ConnectionParameters(
                host=parsed.hostname or 'localhost',
                port=parsed.port or 5672,
                credentials=credentials,
                connection_attempts=2,
                socket_timeout=5
            )

            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            connection.close()

            return True, "RabbitMQ broker"

        else:
            return False, "Invalid broker URL format"

    except Exception as e:
        return False, f"Connection failed: {str(e)[:50]}"


def check_minio() -> Tuple[bool, str]:
    """Check MinIO/S3 connection"""
    try:
        minio_client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ROOT_USER,
            secret_key=settings.MINIO_ROOT_PASSWORD,
            secure=settings.MINIO_USE_SSL
        )

        # List buckets to verify connection
        buckets = minio_client.list_buckets()
        bucket_count = len(buckets)

        # Check required buckets
        required_buckets = [
            settings.MINIO_BUCKET_VIDEOS,
            settings.MINIO_BUCKET_SUBTITLES,
            settings.MINIO_BUCKET_THUMBNAILS,
            settings.MINIO_BUCKET_AUDIO,
            settings.MINIO_BUCKET_CLIPS
        ]

        existing_bucket_names = [b.name for b in buckets]
        missing_buckets = [b for b in required_buckets if b not in existing_bucket_names]

        if missing_buckets:
            return True, f"{bucket_count} buckets (missing: {', '.join(missing_buckets)})"
        else:
            return True, f"{bucket_count} buckets (all required buckets exist)"

    except Exception as e:
        return False, f"Connection failed: {str(e)[:50]}"


def check_elasticsearch() -> Tuple[bool, str]:
    """Check Elasticsearch connection"""
    try:
        es_client = Elasticsearch(
            [settings.ELASTICSEARCH_URL],
            request_timeout=5
        )

        if es_client.ping():
            info = es_client.info()
            version = info.get('version', {}).get('number', 'unknown')
            return True, f"Elasticsearch {version}"
        else:
            return False, "Ping failed"

    except Exception as e:
        return False, f"Connection failed: {str(e)[:50]}"


def check_fastapi() -> Tuple[bool, str]:
    """Check FastAPI backend health"""
    try:
        response = requests.get(
            f"{settings.API_URL}/health",
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            status = data.get('status', 'unknown')
            return True, f"API status: {status}"
        else:
            return False, f"HTTP {response.status_code}"

    except requests.exceptions.ConnectionError:
        return False, "Connection refused (API not running?)"
    except Exception as e:
        return False, f"Request failed: {str(e)[:50]}"


def check_ai_services() -> dict:
    """Check AI microservices"""
    services = {
        "WhisperX": settings.WHISPERX_API_URL,
        "Semantic Chunker": settings.SEMANTIC_CHUNKER_URL,
        "Smart Clipper": settings.SMART_CLIPPER_URL,
    }

    results = {}

    for name, url in services.items():
        try:
            # Try health endpoint
            health_url = f"{url}/health"
            response = requests.get(health_url, timeout=3)

            if response.status_code == 200:
                results[name] = (True, "Responding")
            else:
                results[name] = (False, f"HTTP {response.status_code}")

        except requests.exceptions.ConnectionError:
            results[name] = (False, "Not running")
        except Exception as e:
            results[name] = (False, f"Error: {str(e)[:30]}")

    return results


def main():
    """Main health check function"""
    print_header()

    # Track overall health
    all_healthy = True

    # Core Infrastructure Services
    print(f"{Colors.BOLD}{Colors.MAGENTA}Core Infrastructure:{Colors.RESET}\n")

    services = [
        ("MySQL Database", check_mysql),
        ("Redis Cache", check_redis),
        ("RabbitMQ Broker", check_rabbitmq),
        ("MinIO Storage", check_minio),
        ("Elasticsearch", check_elasticsearch),
    ]

    for service_name, check_func in services:
        healthy, message = check_func()
        print_status(service_name, healthy, message)
        if not healthy:
            all_healthy = False

    # FastAPI Backend
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}Backend API:{Colors.RESET}\n")
    healthy, message = check_fastapi()
    print_status("FastAPI Backend", healthy, message)
    if not healthy:
        all_healthy = False

    # AI Microservices
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}AI Microservices:{Colors.RESET}\n")
    ai_results = check_ai_services()

    for service_name, (healthy, message) in ai_results.items():
        print_status(service_name, healthy, message)
        if not healthy:
            # AI services are optional, so don't fail overall check
            pass

    # Summary
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")

    if all_healthy:
        print(f"{Colors.BOLD}{Colors.GREEN}✓ All core services are healthy!{Colors.RESET}")
        print(f"{Colors.CYAN}System is ready for operation.{Colors.RESET}\n")
        sys.exit(0)
    else:
        print(f"{Colors.BOLD}{Colors.RED}✗ Some services are not healthy!{Colors.RESET}")
        print(f"{Colors.YELLOW}Please check the failed services above.{Colors.RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Health check interrupted by user.{Colors.RESET}\n")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {str(e)}{Colors.RESET}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
