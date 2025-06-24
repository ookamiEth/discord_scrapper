#!/bin/bash

# Discord Scraper Shutdown Monitor
# This script monitors for shutdown requests and executes docker-compose down

MARKER_FILE="/tmp/shutdown_discord_scraper"

echo "🔍 Discord Scraper Shutdown Monitor Started"
echo "Monitoring for shutdown requests..."

while true; do
    if [ -f "$MARKER_FILE" ]; then
        echo "📌 Shutdown request detected!"
        cat "$MARKER_FILE"
        
        # Remove marker file
        rm -f "$MARKER_FILE"
        
        # Change to project directory
        cd "$(dirname "$0")"
        
        echo "🛑 Shutting down all services..."
        docker-compose down
        
        echo "✅ All services stopped. Exiting monitor."
        exit 0
    fi
    
    # Check every 2 seconds
    sleep 2
done