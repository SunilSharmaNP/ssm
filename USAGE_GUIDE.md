# SSMERGE Bot - Enhanced Features Usage Guide

## 🎯 New Features Implemented

### 1. Group-Only Authorization

**How it works:**
- **Owner (you)**: Full access everywhere - private chats and all groups
- **Normal users**: Can ONLY use the bot in authorized groups
- **Private chats**: Blocked for normal users with clear error message

**Managing Authorized Groups:**

The bot owner can authorize groups using the database functions. To authorize a group programmatically:

```python
from helpers.database import add_authorized_chat, remove_authorized_chat

# Add authorized group
await add_authorized_chat(chat_id=-1001234567890, chat_title="My Group")

# Remove authorized group
await remove_authorized_chat(chat_id=-1001234567890)
```

**User Experience:**
- When a normal user tries to use the bot in private chat, they see:
  ```
  🚫 Private Chat Blocked
  
  ❌ This bot works only in authorized groups.
  💡 Normal users cannot use this bot in private messages.
  
  📞 Contact owner: @YourUsername
  ```

### 2. Dual Download Mode System

**Two Modes Available:**

#### 📱 TG File Mode (Default)
- Users can send Telegram video/audio/document files
- URLs are **blocked** with error message
- Perfect for processing files already on Telegram

#### 🔗 URL Download Mode
- Users can send direct download URLs (HTTP/HTTPS)
- Telegram files are **blocked** with error message
- Perfect for downloading from external sources

**Changing Download Mode:**

1. Send `/settings` command
2. Click the **Download Mode** button
3. See visual indicator:
   - `✅ TG | ☐ URL` = TG File Mode active
   - `☐ TG | ✅ URL` = URL Download Mode active
4. Toggle switches between modes

**What Happens When Wrong Type is Sent:**

If you're in TG File mode and send a URL:
```
🚫 URL Blocked

Your download mode is set to TG File Only.
This URL cannot be processed.

💡 Change to URL mode in /settings or send Telegram files only.
```

If you're in URL mode and send a Telegram file:
```
🚫 Telegram File Blocked

Your download mode is set to URL Download Only.
This Telegram file cannot be processed.

💡 Change to TG File mode in /settings or send URLs only.
```

### 3. Enhanced Settings UI

The new settings panel shows:

```
⚙️ Merge Bot Settings
━━━━━━━━━━━━━━━━━━━━━━
User: Your Name

Account Status:
┣ 👦 ID: 1234567890
┣ 🫡 Ban Status: False
┗ ⚡ Allowed: True

Bot Settings:
┣ Ⓜ️ Merge Mode: Video 🎥 + Video 🎥
┣ ✅ Edit Metadata: True
┗ 📥 Download Mode: 📱 TG File

Download Mode: ✅ TG | ☐ URL
━━━━━━━━━━━━━━━━━━━━━━
💡 Tip: Click buttons below to change settings
```

### 4. Enhanced Progress Tracking

All operations now show real-time progress:

#### Download Progress:
```
📥 Downloading

████████████░░░░░░░░ 60.0%

📊 Status:
├ Processed: 120.5 MB
├ Total: 200.0 MB
├ Speed: 5.2 MB/s
├ ETA: 15s
└ Elapsed: 23s

💡 Use /cancel to stop this operation
```

#### Merge Progress:
```
🔄 Merging Videos

██████████████████░░ 90.0%

📊 Progress:
├ Stage: Final Encoding
├ Speed: 2.5x
└ Time Remaining: 30s

💡 Use /cancel to stop this operation
```

#### Upload Progress:
```
📤 Uploading to Telegram

████████████████████ 100%

📊 Status:
├ Uploaded: 500.0 MB
├ Total: 500.0 MB
├ Speed: 8.5 MB/s
└ Elapsed: 58s

✅ Upload Complete!
```

### 5. Database Collections

The bot uses MongoDB with these collections:

- **mergeSettings**: User preferences (download_mode, merge_mode, etc.)
- **authorized_chats**: List of groups where normal users can use the bot
- **allowedUsers**: Users with login access
- **thumbnail**: User custom thumbnails

## 🚀 Getting Started

1. **Set Environment Variables:**
   All required secrets are already configured in Replit Secrets:
   - TELEGRAM_API
   - API_HASH
   - BOT_TOKEN
   - OWNER
   - OWNER_USERNAME
   - DATABASE_URL

2. **Bot is Running:**
   The bot is already running and connected to Telegram!

3. **Test the Bot:**
   - Send `/start` in a private chat (as owner, you'll have access)
   - Send `/settings` to see the enhanced settings panel
   - Try toggling download mode
   - Test sending a file or URL based on your selected mode

## 📋 Admin Commands

As the owner, you have access to these features:

- `/start` - Main menu with bot features
- `/settings` - Configure bot settings
- `/login <password>` - For other users to gain access
- `/help` - Get help information

## 🔐 Security Features

✅ Database credentials are **masked** in logs
✅ Group-only access prevents spam in private chats
✅ Download mode prevents processing wrong media types
✅ All secrets managed through Replit Secrets

## 📝 Notes

- The bot automatically saves user preferences to MongoDB
- Download mode persists between sessions
- Progress updates every 2 seconds to avoid rate limits
- Cancel operations with `/cancel` command at any time
- FFmpeg processes are properly terminated on cancel

## 🎉 Ready to Use!

Your enhanced Telegram Video Merger Bot is fully operational with:
- ✅ Group-only authorization
- ✅ Dual download mode enforcement
- ✅ Real-time progress tracking
- ✅ Enhanced user settings UI
- ✅ Secure credential management

Happy merging! 🎬
