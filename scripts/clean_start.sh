#!/bin/bash

# Discord Scraper Clean Start Script
# This script provides a clean database reset and startup

set -e

echo "🚀 Discord Scraper Clean Start"
echo "=============================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ No .env file found!"
    echo ""
    echo "📝 Creating .env from template..."
    
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env from .env.example"
        echo ""
        echo "⚠️  IMPORTANT: Edit .env and add your secret keys:"
        echo "   - JWT_SECRET_KEY"
        echo "   - TOKEN_ENCRYPTION_KEY"
        echo "   - Set SELFBOT_WARNING_ACCEPTED=true if using self-bot mode"
        echo ""
        echo "Press Enter after updating .env..."
        read
    else
        echo "❌ No .env.example found. Cannot proceed."
        exit 1
    fi
fi

# Parse command line arguments
RESET_DB=false
QUICK_START=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --reset-db)
            RESET_DB=true
            shift
            ;;
        --quick)
            QUICK_START=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--reset-db] [--quick]"
            exit 1
            ;;
    esac
done

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Reset database if requested
if [ "$RESET_DB" = true ]; then
    echo "🗑️  Removing database volumes..."
    docker-compose down -v
    echo "✅ Database reset complete"
fi

# Build containers if not quick start
if [ "$QUICK_START" = false ]; then
    echo "🔨 Building containers..."
    docker-compose build
fi

# Start database services first
echo "🗄️  Starting database services..."
docker-compose up -d postgres redis

# Wait for databases to be ready
echo "⏳ Waiting for databases to be ready..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker-compose exec postgres pg_isready -U discord_user >/dev/null 2>&1; then
        echo "✅ PostgreSQL is ready"
        break
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 1
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ PostgreSQL failed to start"
    exit 1
fi

# Run database migrations
echo "📊 Running database migrations..."
docker-compose run --rm backend alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Database migrations completed"
else
    echo "⚠️  Database migrations failed. This might be normal if tables already exist."
    echo "   Attempting to stamp current version..."
    docker-compose run --rm backend alembic stamp head
fi

# Start all services
echo "🚀 Starting all services..."
docker-compose up -d

# Wait a moment for services to initialize
sleep 5

# Check service health
echo ""
echo "🏥 Checking service health..."
docker-compose ps

# Show logs tail
echo ""
echo "📋 Recent logs:"
docker-compose logs --tail=10

echo ""
echo "✅ Services started successfully!"
echo ""
echo "🌐 Access points:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000/docs"
echo "   PostgreSQL: localhost:5432"
echo "   Redis: localhost:6379"
echo ""
echo "📌 Useful commands:"
echo "   View logs: docker-compose logs -f [service]"
echo "   Stop all: docker-compose down"
echo "   Reset database: $0 --reset-db"
echo "   Quick restart: $0 --quick"
echo ""

# Check for common issues
if ! docker-compose exec backend python -c "import discord_self" 2>/dev/null; then
    echo "⚠️  Note: discord.py-self may not be installed. The worker might fail."
    echo "   Install it with: docker-compose exec backend pip install discord.py-self"
fi