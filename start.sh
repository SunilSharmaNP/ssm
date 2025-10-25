#!/bin/bash

# Improved start script with better error handling and logging

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" >&2
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

# Create necessary directories
mkdir -p downloads
mkdir -p logs

# Set permissions
chmod 755 downloads
chmod 755 logs

log "Starting MERGE-BOT..."

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
log "Python version: $python_version"

# Check if all required packages are installed
log "Checking dependencies..."
if ! python3 -c "import pyrogram, pymongo, ffmpeg, requests" 2>/dev/null; then
    error "Some required packages are missing!"
    error "Please run: pip3 install -r requirements.txt"
    exit 1
fi

# Check if ffmpeg is available
if ! command -v ffmpeg &> /dev/null; then
    error "ffmpeg is not installed or not in PATH!"
    error "Please install ffmpeg: sudo apt-get install ffmpeg"
    exit 1
fi

log "Dependencies check passed!"

# Function to handle graceful shutdown
cleanup() {
    log "Received shutdown signal. Cleaning up..."
    
    # Kill background processes
    jobs -p | xargs -r kill
    
    # Remove temporary files older than 1 day
    find downloads/ -type f -mtime +1 -delete 2>/dev/null || true
    
    log "Cleanup completed. Shutting down..."
    exit 0
}

# Set up signal handlers for graceful shutdown
trap cleanup SIGTERM SIGINT

# Check and fetch config if needed
if [ -n "$CONFIG_FILE_URL" ]; then
    log "Fetching config from URL..."
    if python3 get_config.py; then
        log "Config fetched successfully"
    else
        error "Failed to fetch config from URL"
        exit 1
    fi
fi

# Start the bot with proper error handling
log "Starting the bot process..."

# Create a simple health check endpoint
python3 -c "
import threading
import http.server
import socketserver

class HealthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

def start_health_server():
    try:
        with socketserver.TCPServer(('', 8080), HealthHandler) as httpd:
            httpd.serve_forever()
    except:
        pass

# Start health check server in background
threading.Thread(target=start_health_server, daemon=True).start()
" &

# Start the main bot
exec python3 bot.py
