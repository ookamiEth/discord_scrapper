#!/bin/bash

# Discord Scraper Dashboard - Quick Start Script

echo "🚀 Starting Discord Scraper Dashboard..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed."
    echo "📦 Installing Docker..."
    
    # Check if on macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # Check if Homebrew is installed
        if ! command -v brew &> /dev/null; then
            echo "Installing Homebrew first..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        
        # Install Docker Desktop
        echo "Installing Docker Desktop via Homebrew..."
        brew install --cask docker-desktop 2>/dev/null || {
            echo "⚠️  Brew installation failed. Downloading Docker Desktop manually..."
            curl -o ~/Downloads/Docker.dmg https://desktop.docker.com/mac/main/arm64/196648/Docker.dmg
            hdiutil attach ~/Downloads/Docker.dmg
            cp -R /Volumes/Docker/Docker.app /Applications/
            hdiutil detach /Volumes/Docker
            rm ~/Downloads/Docker.dmg
        }
        
        echo "✅ Docker Desktop installed. Starting it now..."
        open /Applications/Docker.app
        echo "⏳ Waiting for Docker to start (this may take a minute)..."
        while ! docker info > /dev/null 2>&1; do
            sleep 5
        done
    else
        echo "❌ Please install Docker manually for your operating system."
        echo "   Visit: https://www.docker.com/products/docker-desktop/"
        exit 1
    fi
fi

# Check if Docker Desktop is installed but not running
if command -v docker &> /dev/null && ! docker info > /dev/null 2>&1; then
    echo "🐳 Docker is installed but not running."
    if [[ "$OSTYPE" == "darwin"* ]] && [ -d "/Applications/Docker.app" ]; then
        echo "Starting Docker Desktop..."
        open /Applications/Docker.app
        echo "⏳ Waiting for Docker to start (this may take a minute)..."
        while ! docker info > /dev/null 2>&1; do
            sleep 5
        done
    else
        echo "❌ Please start Docker Desktop manually and run this script again."
        exit 1
    fi
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env file with your Discord credentials before continuing."
    echo "   You need:"
    echo "   - DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET (from Discord Developer Portal)"
    echo "   - DISCORD_BOT_TOKEN (your bot token)"
    exit 1
fi

# Build and start containers
echo "🏗️  Building containers..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Run database migrations
echo "📊 Running database migrations..."
docker-compose exec backend alembic upgrade head

echo "✅ Discord Scraper Dashboard is running!"
echo ""
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "📋 To view logs: docker-compose logs -f"
echo "🛑 To stop: docker-compose down"

# Open browser automatically
echo ""
echo "🌐 Opening dashboard in your default browser..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open http://localhost:3000
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:3000
    elif command -v gnome-open &> /dev/null; then
        gnome-open http://localhost:3000
    fi
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    start http://localhost:3000
fi