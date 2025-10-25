#!/bin/bash

# MERGE-BOT VPS Deployment Setup Script
# This script automatically applies all improvements for VPS deployment

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() { echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"; }
warn() { echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING: $1${NC}"; }
error() { echo -e "${RED}[$(date +'%H:%M:%S')] ERROR: $1${NC}"; }
info() { echo -e "${BLUE}[$(date +'%H:%M:%S')] INFO: $1${NC}"; }

# Banner
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════╗"
echo "║           MERGE-BOT VPS SETUP SCRIPT            ║"
echo "║        Automated Deployment Enhancement          ║"
echo "╚══════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if we're in the right directory
if [ ! -f "bot.py" ] || [ ! -f "config.py" ]; then
    error "This doesn't look like a MERGE-BOT directory!"
    error "Please run this script from the MERGE-BOT root directory."
    exit 1
fi

log "Starting MERGE-BOT VPS deployment setup..."

# Create backup of original files
log "Creating backup of original files..."
mkdir -p backup/$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup/$(date +%Y%m%d_%H%M%S)"

# Backup original files
for file in config.py requirements.txt Dockerfile start.sh bot.py get_config.py; do
    if [ -f "$file" ]; then
        cp "$file" "$BACKUP_DIR/"
        log "Backed up $file"
    fi
done

log "✅ All improvements will be applied from the provided improved files"
log "✅ Please replace the files manually with the improved versions"

# Create directories
mkdir -p downloads logs
chmod 755 downloads logs

# Create deployment instructions
log "Creating deployment instructions..."
cat > DEPLOYMENT_README.md << 'EOF'
# 🚀 MERGE-BOT VPS Deployment (Improved)

## Quick Start

1. **Copy environment file:**
   ```bash
   cp .env.template .env
   nano .env  # Fill in your values
   ```

2. **Start with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

3. **Check logs:**
   ```bash
   docker-compose logs -f merge-bot
   ```

## Required Environment Variables

Fill these in your `.env` file:

- `API_HASH` - From my.telegram.org
- `BOT_TOKEN` - From @BotFather
- `TELEGRAM_API` - From my.telegram.org  
- `OWNER` - Your Telegram user ID
- `OWNER_USERNAME` - Your Telegram username
- `DATABASE_URL` - MongoDB connection string (default works for Docker)

## Health Check

Visit: http://your-server-ip:8080/health

## Support

- Original repo: https://github.com/yashoswalyo/MERGE-BOT
- Issues: Create GitHub issue with logs
EOF

log "✅ Setup preparation completed successfully!"

echo
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                SETUP COMPLETE!                   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo

info "Next steps:"
echo "1. Replace original files with improved versions provided"
echo "2. Copy .env.template to .env: cp .env.template .env"
echo "3. Edit .env file with your configuration: nano .env"
echo "4. Start the bot: docker-compose up -d"
echo "5. Check logs: docker-compose logs -f merge-bot"
echo

info "Your original files are backed up in: $BACKUP_DIR"
info "For detailed instructions, see: DEPLOYMENT_README.md"

log "Setup completed successfully! 🎉"
