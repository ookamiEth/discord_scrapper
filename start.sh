#!/bin/bash

# Discord Scraper Quick Start Script
# This starts all services and opens the dashboard

echo "🚀 Starting Discord Scraper..."

# Clean up any old shutdown marker
rm -f /tmp/shutdown_discord_scraper

# Start Docker Compose services
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 5

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✅ All services started successfully!"
    echo ""
    echo "📊 Dashboard available at: http://localhost:3000"
    echo ""
    echo "🔍 Starting shutdown monitor..."
    # Start the shutdown monitor in the background
    ./shutdown-monitor.sh &
    MONITOR_PID=$!
    echo "Shutdown monitor PID: $MONITOR_PID"
    echo ""
    echo "To stop the app:"
    echo "  1. Use the Shutdown button in the dashboard (top-right menu) - RECOMMENDED"
    echo "  2. Run: docker-compose down (then kill -9 $MONITOR_PID to stop monitor)"
    echo ""
    
    # Optional: Open browser automatically (uncomment if desired)
    # open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 2>/dev/null || echo "Please open http://localhost:3000 in your browser"
else
    echo "❌ Failed to start services. Check logs with: docker-compose logs"
    exit 1
fi