# 🎬 VIDEOMERGE Bot v3.0 - Professional Edition

**A Powerful Telegram Bot for Video Merging and Encoding**

## 🌟 Features

### 🔥 Merge Mode
- ✅ Merge multiple videos into one seamless file
- ✅ Add audio tracks to existing videos
- ✅ Embed subtitle files (SRT, ASS, MKA)
- ✅ Extract audio/subtitle streams from videos
- ✅ Custom thumbnail support
- ✅ Queue management system

### 🎬 Encoding Mode
- ✅ **Multiple Quality Presets:**
  - 1080p H.264 / HEVC
  - 720p H.264 / HEVC
  - 480p H.264 / HEVC
  
- ✅ **Custom Encoding Settings:**
  - CRF quality control (Best to Potato)
  - Video codecs (H.264, H.265/HEVC, VP9)
  - Encoding speed presets (Ultra Fast to Very Slow)
  - Resolution scaling
  - Audio bitrate control (64k to 320k)
  - Audio codec selection (AAC, Opus, MP3)

### 🔧 Additional Features
- ✅ GoFile upload integration for large files (>2GB)
- ✅ Password protection & user management
- ✅ Professional FFmpeg integration
- ✅ Real-time progress tracking
- ✅ Error recovery & logging
- ✅ Database persistence (PostgreSQL/MongoDB)

## 📋 Requirements

- Python 3.8+
- FFmpeg installed
- PostgreSQL or MongoDB database
- Telegram Bot Token
- Telegram API ID & Hash

## 🚀 Installation

### 1. Clone Repository
```bash
git clone https://github.com/SunilSharmaNP/ssm.git
cd ssm
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install FFmpeg
**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html)

### 4. Configure Environment
Copy and edit the config file:
```bash
cp sample_config.env config.env
nano config.env
```

Required variables:
```env
# Telegram Configuration
API_HASH=your_api_hash_here
BOT_TOKEN=your_bot_token_here
TELEGRAM_API=your_api_id_here
OWNER=your_telegram_user_id
OWNER_USERNAME=your_telegram_username

# Database (PostgreSQL or MongoDB)
DATABASE_URL=your_database_url_here

# Bot Settings
PASSWORD=your_bot_password

# Optional - GoFile Upload
GOFILE_TOKEN=your_gofile_token  # Optional, works without token too

# Optional - Log Channel
LOGCHANNEL=-100xxxxxxxxxxxxx  # Optional
```

### 5. Run the Bot
```bash
python bot.py
```

## 📖 Usage Guide

### Getting Started

1. **Start the bot:** `/start`
2. **Login:** `/login <password>`
3. **Get help:** `/help`

### 🔥 Merge Mode

**Step 1:** Upload 2 or more video files to the bot

**Step 2:** Click the "🔥 Merge Videos" button

**Step 3:** Wait for processing (progress shown)

**Step 4:** Receive your merged video!

**Optional:** Add audio tracks or subtitles before merging

### 🎬 Encoding Mode

**Step 1:** Send command `/encode`

**Step 2:** Upload a single video file

**Step 3:** Choose from options:
- **Quick Preset:** Select 1080p/720p/480p with H.264 or HEVC
- **Custom Settings:** Fine-tune every aspect

**Step 4:** Confirm and wait for encoding

**Step 5:** Receive your encoded video!

### ⚙️ Custom Encoding Settings

**Quality (CRF):**
- Best (18/23): Nearly lossless, large files
- High (21/26): Excellent quality
- Medium (23/28): Good balance (recommended)
- Low (26/31): Smaller files
- Potato (30/35): Very small files

**Video Codecs:**
- H.264: Best compatibility, good quality
- HEVC/H.265: Better compression, smaller files
- VP9: Open codec, good for web

**Encoding Speed:**
- Ultra Fast: Quick encoding, larger files
- Medium: Balanced (recommended)
- Slow/Very Slow: Best compression, takes longer

**Audio Bitrate:**
- 64k-96k: Low quality
- 128k: Standard (recommended)
- 192k-256k: High quality
- 320k: Maximum quality

## 🎯 Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/login <password>` | Login to access bot features |
| `/help` | Show detailed usage guide |
| `/encode` | Start encoding mode |
| `/settings` | View/change user settings |

## 📊 Supported Formats

### Video Formats
MP4, MKV, AVI, MOV, WEBM, TS, WAV

### Audio Formats
MP3, AAC, AC3, EAC3, M4A, MKA, THD, DTS

### Subtitle Formats
SRT, ASS, MKA, MKS

## 🔧 Advanced Configuration

### GoFile Upload Setup
For files larger than 2GB, enable GoFile upload:

1. Get GoFile API token (optional - works without it)
2. Add to config.env: `GOFILE_TOKEN=your_token`
3. Enable in bot settings

### Database Options

**PostgreSQL:**
```env
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

**MongoDB:**
```env
DATABASE_URL=mongodb://user:password@localhost:27017/dbname
```

## 🐛 Troubleshooting

### FFmpeg Not Found
```bash
# Verify FFmpeg installation
ffmpeg -version

# Install if missing
sudo apt install ffmpeg  # Ubuntu/Debian
brew install ffmpeg      # macOS
```

### Database Connection Error
- Check DATABASE_URL format
- Verify database server is running
- Check user permissions

### Bot Not Responding
- Verify BOT_TOKEN is correct
- Check internet connection
- Review bot logs: `mergebotlog.txt`

### Encoding Fails
- Check FFmpeg is installed
- Verify input video is not corrupted
- Try with different encoding preset
- Check available disk space

## 📈 Performance Tips

### Merge Mode
- Use videos with similar resolution/codec for faster merging
- Enable "copy" mode (no re-encoding) when possible
- Large files: Use GoFile upload

### Encoding Mode
- **For Speed:** Use "Fast" or "Ultra Fast" preset
- **For Quality:** Use "Slow" or "Very Slow" preset
- **For Size:** Use HEVC codec with CRF 28
- **For Compatibility:** Use H.264 codec

## 🔒 Security

- Bot uses password protection
- User management system
- Owner-only statistics
- Secure database storage
- No data retention after processing

## 📝 Changelog

### Version 3.0 (Current)
- ✨ Added professional encoding mode
- ✨ Multiple quality presets (1080p/720p/480p)
- ✨ Custom encoding settings
- ✨ H.264 and HEVC/H.265 support
- ✨ Button-based interface
- ✨ GoFile upload integration
- 🔧 Removed RClone and Google Drive
- 🐛 Fixed merge errors
- 🐛 Improved error handling

### Version 2.0
- ✨ Added merge functionality
- ✨ Audio/subtitle support
- ✨ Database integration

### Version 1.0
- 🎉 Initial release

## 👨‍💻 Developer

**Sunil Sharma NP**
- Telegram: [@SunilSharmaNP](https://t.me/SunilSharmaNP)
- GitHub: [SunilSharmaNP](https://github.com/SunilSharmaNP)

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## ⚠️ Disclaimer

This bot is for educational and personal use only. Ensure you have rights to process any media content.

## 💡 Tips & Best Practices

### Merge Mode
1. Keep videos in same format for best results
2. Use "copy" codec when possible (faster)
3. Add subtitles before audio tracks
4. Check queue before merging

### Encoding Mode
1. **Quick Web Upload:** 480p H.264, CRF 26, Fast
2. **Archival Quality:** 1080p HEVC, CRF 23, Slow
3. **Balanced:** 720p H.264, CRF 23, Medium
4. **Maximum Compression:** Any resolution HEVC, CRF 28, Slow

### General
1. Delete queue after processing
2. Use GoFile for files >2GB
3. Enable log channel for monitoring
4. Regular database backups

## 📞 Support

- Issues: [GitHub Issues](https://github.com/SunilSharmaNP/ssm/issues)
- Telegram: [@SunilSharmaNP](https://t.me/SunilSharmaNP)
- Documentation: This README

## 🙏 Acknowledgments

- FFmpeg team for the amazing tool
- Pyrogram for Telegram Bot API
- GoFile for file hosting
- All contributors and users

---

**Made with ❤️ by Sunil Sharma NP**

*Star ⭐ this repo if you find it useful!*
