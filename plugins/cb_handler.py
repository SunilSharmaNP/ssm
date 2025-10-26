import asyncio
import os
import time
from pyrogram import Client
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import MessageNotModified
from plugins.mergeVideoAudio import mergeAudio      
from plugins.mergeVideoSub import mergeSub            
from plugins.streams_extractor import streamsExtractor
from plugins.metadataEditor import handle_metadata_callback
from __init__ import (UPLOAD_AS_DOC, UPLOAD_TO_GOFILE, formatDB, gDict, 
                      queueDB, replyDB, LOGGER, MERGE_MODE)
from bot import delete_all
from config import Config
from helpers.utils import UserSettings
from plugins.mergeVideo import mergeNow

# Import GoFile uploader
try:
    from helpers.uploader import GofileUploader
    GOFILE_AVAILABLE = True
except ImportError:
    GOFILE_AVAILABLE = False
    LOGGER.warning("GoFile uploader not available")

@Client.on_callback_query()
async def callback_handler(c: Client, cb: CallbackQuery):
    """Enhanced callback handler with GoFile support and better error handling"""
    try:
        user_id = cb.from_user.id
        data = cb.data
        user = UserSettings(user_id, cb.from_user.first_name)

        # Check user permissions
        if user_id != int(Config.OWNER) and not user.allowed:
            await cb.answer("🔐 Access denied! Please login first.", show_alert=True)
            return

        LOGGER.info(f"Callback from user {user_id}: {data}")

        if data == "cancel":
            await handle_cancel(cb, user_id)

        elif data == "merge":
            await handle_merge_request(c, cb, user_id)

        elif data.startswith("rename"):
            await handle_rename(cb, user_id)

        elif data.startswith("upload"):
            await handle_upload_mode(cb, data, user_id)

        elif data.startswith("gofile"):
            await handle_gofile_toggle(cb, data, user_id)

        elif data == "settings":
            await show_settings_menu(cb, user)

        elif data == "help":
            await show_help_menu(cb)

        elif data == "about":
            await show_about_menu(cb)

        elif data == "back_to_start":
            await show_start_menu(c, cb)

        elif data == "close":
            await cb.message.delete()

        elif data == "toggle_upload_mode":
            # Toggle between Video and Document upload - SAVE TO DATABASE
            user.upload_as_doc = not user.upload_as_doc
            user.set()  # Save to database
            UPLOAD_AS_DOC[str(user_id)] = user.upload_as_doc  # Sync with in-memory dict
            mode_name = "Document" if user.upload_as_doc else "Video"
            await cb.answer(f"📤 Upload mode changed to: {mode_name}", show_alert=False)
            await show_settings_menu(cb, user)
        
        elif data == "metadata_toggle":
            # Toggle metadata editing
            from helpers.database import enableMetadataToggle
            user.edit_metadata = not user.edit_metadata
            user.set()  # Save to database
            enableMetadataToggle(user_id, user.edit_metadata)
            status = "Enabled" if user.edit_metadata else "Disabled"
            await cb.answer(f"📊 Metadata editing {status}", show_alert=False)
            await show_settings_menu(cb, user)
        
        elif data == "thumbnail_toggle":
            # Information about thumbnail
            if user.thumbnail:
                await cb.answer("🖼️ Thumbnail is set. Send a photo to update it.", show_alert=True)
            else:
                await cb.answer("🖼️ No thumbnail set. Send a photo to set one.", show_alert=True)
        
        elif data == "clear_queue":
            # Clear user queue
            if user_id in queueDB:
                queueDB[user_id] = {"videos": [], "subtitles": [], "audios": []}
                await cb.answer("🗑️ Queue cleared successfully!", show_alert=True)
            else:
                await cb.answer("📋 Queue is already empty!", show_alert=True)
            await show_settings_menu(cb, user)
        
        elif data == "rename_file":
            await cb.answer("✏️ Rename feature - Send custom filename after starting merge", show_alert=True)
        
        elif data.startswith("meta_"):
            # Handle metadata editing callbacks
            await handle_metadata_callback(c, cb)
        
        elif data == "mode_video":
            # Video + Video merge - SAVE TO DATABASE
            UPLOAD_TO_GOFILE.setdefault(str(user_id), False)
            UPLOAD_AS_DOC.setdefault(str(user_id), False)
            MERGE_MODE[user_id] = 1
            user.merge_mode = 1
            user.set()  # Save to database
            await cb.answer("🎥 Mode set: Video + Video", show_alert=False)
            await show_settings_menu(cb, user)

        elif data == "mode_audio":
            # Video + Audio merge - SAVE TO DATABASE
            UPLOAD_TO_GOFILE.setdefault(str(user_id), False)
            UPLOAD_AS_DOC.setdefault(str(user_id), False)
            MERGE_MODE[user_id] = 2
            user.merge_mode = 2
            user.set()  # Save to database
            await cb.answer("🎵 Mode set: Video + Audio", show_alert=False)
            await show_settings_menu(cb, user)

        elif data == "mode_subtitle":
            # Video + Subtitle merge - SAVE TO DATABASE
            UPLOAD_TO_GOFILE.setdefault(str(user_id), False)
            UPLOAD_AS_DOC.setdefault(str(user_id), False)
            MERGE_MODE[user_id] = 3
            user.merge_mode = 3
            user.set()  # Save to database
            await cb.answer("📝 Mode set: Video + Subtitle", show_alert=False)
            await show_settings_menu(cb, user)

        elif data == "mode_extract":
            # Extract streams - SAVE TO DATABASE
            UPLOAD_TO_GOFILE.setdefault(str(user_id), False)
            UPLOAD_AS_DOC.setdefault(str(user_id), False)
            MERGE_MODE[user_id] = 4
            user.merge_mode = 4
            user.set()  # Save to database
            await cb.answer("🔍 Mode set: Extract Streams", show_alert=False)
            await show_settings_menu(cb, user)

        elif data == "remove_stream":
            # Remove last added stream from queue
            q = queueDB.get(user_id, {})
            mode = MERGE_MODE.get(user_id, 1)
            if mode in (1,2,3):
                # Remove last video for video modes
                q["videos"].pop() if q["videos"] else None
            else:
                # Remove last subtitle/audio for extract mode
                q["subtitles"].pop() if q["subtitles"] else None
            queueDB[user_id] = q
            await cb.answer("🗑️ Last stream removed", show_alert=True)
            await show_settings_menu(cb, user)

        # ──────────────────────────────────────────────────────────────
        elif data == "merge":
            # Start merge based on selected mode
            from plugins.mergeVideo import mergeNow
            from plugins.mergeVideoAudio import mergeAudioNow
            from plugins.mergeVideoSub import mergeSubNow
            from plugins.streams_extractor import extractStreamsNow

            mode = MERGE_MODE.get(user_id, 1)
            if mode == 1:
                await mergeNow(c, cb, f"downloads/{user_id}/merged.mkv")
            elif mode == 2:
                await mergeAudioNow(c, cb, f"downloads/{user_id}/merged_audio.mkv")
            elif mode == 3:
                await mergeSubNow(c, cb, f"downloads/{user_id}/merged_subtitle.mkv")
            elif mode == 4:
                await extractStreamsNow(c, cb)
            else:
                await cb.answer("⚠️ Invalid mode", show_alert=True)

        # ──────────────────────────────────────────────────────────────

        else:
            await cb.answer("🚧 Feature coming soon!", show_alert=True)

    except Exception as e:
        LOGGER.error(f"Callback handler error: {e}")
        try:
            await cb.answer("❌ Something went wrong! Please try again.", show_alert=True)
        except:
            pass

async def handle_cancel(cb: CallbackQuery, user_id: int):
    """Handle cancel operation with proper cleanup"""
    try:
        # Clear user data
        if user_id in queueDB:
            queueDB[user_id] = {"videos": [], "subtitles": [], "audios": []}

        if user_id in formatDB:
            formatDB[user_id] = None

        if user_id in replyDB:
            del replyDB[user_id]

        # Clear upload preferences
        if str(user_id) in UPLOAD_AS_DOC:
            del UPLOAD_AS_DOC[str(user_id)]

        if str(user_id) in UPLOAD_TO_GOFILE:
            del UPLOAD_TO_GOFILE[str(user_id)]

        # Delete download directory
        delete_all(root=f"downloads/{str(user_id)}")

        await cb.message.edit_text(
            "🗑️ **Operation Cancelled**\n\n"
            "✅ All files and settings cleared\n"
            "📤 Ready for new merge request"
        )

        LOGGER.info(f"Cancelled operation for user {user_id}")

    except Exception as e:
        LOGGER.error(f"Cancel handler error: {e}")
        await cb.answer("❌ Error during cancellation", show_alert=True)

async def handle_merge_request(c: Client, cb: CallbackQuery, user_id: int):
    """Handle merge request with better UI"""
    try:
        # Check if user has videos to merge
        if user_id not in queueDB or not queueDB[user_id]["videos"]:
            await cb.answer("❌ No videos found to merge!", show_alert=True)
            return

        videos_count = len(queueDB[user_id]["videos"])

        # Show merge options with GoFile integration
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Upload to Telegram", callback_data="upload_telegram")],
            [InlineKeyboardButton("🔗 Upload to GoFile", callback_data="upload_gofile")],
            [InlineKeyboardButton("📁 Upload as Document", callback_data="upload_document"),
             InlineKeyboardButton("🎬 Upload as Video", callback_data="upload_video")],
            [InlineKeyboardButton("✏️ Custom Name", callback_data="rename_custom"),
             InlineKeyboardButton("📝 Default Name", callback_data="rename_default")],
            [InlineKeyboardButton("🔙 Back", callback_data="show_queue")]
        ])

        await cb.message.edit_text(
            f"🔀 **Ready to Merge!**\n\n"
            f"📹 **Videos:** `{videos_count}`\n"
            f"📊 **Mode:** Video Merge\n\n"
            f"**Choose upload method:**",
            reply_markup=keyboard
        )

    except Exception as e:
        LOGGER.error(f"Merge request error: {e}")
        await cb.answer("❌ Error preparing merge", show_alert=True)

async def handle_upload_mode(cb: CallbackQuery, data: str, user_id: int):
    """Handle upload mode selection"""
    try:
        if data == "upload_telegram":
            UPLOAD_TO_GOFILE[str(user_id)] = False
            await cb.answer("📤 Telegram upload selected", show_alert=False)

        elif data == "upload_gofile":
            if GOFILE_AVAILABLE:
                UPLOAD_TO_GOFILE[str(user_id)] = True
                await cb.answer("🔗 GoFile upload selected", show_alert=False)
            else:
                await cb.answer("❌ GoFile not available", show_alert=True)
                return

        elif data == "upload_document":
            UPLOAD_AS_DOC[str(user_id)] = True
            await cb.answer("📁 Document mode selected", show_alert=False)

        elif data == "upload_video":
            UPLOAD_AS_DOC[str(user_id)] = False
            await cb.answer("🎬 Video mode selected", show_alert=False)

        # Start merging process
        await start_merge_process(cb, user_id)

    except Exception as e:
        LOGGER.error(f"Upload mode error: {e}")
        await cb.answer("❌ Error setting upload mode", show_alert=True)

async def handle_gofile_toggle(cb: CallbackQuery, data: str, user_id: int):
    """Handle GoFile toggle with database persistence"""
    try:
        user = UserSettings(user_id, cb.from_user.first_name)
        
        if not GOFILE_AVAILABLE:
            await cb.answer("❌ GoFile integration not available", show_alert=True)
            return

        # Toggle GoFile status - SAVE TO DATABASE
        user.upload_to_drive = not user.upload_to_drive
        user.set()  # Save to database
        UPLOAD_TO_GOFILE[str(user_id)] = user.upload_to_drive  # Sync with in-memory dict
        
        status_text = "enabled" if user.upload_to_drive else "disabled"
        await cb.answer(f"🔗 GoFile upload {status_text}", show_alert=False)

        # Refresh settings menu
        await show_settings_menu(cb, user)

    except Exception as e:
        LOGGER.error(f"GoFile toggle error: {e}")
        await cb.answer("❌ Error toggling GoFile", show_alert=True)

async def handle_rename(cb: CallbackQuery, user_id: int):
    """Handle file renaming"""
    try:
        if cb.data == "rename_default":
            # Use default name
            file_name = f"downloads/{user_id}/[@{Config.OWNER_USERNAME}]_merged.mkv"
            await start_merge_with_name(cb, user_id, file_name)

        elif cb.data == "rename_custom":
            await cb.message.edit_text(
                "✏️ **Custom File Name**\n\n"
                "📝 Reply with your desired filename\n"
                "⚠️ Don't include file extension\n\n"
                "**Example:** `My Merged Video`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="merge")]
                ])
            )
            # Note: This would need to be handled in a separate message handler

    except Exception as e:
        LOGGER.error(f"Rename error: {e}")
        await cb.answer("❌ Error handling rename", show_alert=True)

async def start_merge_process(cb: CallbackQuery, user_id: int):
    """Start the actual merge process"""
    try:
        # Generate default filename
        timestamp = int(time.time())
        file_name = f"downloads/{user_id}/[@{Config.OWNER_USERNAME}]_{timestamp}.mkv"

        await start_merge_with_name(cb, user_id, file_name)

    except Exception as e:
        LOGGER.error(f"Start merge error: {e}")
        await cb.answer("❌ Error starting merge process", show_alert=True)

async def start_merge_with_name(cb: CallbackQuery, user_id: int, file_name: str):
    """Start merge with specified filename"""
    try:
        await cb.message.edit_text("🔄 **Starting merge process...**\n\nPlease wait...")

        # Import and call merge function
        from plugins.mergeVideo import mergeNow
        await mergeNow(cb.client, cb, file_name)

    except Exception as e:
        LOGGER.error(f"Merge with name error: {e}")
        await cb.message.edit_text(
            f"❌ **Merge Failed!**\n\n"
            f"🚨 **Error:** `{str(e)}`\n\n"
            f"💡 Please try again or contact support."
        )

async def show_settings_menu(cb: CallbackQuery, user: UserSettings):
    """Show enhanced settings menu with proper database persistence"""
    try:
        # Get current settings DIRECTLY FROM DATABASE (UserSettings object)
        upload_mode = "Document 📁" if user.upload_as_doc else "Video 📹"
        gofile_status = "Enabled ✅" if user.upload_to_drive else "Disabled ❌"
        
        # Sync in-memory dicts with database values for backward compatibility
        UPLOAD_AS_DOC[str(user.user_id)] = user.upload_as_doc
        UPLOAD_TO_GOFILE[str(user.user_id)] = user.upload_to_drive
        
        # Get merge mode from user settings
        mode_names = {
            1: "Video + Video 🎬",
            2: "Video + Audio 🎵",
            3: "Video + Subtitle 📝",
            4: "Extract Streams 🔍"
        }
        current_mode = mode_names.get(user.merge_mode, "Video + Video 🎬")
        
        # Check metadata status
        metadata_status = "Enabled ✅" if user.edit_metadata else "Disabled ❌"
        
        # Check thumbnail status
        thumbnail_status = "Set ✅" if user.thumbnail else "Not Set ❌"

        settings_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📤 Upload: {upload_mode}", callback_data="toggle_upload_mode")],
            [InlineKeyboardButton("🎥 Video+Video", callback_data="mode_video"),
             InlineKeyboardButton("🎵 Video+Audio", callback_data="mode_audio")],
            [InlineKeyboardButton("📝 Video+Subtitle", callback_data="mode_subtitle"),
             InlineKeyboardButton("🔍 Extract", callback_data="mode_extract")],
            [InlineKeyboardButton(f"🖼️ Thumbnail: {thumbnail_status}", callback_data="thumbnail_toggle")],
            [InlineKeyboardButton(f"📊 Metadata: {metadata_status}", callback_data="metadata_toggle")],
            [InlineKeyboardButton(f"🔗 GoFile: {gofile_status}", callback_data="gofile_toggle")],
            [InlineKeyboardButton("🗑️ Clear Queue", callback_data="clear_queue"),
             InlineKeyboardButton("✏️ Rename", callback_data="rename_file")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_start"),
             InlineKeyboardButton("❌ Close", callback_data="close")]
        ])

        settings_text = f"""⚙️ **USER SETTINGS & PREFERENCES**

👤 **User:** {user.name}
🆔 **ID:** `{user.user_id}`
🔐 **Status:** {"Banned ❌" if user.banned else "Active ✅"}

**📤 UPLOAD SETTINGS:**
• Upload As: {upload_mode}
• GoFile Upload: {gofile_status}

**🎬 MERGE SETTINGS:**
• Current Mode: {current_mode}
• Metadata Edit: {metadata_status}
• Custom Thumbnail: {thumbnail_status}

**💡 TIP:** All settings are automatically saved to database"""

        await cb.message.edit_text(settings_text, reply_markup=settings_keyboard)

    except Exception as e:
        LOGGER.error(f"Settings menu error: {e}")
        await cb.answer("❌ Error loading settings", show_alert=True)

async def show_help_menu(cb: CallbackQuery):
    """Show help menu"""
    help_text = """❓ **HELP & USER GUIDE**

**📹 VIDEO MERGING:**
1️⃣ Send 2 or more video files
2️⃣ Files will be added to queue automatically
3️⃣ Click "🔥 Merge Now" button
4️⃣ Choose your upload preferences
5️⃣ Wait for processing (may take time for large files)

**📤 UPLOAD METHODS:**
• **Telegram:** Direct upload to chat (2GB limit for regular users)
• **GoFile:** External cloud storage (unlimited size, 10-day expiry)
• **Document Mode:** Upload as file (preserves quality)
• **Video Mode:** Upload as video (with streaming support)

**⚙️ SETTINGS OPTIONS:**
• Merge Mode: Video+Video / Video+Audio / Video+Subtitle
• Upload Method: Telegram or GoFile
• File Type: Video or Document
• Custom Thumbnails: Set before merging
• Rename: Custom or default naming

**🔧 ADVANCED FEATURES:**
• Extract audio/video streams
• Add subtitles to videos
• Merge audio tracks
• Custom file naming
• Metadata preservation

**💡 PRO TIPS:**
• Use GoFile for files larger than 2GB
• Set custom thumbnail for better presentation
• Use Document mode for highest quality
• Check queue before merging
• Clear queue if you want to start over

**🆘 TROUBLESHOOTING:**
• If merge fails, check file formats
• For large files, use GoFile upload
• Contact owner if persistent issues"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
    ])

    await cb.message.edit_text(help_text, reply_markup=keyboard)

async def show_about_menu(cb: CallbackQuery):
    """Show about menu"""
    about_text = """ℹ️ **ABOUT VIDEO TOOLS BOT**

🤖 **Version:** Professional Edition v3.0
⚡ **Powered by:** FFmpeg & Pyrogram

**🆕 Features:**
✅ Video merging (multiple files)
✅ Video + Audio merging
✅ Video + Subtitle merging
✅ Stream extraction
✅ Professional encoding
✅ GoFile integration (unlimited size)
✅ Custom thumbnails
✅ MongoDB user settings

**📋 Supported Formats:**
🎬 Videos: MP4, MKV, WebM, TS, MOV
🎵 Audio: AAC, AC3, MP3, M4A
📝 Subtitles: SRT, ASS, MKS

**⚙️ Advanced Options:**
• Upload to Telegram (2GB limit)
• Upload to GoFile (unlimited)
• Custom file naming
• Metadata editing
• Quality presets

**👨‍💻 Professional Bot Service**
**🔧 Technical Support Available**"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/yashoswalyo")],
        [InlineKeyboardButton("🏘 Source", url="https://github.com/yashoswalyo/MERGE-BOT"),
         InlineKeyboardButton("🤔 Owner", url=f"https://t.me/{Config.OWNER_USERNAME}")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
    ])

    await cb.message.edit_text(about_text, reply_markup=keyboard)

async def show_start_menu(c: Client, cb: CallbackQuery):
    """Show start menu"""
    user = UserSettings(cb.from_user.id, cb.from_user.first_name)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
         InlineKeyboardButton("📊 Stats", callback_data="bot_stats")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about"),
         InlineKeyboardButton("❓ Help", callback_data="help")],
        [InlineKeyboardButton("🔗 Owner", url=f"https://t.me/{Config.OWNER_USERNAME}")]
    ])

    await cb.message.edit_text(
        f"👋 **Welcome Back {cb.from_user.first_name}!**\n\n"
        f"🤖 **Professional Video Tools Bot**\n"
        f"📹 Your complete video processing solution\n\n"
        f"**Available Tools:**\n"
        f"• Video Merging & Combining\n"
        f"• Audio/Subtitle Integration\n"
        f"• Stream Extraction\n"
        f"• Quality Encoding\n"
        f"• Professional Processing\n\n"
        f"💡 **Quick Actions:** Settings | About | Help",
        reply_markup=keyboard
    )
