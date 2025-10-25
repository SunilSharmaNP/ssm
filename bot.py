#!/usr/bin/env python3
"""
MERGE-BOT - Complete Fixed Version
All spam, callback, and merge issues resolved
"""
import os
import shutil
import time
import psutil
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyromod import listen

# Import configurations
from __init__ import (
    AUDIO_EXTENSIONS, LOGGER, MERGE_MODE, SUBTITLE_EXTENSIONS, 
    UPLOAD_AS_DOC, UPLOAD_TO_GOFILE, VIDEO_EXTENSIONS,
    formatDB, gDict, queueDB, replyDB
)
from config import Config
from helpers.utils import UserSettings, get_readable_file_size, get_readable_time

botStartTime = time.time()

class MergeBot(Client):
    def start(self):
        super().start()
        try:
            self.send_message(
                chat_id=int(Config.OWNER), 
                text="🚀 **Bot Started Successfully!**\n\n"
                     f"⏰ Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                     "🤖 Version: SSMERGE Bot v2.0"
            )
        except Exception:
            pass
        LOGGER.info("✅ Bot Started Successfully!")

    def stop(self):
        super().stop()
        LOGGER.info("🛑 Bot Stopped")

def delete_all(root):
    """Delete directory and all contents"""
    if os.path.exists(root):
        shutil.rmtree(root)

mergeApp = MergeBot(
    name="merge-bot",
    api_hash=Config.API_HASH,
    api_id=Config.TELEGRAM_API,
    bot_token=Config.BOT_TOKEN,
    workers=300,
    app_version="2.0+fixed",
)

# Create downloads directory
if not os.path.exists("downloads"):
    os.makedirs("downloads")

# ================== LOGIN HANDLER ==================

@mergeApp.on_message(filters.command(["login"]) & filters.private)
async def loginHandler(c: Client, m: Message):
    """Fixed login handler with proper persistence"""
    user = UserSettings(m.from_user.id, m.from_user.first_name)
    
    LOGGER.info(f"Login attempt - User: {user.user_id}, Allowed: {user.allowed}")
    
    if user.banned:
        await m.reply_text(
            "🚫 **Access Denied**\n\n❌ Your account has been banned\n"
            f"📞 Contact: @{Config.OWNER_USERNAME}",
            quote=True
        )
        return

    # Owner gets immediate access
    if user.user_id == int(Config.OWNER):
        user.allowed = True
        user.set()
        await m.reply_text(
            "✅ **Owner Access Granted!**\n\n"
            f"👋 Hi {m.from_user.first_name}\n🎉 You have full bot access!",
            quote=True
        )
        return

    # Check if already allowed
    if user.allowed:
        await m.reply_text(
            "✅ **Welcome Back!**\n\n"
            f"👋 Hi {m.from_user.first_name}\n🎉 You can use the bot freely!",
            quote=True
        )
        return

    # Password login
    try:
        passwd = m.text.split(" ", 1)[1].strip()
    except IndexError:
        await m.reply_text(
            "🔐 **Login Required**\n\n"
            "**Usage:** `/login <password>`\n\n"
            f"🔑 Get password from: @{Config.OWNER_USERNAME}",
            quote=True
        )
        return

    if passwd == Config.PASSWORD:
        user.allowed = True
        user.set()  # CRITICAL: Save to database
        await m.reply_text(
            "🎉 **Login Successful!**\n\n"
            "✅ Access granted\n🚀 You can now use the bot!",
            quote=True
        )
    else:
        await m.reply_text(
            "❌ **Login Failed**\n\n"
            "🔐 Incorrect password\n"
            f"📞 Contact: @{Config.OWNER_USERNAME}",
            quote=True
        )

# ================== START HANDLER ==================

@mergeApp.on_message(filters.command(["start"]) & filters.private)
async def start_handler(c: Client, m: Message):
    """Fixed start handler - no more spam"""
    user = UserSettings(m.from_user.id, m.from_user.first_name)
    
    LOGGER.info(f"Start command - User: {user.user_id}, Allowed: {user.allowed}")
    
    # Check access for non-owners
    if m.from_user.id != int(Config.OWNER) and not user.allowed:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔐 Login", callback_data="need_login")],
            [InlineKeyboardButton("ℹ️ About", callback_data="about")],
            [InlineKeyboardButton("📞 Owner", url=f"https://t.me/{Config.OWNER_USERNAME}")]
        ])
        
        await m.reply_text(
            f"👋 **Welcome {m.from_user.first_name}!**\n\n"
            "🤖 **Professional Video Tools Bot**\n"
            "📹 Advanced video processing and manipulation tools\n\n"
            "🔐 **Login Required for Access**\n"
            f"📞 Contact owner: @{Config.OWNER_USERNAME}",
            quote=True,
            reply_markup=keyboard
        )
        return  # STOP HERE - NO SPAM

    # Owner access
    if m.from_user.id == int(Config.OWNER):
        user.allowed = True
        user.set()

    # Authorized user menu
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Merge Mode", callback_data="merge_mode_info"),
         InlineKeyboardButton("🎬 Encode Mode", callback_data="enc_mode_menu")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
         InlineKeyboardButton("ℹ️ About", callback_data="about")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("🔗 Owner", url=f"https://t.me/{Config.OWNER_USERNAME}")]
    ])
    
    await m.reply_text(
        f"👋 **Welcome {m.from_user.first_name}!**\n\n"
        "🤖 **Professional Video Tools Bot**\n"
        "📹 **Dual Mode System:**\n"
        "• 🔥 **Merge Mode** - Combine multiple videos\n"
        "• 🎬 **Encode Mode** - Professional quality encoding\n\n"
        "✅ **Full Access Granted**\n"
        f"⏱ **Bot Uptime:** `{get_readable_time(time.time() - botStartTime)}`\n\n"
        "💡 **Tip:** Use /help for detailed guide",
        quote=True,
        reply_markup=keyboard
    )

# ================== VIDEO UPLOAD HANDLER ==================

@mergeApp.on_message((filters.video | filters.document) & filters.private)
async def video_upload_handler(c: Client, m: Message):
    """Handle video uploads with download mode enforcement"""
    user = UserSettings(m.from_user.id, m.from_user.first_name)
    
    if not user.allowed and m.from_user.id != int(Config.OWNER):
        await m.reply_text("🔐 **Access Required!** Please login first using `/login <password>`")
        return
    
    # Download mode enforcement
    download_mode = user.download_mode
    if download_mode == "url":
        await m.reply_text(
            "🚫 **Telegram Files Blocked**\n\n"
            "Your download mode is set to **URL Download Only**.\n"
            "Please send download URLs instead of Telegram files.\n\n"
            "💡 Change mode: Use `/settings` to switch to TG File mode.",
            quote=True
        )
        return
    
    # Initialize user queue if not exists
    if m.from_user.id not in queueDB:
        queueDB[m.from_user.id] = {"videos": [], "subtitles": [], "audios": []}

    # Check file type and add to appropriate queue
    file_added = False
    file_name = "Unknown"
    file_size = 0
    
    if m.video:
        queueDB[m.from_user.id]["videos"].append(m.id)
        file_name = m.video.file_name or f"video_{m.id}.mp4"
        file_size = m.video.file_size
        file_added = True
        
    elif m.document:
        file_ext = m.document.file_name.split('.')[-1].lower() if m.document.file_name else ""
        
        if file_ext in VIDEO_EXTENSIONS:
            queueDB[m.from_user.id]["videos"].append(m.id)
            file_added = True
        elif file_ext in AUDIO_EXTENSIONS:
            queueDB[m.from_user.id]["audios"].append(m.id)
            file_added = True  
        elif file_ext in SUBTITLE_EXTENSIONS:
            queueDB[m.from_user.id]["subtitles"].append(m.id)
            file_added = True
            
        file_name = m.document.file_name or f"document_{m.id}"
        file_size = m.document.file_size

    if file_added:
        # Show queue status with merge/encode buttons
        video_count = len(queueDB[m.from_user.id]["videos"])
        audio_count = len(queueDB[m.from_user.id]["audios"]) 
        subtitle_count = len(queueDB[m.from_user.id]["subtitles"])
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔥 Merge Videos", callback_data="merge"),
             InlineKeyboardButton("🎬 Encode Video", callback_data="enc_mode_menu")],
            [InlineKeyboardButton("📋 Show Queue", callback_data="show_queue"),
             InlineKeyboardButton("🗑️ Clear Queue", callback_data="clear_queue")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
        ])
        
        await m.reply_text(
            f"✅ **File Added to Queue!**\n\n"
            f"📁 **File:** `{file_name}`\n"
            f"📊 **Size:** `{get_readable_file_size(file_size)}`\n\n"
            f"📋 **Queue Status:**\n"
            f"🎬 Videos: **{video_count}**\n"
            f"🎵 Audios: **{audio_count}**\n"
            f"📝 Subtitles: **{subtitle_count}**\n\n"
            f"{'🚀 Ready to merge!' if video_count >= 2 else '📥 Add more videos to merge'}",
            reply_markup=keyboard
        )
    else:
        await m.reply_text(
            "❌ **Unsupported File Type!**\n\n"
            "📌 **Supported formats:**\n"
            f"🎬 Videos: `{', '.join(VIDEO_EXTENSIONS)}`\n"
            f"🎵 Audios: `{', '.join(AUDIO_EXTENSIONS)}`\n"
            f"📝 Subtitles: `{', '.join(SUBTITLE_EXTENSIONS)}`"
        )

# ================== URL MESSAGE HANDLER ==================

@mergeApp.on_message(filters.text & filters.private & ~filters.command(["start", "login", "help", "settings", "encode", "cancel", "stats"]))
async def url_message_handler(c: Client, m: Message):
    """Handle URL messages with download mode enforcement"""
    user = UserSettings(m.from_user.id, m.from_user.first_name)
    
    if not user.allowed and m.from_user.id != int(Config.OWNER):
        await m.reply_text("🔐 **Access Required!** Please login first using `/login <password>`")
        return
    
    # Check if message contains URL
    text = m.text
    if not (text.startswith("http://") or text.startswith("https://")):
        await m.reply_text(
            "❓ **Invalid Input**\n\n"
            "Please send:\n"
            "• Video files (for TG File mode)\n"
            "• Direct download URLs (for URL mode)\n\n"
            "💡 Change download mode with `/settings`",
            quote=True
        )
        return
    
    # Download mode enforcement
    download_mode = user.download_mode
    if download_mode == "tg":
        await m.reply_text(
            "🚫 **URLs Blocked**\n\n"
            "Your download mode is set to **TG File Only**.\n"
            "Please send Telegram video files instead of URLs.\n\n"
            "💡 Change mode: Use `/settings` to switch to URL Download mode.",
            quote=True
        )
        return
    
    # URL mode - accept the URL
    await m.reply_text(
        "🔗 **URL Received**\n\n"
        f"📥 **Link:** `{text}`\n\n"
        "⚠️ **Note:** URL downloading is currently in development.\n"
        "For now, please use Telegram files by changing mode to TG File in `/settings`.",
        quote=True
    )

# ================== CALLBACK HANDLER ==================

@mergeApp.on_callback_query()
async def callback_handler(c: Client, cb):
    """Fixed callback handler with all functions + encoding support"""
    data = cb.data
    user_id = cb.from_user.id
    user = UserSettings(user_id, cb.from_user.first_name)
    
    LOGGER.info(f"Callback: {data} from user {user_id}, allowed: {user.allowed}")
    
    # Handle encoding callbacks
    if data.startswith("enc_"):
        from plugins.encoding import handle_encoding_callback
        await handle_encoding_callback(c, cb)
        return
    
    try:
        if data == "need_login":
            await cb.message.edit_text(
                "🔐 **Login Required**\n\n"
                "**Usage:** Send `/login <password>`\n\n"
                f"🔑 Get password from: @{Config.OWNER_USERNAME}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
                ])
            )
            
        elif data == "back_to_start":
            # Recreate user object with correct user_id from callback
            user = UserSettings(cb.from_user.id, cb.from_user.first_name)
            
            # Check access for non-owners
            if cb.from_user.id != int(Config.OWNER) and not user.allowed:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔐 Login", callback_data="need_login")],
                    [InlineKeyboardButton("ℹ️ About", callback_data="about")],
                    [InlineKeyboardButton("📞 Owner", url=f"https://t.me/{Config.OWNER_USERNAME}")]
                ])
                
                await cb.message.edit_text(
                    f"👋 **Welcome {cb.from_user.first_name}!**\n\n"
                    "🤖 **Professional Video Tools Bot**\n"
                    "📹 Advanced video processing and manipulation tools\n\n"
                    "🔐 **Login Required for Access**\n"
                    f"📞 Contact owner: @{Config.OWNER_USERNAME}",
                    reply_markup=keyboard
                )
                return
            
            # Owner access
            if cb.from_user.id == int(Config.OWNER):
                user.allowed = True
                user.set()
            
            # Authorized user menu
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔥 Merge Mode", callback_data="merge_mode_info"),
                 InlineKeyboardButton("🎬 Encode Mode", callback_data="enc_mode_menu")],
                [InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
                 InlineKeyboardButton("ℹ️ About", callback_data="about")],
                [InlineKeyboardButton("📊 Stats", callback_data="stats")],
                [InlineKeyboardButton("🔗 Owner", url=f"https://t.me/{Config.OWNER_USERNAME}")]
            ])
            
            await cb.message.edit_text(
                f"👋 **Welcome {cb.from_user.first_name}!**\n\n"
                "🤖 **Professional Video Tools Bot**\n"
                "📹 **Dual Mode System:**\n"
                "• 🔥 **Merge Mode** - Combine multiple videos\n"
                "• 🎬 **Encode Mode** - Professional quality encoding\n\n"
                "✅ **Full Access Granted**\n"
                f"⏱ **Bot Uptime:** `{get_readable_time(time.time() - botStartTime)}`\n\n"
                "💡 **Tip:** Use /help for detailed guide",
                reply_markup=keyboard
            )
            
        elif data == "settings":
            if not user.allowed:
                await cb.answer("🔐 Login required!", show_alert=True)
                return
                
            settings_text = f"""⚙️ **User Settings**

👤 **Name:** {cb.from_user.first_name}
🆔 **User ID:** `{user_id}`
🎭 **Mode:** Video + Video
📤 **Upload:** As Video
🚫 **Banned:** No ✅
✅ **Allowed:** Yes"""
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎥 Mode: Video+Video", callback_data="mode_1")],
                [InlineKeyboardButton("🎵 Mode: Video+Audio", callback_data="mode_2")],
                [InlineKeyboardButton("📝 Mode: Video+Subtitle", callback_data="mode_3")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
            
            await cb.message.edit_text(settings_text, reply_markup=keyboard)
            
        elif data.startswith("mode_"):
            mode_id = int(data.split("_")[1])
            user.merge_mode = mode_id
            user.set()
            
            mode_names = {1: "Video+Video", 2: "Video+Audio", 3: "Video+Subtitle"}
            await cb.answer(f"✅ Mode changed to: {mode_names.get(mode_id, 'Unknown')}")
            
        elif data == "merge":
            if not user.allowed:
                await cb.answer("🔐 Login required!", show_alert=True)
                return
                
            if user_id not in queueDB or not queueDB[user_id]["videos"]:
                await cb.answer("📋 Queue is empty! Please add videos first.", show_alert=True)
                return
                
            video_count = len(queueDB[user_id]["videos"])
            if video_count < 2:
                await cb.answer("📥 Need at least 2 videos to merge!", show_alert=True)
                return
            
            # Start merge process
            await cb.message.edit_text(
                "🔄 **Starting Merge Process...**\n\n"
                f"📁 Processing {video_count} videos\n"
                "⏳ Please wait, this may take a while..."
            )
            
            try:
                # Import and call merge function
                from helpers.merge_helper import start_merge_process
                await start_merge_process(c, cb, user_id)
                
            except ImportError:
                await cb.message.edit_text(
                    "❌ **Merge Module Not Found!**\n\n"
                    "🚨 The merge functionality is not available.\n"
                    "📞 Contact the developer for assistance."
                )
            except Exception as e:
                LOGGER.error(f"Merge error: {e}")
                await cb.message.edit_text(
                    "❌ **Merge Failed!**\n\n"
                    f"🚨 Error: `{str(e)}`\n"
                    "💡 Please try again or contact support."
                )
                
        elif data == "show_queue":
            if user_id not in queueDB:
                await cb.answer("📋 Queue is empty!", show_alert=True)
                return
                
            video_count = len(queueDB[user_id]["videos"])
            audio_count = len(queueDB[user_id]["audios"])
            subtitle_count = len(queueDB[user_id]["subtitles"])
            
            queue_text = f"""📋 **Current Queue:**

🎬 Videos: {video_count}
🎵 Audios: {audio_count}  
📝 Subtitles: {subtitle_count}

Total Items: {video_count + audio_count + subtitle_count}"""
            
            await cb.answer(queue_text, show_alert=True)
            
        elif data == "clear_queue":
            if user_id in queueDB:
                queueDB[user_id] = {"videos": [], "subtitles": [], "audios": []}
                await cb.answer("🗑️ Queue cleared successfully!", show_alert=True)
            else:
                await cb.answer("📋 Queue is already empty!", show_alert=True)
                
        elif data == "about":
            about_text = """ℹ️ **About This Bot**

🤖 **VIDEOMERGE Bot v3.0 - Professional Edition**

**🔥 Merge Features:**
✅ Merge multiple videos into one
✅ Add audio tracks to videos
✅ Add subtitle files (SRT, ASS)
✅ Custom thumbnails
✅ Stream extraction (audio/subtitles)

**🎬 Encoding Features:**
✅ Multiple quality presets (1080p/720p/480p)
✅ H.264 and HEVC/H.265 codecs
✅ Custom CRF quality control
✅ Adjustable encoding speed
✅ Custom audio bitrate & codec
✅ Resolution scaling

**🔧 Additional Features:**
✅ GoFile upload for large files (>2GB)
✅ Password protection & user management
✅ Professional FFmpeg integration
✅ Progress tracking
✅ Error recovery

**Developer:** @SunilSharmaNP
**Version:** 3.0 (Merge + Encode)
**Support:** Contact owner for issues"""
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
            
            await cb.message.edit_text(about_text, reply_markup=keyboard)
            
        elif data == "merge_mode_info":
            merge_info_text = """🔥 **Merge Mode - How It Works**

**Step-by-Step Guide:**

1️⃣ **Upload Videos**
   • Send 2 or more video files
   • Supports MP4, MKV, AVI, MOV, etc.

2️⃣ **Add Additional Content** (Optional)
   • Audio tracks (MP3, AAC, etc.)
   • Subtitle files (SRT, ASS)

3️⃣ **Click Merge**
   • Press "🔥 Merge Videos" button
   • Bot will download and process files

4️⃣ **Get Result**
   • Merged video uploaded automatically
   • Option to upload to GoFile for large files

💡 **Tips:**
• All videos should have similar resolution for best results
• Maximum file size: 2GB per video
• For files >2GB, enable GoFile upload in settings

🎯 **Supported Formats:**
• Video: MP4, MKV, AVI, MOV, WEBM, TS
• Audio: MP3, AAC, M4A, MKA, DTS
• Subtitles: SRT, ASS, MKA, MKS"""
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎬 Try Encoding Instead", callback_data="enc_mode_menu")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
            
            await cb.message.edit_text(merge_info_text, reply_markup=keyboard)
        
        elif data == "stats":
            if user_id != int(Config.OWNER):
                await cb.answer("❌ Owner only!", show_alert=True)
                return
                
            uptime = get_readable_time(time.time() - botStartTime)
            total_users = len(queueDB)
            
            stats_text = f"""📊 **Bot Statistics**

⏰ **Uptime:** `{uptime}`
👥 **Active Users:** `{total_users}`
🤖 **Version:** SSMERGE v2.0
📅 **Started:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(botStartTime))}"""
            
            await cb.answer(stats_text, show_alert=True)
            
        else:
            await cb.answer("🚧 Feature coming soon!", show_alert=True)
            
    except Exception as e:
        LOGGER.error(f"Callback error: {e}")
        await cb.answer("❌ Something went wrong!", show_alert=True)

# ================== ADDITIONAL COMMANDS ==================

@mergeApp.on_message(filters.command(["help"]) & filters.private)
async def help_handler(c: Client, m: Message):
    """Help command"""
    help_text = f"""❓ **How to Use - Dual Mode Bot**

**🔥 MERGE MODE:**
1️⃣ **Login:** `/login <password>`
2️⃣ **Send Videos:** Upload 2 or more video files
3️⃣ **Click Merge:** Press the "🔥 Merge Videos" button
4️⃣ **Wait:** Bot will process and send merged video

**🎬 ENCODING MODE:**
1️⃣ **Send Command:** `/encode`
2️⃣ **Upload Video:** Send a single video file
3️⃣ **Select Quality:** Choose preset (1080p/720p/480p)
4️⃣ **Custom Settings:** Optional - adjust CRF, codec, bitrate
5️⃣ **Encode:** Bot will encode and upload

**📋 Commands:**
• `/start` - Start the bot
• `/login <password>` - Login to use bot
• `/help` - Show this help
• `/encode` - Start encoding mode
• `/settings` - User preferences

**🎯 Features:**
• Merge multiple videos into one
• Professional video encoding
• Multiple quality presets
• H.264 & HEVC/H.265 support
• Custom encoding settings
• GoFile upload for large files

**Support:** Contact @{Config.OWNER_USERNAME}"""
    
    await m.reply_text(help_text, quote=True)

@mergeApp.on_message(filters.command(["cancel"]) & filters.private)
async def cancel_command(c: Client, m: Message):
    """Enhanced cancel command with safe FFmpeg process termination"""
    user_id = m.from_user.id
    
    # Clear merge queue
    queue_cleared = False
    if user_id in queueDB:
        queueDB[user_id] = {"videos": [], "subtitles": [], "audios": []}
        queue_cleared = True
    
    # Safely terminate FFmpeg processes for this user only
    terminated_count = 0
    user_dir = f"downloads/{user_id}"
    
    for proc in psutil.process_iter(['pid', 'name', 'cwd', 'cmdline']):
        try:
            # Check if it's an FFmpeg process
            if proc.info['name'] and 'ffmpeg' in proc.info['name'].lower():
                # Verify process is running in this user's directory
                cwd = proc.info['cwd']
                cmdline = proc.info['cmdline']
                
                # Only terminate if process is working in user's directory or has user_id in output path
                if cwd and user_dir in cwd:
                    proc.terminate()
                    terminated_count += 1
                    LOGGER.info(f"Terminated FFmpeg process {proc.info['pid']} for user {user_id}")
                elif cmdline:
                    # Check if output file contains user_id directory
                    cmdline_str = ' '.join(str(arg) for arg in cmdline)
                    if f"downloads/{user_id}/" in cmdline_str or f"downloads\\{user_id}\\" in cmdline_str:
                        proc.terminate()
                        terminated_count += 1
                        LOGGER.info(f"Terminated FFmpeg process {proc.info['pid']} for user {user_id}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.Error):
            continue
    
    # Clean up user's download directory
    files_cleaned = False
    if os.path.exists(user_dir):
        try:
            shutil.rmtree(user_dir)
            files_cleaned = True
            LOGGER.info(f"Cleaned up directory: {user_dir}")
        except Exception as e:
            LOGGER.warning(f"Failed to cleanup {user_dir}: {e}")
    
    # Build status message
    status_msg = "✅ **Operation Cancelled**\n\n"
    if queue_cleared:
        status_msg += "🗑️ Queue cleared\n"
    if terminated_count > 0:
        status_msg += f"🛑 Stopped {terminated_count} FFmpeg process(es)\n"
    if files_cleaned:
        status_msg += "🧹 Temporary files cleaned\n"
    
    if not queue_cleared and terminated_count == 0 and not files_cleaned:
        status_msg += "📋 Nothing to cancel\n"
    
    status_msg += "\n💡 You can start fresh now!"
    
    await m.reply_text(status_msg, quote=True)

@mergeApp.on_message(filters.command(["stats"]) & filters.private)
async def stats_command(c: Client, m: Message):
    """Stats command for owner and admins"""
    user = UserSettings(m.from_user.id, m.from_user.first_name)
    
    # Check if user is owner or admin (allowed user)
    if m.from_user.id != int(Config.OWNER) and not user.allowed:
        await m.reply_text("🔐 **Access Required!** This command is restricted.")
        return
    
    from helpers.database import Database
    
    # Get statistics
    try:
        total_users = Database.mergebot.users.count_documents({})
        allowed_users = Database.mergebot.allowedUsers.count_documents({})
        user_settings = Database.mergebot.mergeSettings.count_documents({})
        
        # System stats
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        uptime = get_readable_time(time.time() - botStartTime)
        
        stats_text = f"""📊 **Bot Statistics**

👥 **Users:**
• Total: `{total_users}`
• Allowed: `{allowed_users}`
• With Settings: `{user_settings}`

⚙️ **System:**
• Uptime: `{uptime}`
• CPU: `{cpu_percent}%`
• RAM: `{memory.percent}%` (`{get_readable_file_size(memory.used)}/{get_readable_file_size(memory.total)}`)
• Disk: `{disk.percent}%` (`{get_readable_file_size(disk.used)}/{get_readable_file_size(disk.total)}`)

🔧 **Active Queue:**
• Users in queue: `{len(queueDB)}`

🤖 **Bot:** @{Config.OWNER_USERNAME}"""
        
        await m.reply_text(stats_text, quote=True)
        
    except Exception as e:
        LOGGER.error(f"Stats error: {e}")
        await m.reply_text(f"❌ **Error fetching stats:** `{str(e)}`", quote=True)

@mergeApp.on_message(filters.command(["settings"]) & filters.private)
async def settings_command(c: Client, m: Message):
    """Settings command"""
    user = UserSettings(m.from_user.id, m.from_user.first_name)
    
    if not user.allowed and m.from_user.id != int(Config.OWNER):
        await m.reply_text("🔐 **Access Required!** Please login first.")
        return
    
    # Trigger settings callback
    await callback_handler(c, type('obj', (object,), {
        'data': 'settings',
        'from_user': m.from_user,
        'message': m,
        'answer': lambda x, show_alert=False: None
    })())

@mergeApp.on_message(filters.command(["encode"]) & filters.private)
async def encode_command(c: Client, m: Message):
    """Encoding command - Start encoding mode"""
    user = UserSettings(m.from_user.id, m.from_user.first_name)
    
    if not user.allowed and m.from_user.id != int(Config.OWNER):
        await m.reply_text("🔐 **Access Required!** Please login first using `/login <password>`")
        return
    
    # Import encoding buttons
    from helpers.encode_buttons import get_encoding_mode_buttons
    
    await m.reply_text(
        "🎬 **Video Encoding Mode**\n\n"
        "📤 **Step 1:** Send me a video file to encode\n"
        "📊 **Step 2:** Select quality preset or custom settings\n"
        "⏳ **Step 3:** Wait for encoding to complete\n\n"
        "💡 **Features:**\n"
        "• Multiple quality presets (1080p/720p/480p)\n"
        "• H.264 and HEVC/H.265 codecs\n"
        "• Custom CRF, resolution, bitrate settings\n"
        "• Professional encoding with FFmpeg\n\n"
        "🚀 **Send a video to start!**",
        quote=True
    )

if __name__ == "__main__":
    LOGGER.info("🚀 Starting SSMERGE Bot...")
    mergeApp.run()
