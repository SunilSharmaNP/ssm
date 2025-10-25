# SS Video Merger Bot - Replit Project

## Overview
Professional Telegram video merger bot with advanced features including group-only authorization, MongoDB user settings, download mode preferences with enforcement, user mentions, enhanced cancellation, and professional progress tracking.

## Recent Changes (October 2025)
✅ **Download Mode Settings:**
- Added download_mode field to database schema and UserSettings class
- Created `/settings` plugin with TG File vs URL Download mode toggle
- Implemented visual selection indicator (✅ checkmark) for current mode
- Full persistence in MongoDB with backward compatibility

✅ **Mode Enforcement:**
- TG File mode: Blocks URL messages, accepts only Telegram video files
- URL Download mode: Blocks Telegram files, accepts only download URLs
- Clear error messages guide users to switch modes via `/settings`

✅ **Upload Completion Enhancements:**
- Added user mention ({user.mention}) in upload completion notifications
- User gets mentioned when merged video upload completes

✅ **Enhanced Cancel Command:**
- `/cancel` command with safe FFmpeg process termination
- Only terminates user's own FFmpeg processes (multi-user safe)
- Clears queue, stops processes, cleans temporary files
- Detailed status message showing what was cancelled

✅ **Stats Command:**
- `/stats` command for owner and authorized users (admins)
- Shows user statistics (total, allowed, with settings)
- System stats (uptime, CPU, RAM, disk usage)
- Active queue information

## Project Architecture
- **Main Bot:** bot.py - Core bot with all command handlers and mode enforcement
- **Config:** config.py - Configuration management with environment variables
- **Helpers:** helpers/ - Database, utils, ffmpeg, encoding, upload modules
- **Plugins:** plugins/ - Modular command handlers (callbacks, encoding, merging, settings)
- **Downloads:** downloads/ - Temporary storage for video processing (user-isolated)

## User Preferences (MongoDB Persisted)
- **Download Mode:** TG File (default) or URL Download
- **Merge Mode:** video-video, video-audio, video-subtitle, extract-streams
- **Upload Mode:** Telegram or GoFile
- **Metadata Editing:** Enabled/Disabled
- **Upload as Document:** True/False
- All preferences stored in `mergeSettings` collection with full persistence

## Key Features

### Download Mode System
- **TG File Mode:** Accept Telegram video files, block URL messages
- **URL Download Mode:** Accept download URLs, block Telegram files
- Settings accessible via `/settings` command
- Visual indicator shows current selected mode
- Mode enforcement prevents wrong input type

### Commands
- `/start` - Welcome message and access check
- `/login <password>` - User authentication
- `/help` - Detailed usage guide
- `/settings` - Download mode and preference settings
- `/cancel` - Cancel operations, stop FFmpeg, clear queue
- `/stats` - Bot statistics (owner/admins only)
- `/encode` - Start encoding mode

### Video Processing
- Merge multiple videos with professional FFmpeg integration
- Real-time progress tracking for download/merge/encode/upload
- Custom filename and thumbnail support
- Multiple quality presets (1080p/720p/480p)
- H.264 and HEVC/H.265 codec support
- Upload destination choice (Telegram vs GoFile)

### Security & Access Control
- Password-based login system
- Owner and admin authorization
- Per-user isolated processing (downloads/{user_id})
- Safe FFmpeg termination (won't kill other users' processes)
- Banned user management

## Environment Variables
See `config.env` for template. Add to Replit Secrets:

**Required:**
- `API_HASH` - Telegram API hash
- `BOT_TOKEN` - Telegram bot token
- `TELEGRAM_API` - Telegram API ID (integer)
- `OWNER` - Owner user ID (integer)
- `OWNER_USERNAME` - Owner Telegram username
- `DATABASE_URL` - MongoDB connection string

**Optional:**
- `PASSWORD` - Bot access password (default: mergebot123)
- `GOFILE_TOKEN` - GoFile API token for uploads
- `LOGCHANNEL` - Channel ID for logging uploads
- `MAX_CONCURRENT_USERS` - Concurrent processing limit
- `MAX_FILE_SIZE` - Maximum file size in bytes

## Database Schema
Collection: `mergeSettings`
```json
{
  "_id": user_id,
  "name": "User Name",
  "user_settings": {
    "merge_mode": 1,
    "edit_metadata": false,
    "upload_as_doc": false,
    "upload_to_drive": false,
    "download_mode": "tg"  // "tg" or "url"
  },
  "isAllowed": true,
  "isBanned": false,
  "thumbnail": null
}
```

## Dependencies
- Python 3.11
- Pyrogram 2.0.106 - Telegram MTProto API
- pymongo 4.5.0 - MongoDB driver
- FFmpeg (system) - Video processing
- MongoDB (system) - Database
- psutil 5.9.6 - Process management
- Additional: TgCrypto, aiofiles, aiohttp, motor, requests

## Workflow
- **Name:** Merger Bot
- **Command:** `python bot.py`
- **Output:** Console
- Auto-restart on package/module installation

## Next Steps for User
1. Add credentials to Replit Secrets (API_HASH, BOT_TOKEN, etc.)
2. Start the workflow
3. Test download mode settings with `/settings`
4. Test mode enforcement (send TG file in URL mode, URL in TG mode)
5. Test cancel command during active merge
6. Test stats command
