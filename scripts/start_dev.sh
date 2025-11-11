#!/bin/bash

# Start Development Environment Script
# English Video Learning Platform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}English Video Learning Platform${NC}"
echo -e "${BLUE}Development Environment Startup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠ .env file not found. Copying from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env file. Please edit it with your API keys!${NC}"
    echo -e "${YELLOW}⚠ Especially add GEMINI_API_KEY for AI features${NC}"
    echo ""
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker is not running!${NC}"
    echo -e "${YELLOW}  Please start Docker Desktop and try again.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker is running${NC}"
echo ""

# Stop existing containers if any
echo -e "${BLUE}Stopping existing containers...${NC}"
docker-compose down

# Pull latest images
echo -e "${BLUE}Pulling latest images...${NC}"
docker-compose pull

# Build custom images
echo -e "${BLUE}Building custom images...${NC}"
docker-compose build

# Start all services
echo -e "${BLUE}Starting all services...${NC}"
docker-compose up -d

echo ""
echo -e "${GREEN}✓ All services started!${NC}"
echo ""

# Wait for services to be healthy
echo -e "${BLUE}Waiting for services to be healthy...${NC}"
sleep 10

# Check service health
echo ""
echo -e "${BLUE}Checking service health...${NC}"
echo ""

# Run health check script if available
if [ -f backend/scripts/check_services.py ]; then
    docker-compose exec backend-api python scripts/check_services.py || true
else
    # Manual checks
    docker-compose ps
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Services are running!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "📊 ${BLUE}Access Points:${NC}"
echo -e "   Frontend:         ${GREEN}http://localhost:3000${NC}"
echo -e "   Backend API:      ${GREEN}http://localhost:8000${NC}"
echo -e "   API Docs:         ${GREEN}http://localhost:8000/docs${NC}"
echo -e "   MinIO Console:    ${GREEN}http://localhost:9001${NC} (minioadmin/minioadmin)"
echo -e "   RabbitMQ Mgmt:    ${GREEN}http://localhost:15672${NC} (guest/guest)"
echo -e "   Flower (Celery):  ${GREEN}http://localhost:5555${NC}"
echo -e "   Elasticsearch:    ${GREEN}http://localhost:9200${NC}"
echo ""
echo -e "🔧 ${BLUE}Useful Commands:${NC}"
echo -e "   View logs:        ${YELLOW}docker-compose logs -f [service]${NC}"
echo -e "   Stop all:         ${YELLOW}docker-compose down${NC}"
echo -e "   Restart service:  ${YELLOW}docker-compose restart [service]${NC}"
echo -e "   Run backend cmd:  ${YELLOW}docker-compose exec backend-api [command]${NC}"
echo ""
echo -e "🎯 ${BLUE}Next Steps:${NC}"
echo -e "   1. Check service health: ${YELLOW}docker-compose exec backend-api python scripts/check_services.py${NC}"
echo -e "   2. Seed test data:       ${YELLOW}docker-compose exec backend-api python scripts/seed_data.py${NC}"
echo -e "   3. Run tests:            ${YELLOW}docker-compose exec backend-api pytest -v${NC}"
echo -e "   4. Create admin user:    See README.md for instructions"
echo ""
echo -e "${GREEN}Happy coding! 🚀${NC}"
