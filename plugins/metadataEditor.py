#
# (c) Yash Oswal | yashoswal18@gmail.com

import os
import time
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from __init__ import LOGGER
from config import Config
from helpers.utils import UserSettings
from helpers.display_progress import Progress
import asyncio

# Store pending metadata changes per user
metadata_storage = {}


async def show_metadata_menu(c: Client, message: Message, user_id: int, msg_id: int, file_name: str, file_size: int):
    """Show metadata editing menu with current values"""
    metadata = metadata_storage.get(user_id, {}).get(msg_id, {})
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Edit Title", callback_data=f"meta_title_{msg_id}"),
         InlineKeyboardButton("👤 Edit Author", callback_data=f"meta_author_{msg_id}")],
        [InlineKeyboardButton("🎵 Edit Audio Title", callback_data=f"meta_audio_{msg_id}"),
         InlineKeyboardButton("📝 Edit Subtitle", callback_data=f"meta_subtitle_{msg_id}")],
        [InlineKeyboardButton("🎨 Edit Thumbnail", callback_data=f"meta_thumb_{msg_id}")],
        [InlineKeyboardButton("✅ Apply Changes", callback_data=f"meta_apply_{msg_id}"),
         InlineKeyboardButton("❌ Cancel", callback_data="close")]
    ])
    
    metadata_text = f"""📊 **Metadata Editor**

📁 **File:** `{file_name}`
📊 **Size:** `{file_size / (1024*1024):.2f} MB`

**Current Values:**
"""
    
    if metadata.get('title'):
        metadata_text += f"✏️ **Title:** `{metadata['title']}`\n"
    if metadata.get('author'):
        metadata_text += f"👤 **Author:** `{metadata['author']}`\n"
    if metadata.get('audio'):
        metadata_text += f"🎵 **Audio:** `{metadata['audio']}`\n"
    if metadata.get('subtitle'):
        metadata_text += f"📝 **Subtitle:** `{metadata['subtitle']}`\n"
    if metadata.get('thumbnail'):
        metadata_text += f"🎨 **Thumbnail:** Set\n"
    
    if not any([metadata.get('title'), metadata.get('author'), metadata.get('audio'), 
                metadata.get('subtitle'), metadata.get('thumbnail')]):
        metadata_text += "_(No changes yet)_\n"
    
    metadata_text += """
💡 **Instructions:**
1. Click on what you want to edit
2. Send the new value
3. Click "Apply Changes" when done

⚠️ **Note:** Changes will create a new file with updated metadata."""
    
    await message.edit_text(metadata_text, reply_markup=keyboard)


async def metaEditor(c: Client, m: Message):
    """
    Metadata Editor - Edit video metadata (title, author, audio, subtitle)
    Usage: Reply to a video with /metadata
    """
    try:
        user_id = m.from_user.id
        user = UserSettings(user_id, m.from_user.first_name)
        
        if not user.is_allowed():
            await m.reply_text(
                "🔐 **Access Denied!**\n\n"
                "❌ You don't have permission to use this bot.\n"
                "📝 Contact the owner for access.",
                quote=True
            )
            return
        
        if not m.reply_to_message:
            await m.reply_text(
                "❌ **Invalid Usage!**\n\n"
                "📝 **Correct Usage:**\n"
                "Reply to a video/document with `/metadata`\n\n"
                "**Example:**\n"
                "`/metadata` (reply to video)",
                quote=True
            )
            return
        
        replied_msg = m.reply_to_message
        
        if not (replied_msg.video or replied_msg.document):
            await m.reply_text(
                "❌ **No Media Found!**\n\n"
                "⚠️ Please reply to a video or document file.",
                quote=True
            )
            return
        
        media = replied_msg.video or replied_msg.document
        file_name = media.file_name or "video.mp4"
        file_size = media.file_size
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Edit Title", callback_data=f"meta_title_{replied_msg.id}"),
             InlineKeyboardButton("👤 Edit Author", callback_data=f"meta_author_{replied_msg.id}")],
            [InlineKeyboardButton("🎵 Edit Audio Title", callback_data=f"meta_audio_{replied_msg.id}"),
             InlineKeyboardButton("📝 Edit Subtitle", callback_data=f"meta_subtitle_{replied_msg.id}")],
            [InlineKeyboardButton("🎨 Edit Thumbnail", callback_data=f"meta_thumb_{replied_msg.id}")],
            [InlineKeyboardButton("✅ Apply Changes", callback_data=f"meta_apply_{replied_msg.id}"),
             InlineKeyboardButton("❌ Cancel", callback_data="close")]
        ])
        
        metadata_text = f"""📊 **Metadata Editor**

📁 **File:** `{file_name}`
📊 **Size:** `{file_size / (1024*1024):.2f} MB`

**Available Options:**
• Edit Video Title
• Edit Author/Artist Name  
• Edit Audio Track Title
• Edit Subtitle Language
• Change Thumbnail

💡 **Instructions:**
1. Click on what you want to edit
2. Send the new value
3. Click "Apply Changes" when done

⚠️ **Note:** Changes will create a new file with updated metadata."""

        await m.reply_text(
            metadata_text,
            reply_markup=keyboard,
            quote=True
        )
        
        # Initialize metadata storage for this user
        if user_id not in metadata_storage:
            metadata_storage[user_id] = {}
        metadata_storage[user_id][replied_msg.id] = {
            'title': None,
            'author': None,
            'audio': None,
            'subtitle': None,
            'thumbnail': None,
            'file_path': None,
            'file_name': file_name,
            'file_size': file_size
        }
        
        LOGGER.info(f"Metadata editor opened by user {user_id} for file: {file_name}")
        
    except Exception as e:
        LOGGER.error(f"Metadata editor error: {e}")
        await m.reply_text(
            f"❌ **Error!**\n\n"
            f"🚨 **Error:** `{str(e)}`\n"
            f"💡 **Tip:** Try again or contact support",
            quote=True
        )


async def handle_metadata_callback(c: Client, cb: CallbackQuery):
    """Handle metadata editing callbacks"""
    try:
        user_id = cb.from_user.id
        data = cb.data
        
        # Parse callback data
        parts = data.split('_')
        action = parts[1]  # title, author, audio, subtitle, thumb, apply
        msg_id = int(parts[2]) if len(parts) > 2 else None
        
        # Check if metadata storage exists
        if user_id not in metadata_storage or msg_id not in metadata_storage[user_id]:
            await cb.answer("⚠️ Session expired! Please restart /metadata", show_alert=True)
            return
        
        if action == 'title':
            await cb.answer("📝 Send the new video title:")
            await cb.message.edit_text(
                "✏️ **Edit Video Title**\n\n"
                "📝 Please send the new title for this video:\n\n"
                "💡 Example: `My Awesome Video 2025`\n\n"
                "⚠️ Send /cancel to cancel"
            )
            try:
                response = await c.listen(cb.message.chat.id, timeout=60)
                if response.text and response.text.startswith('/cancel'):
                    await response.reply_text("❌ Cancelled!")
                    metadata = metadata_storage[user_id][msg_id]
                    await show_metadata_menu(c, cb.message, user_id, msg_id, 
                                            metadata['file_name'], metadata['file_size'])
                    return
                metadata_storage[user_id][msg_id]['title'] = response.text
                await response.reply_text(f"✅ Title saved: `{response.text}`")
                metadata = metadata_storage[user_id][msg_id]
                await show_metadata_menu(c, cb.message, user_id, msg_id, 
                                        metadata['file_name'], metadata['file_size'])
            except asyncio.TimeoutError:
                await cb.message.reply_text("⏰ Timeout! Please try again.")
                metadata = metadata_storage[user_id][msg_id]
                await show_metadata_menu(c, cb.message, user_id, msg_id, 
                                        metadata['file_name'], metadata['file_size'])
                
        elif action == 'author':
            await cb.answer("👤 Send the new author name:")
            await cb.message.edit_text(
                "👤 **Edit Author/Artist**\n\n"
                "📝 Please send the new author/artist name:\n\n"
                "💡 Example: `John Doe`\n\n"
                "⚠️ Send /cancel to cancel"
            )
            try:
                response = await c.listen(cb.message.chat.id, timeout=60)
                if response.text and response.text.startswith('/cancel'):
                    await response.reply_text("❌ Cancelled!")
                    metadata = metadata_storage[user_id][msg_id]
                    await show_metadata_menu(c, cb.message, user_id, msg_id, 
                                            metadata['file_name'], metadata['file_size'])
                    return
                metadata_storage[user_id][msg_id]['author'] = response.text
                await response.reply_text(f"✅ Author saved: `{response.text}`")
                metadata = metadata_storage[user_id][msg_id]
                await show_metadata_menu(c, cb.message, user_id, msg_id, 
                                        metadata['file_name'], metadata['file_size'])
            except asyncio.TimeoutError:
                await cb.message.reply_text("⏰ Timeout! Please try again.")
                metadata = metadata_storage[user_id][msg_id]
                await show_metadata_menu(c, cb.message, user_id, msg_id, 
                                        metadata['file_name'], metadata['file_size'])
                
        elif action == 'audio':
            await cb.answer("🎵 Send the new audio title:")
            await cb.message.edit_text(
                "🎵 **Edit Audio Track Title**\n\n"
                "📝 Please send the new audio track title:\n\n"
                "💡 Example: `English Audio`\n\n"
                "⚠️ Send /cancel to cancel"
            )
            try:
                response = await c.listen(cb.message.chat.id, timeout=60)
                if response.text and response.text.startswith('/cancel'):
                    await response.reply_text("❌ Cancelled!")
                    metadata = metadata_storage[user_id][msg_id]
                    await show_metadata_menu(c, cb.message, user_id, msg_id, 
                                            metadata['file_name'], metadata['file_size'])
                    return
                metadata_storage[user_id][msg_id]['audio'] = response.text
                await response.reply_text(f"✅ Audio title saved: `{response.text}`")
                metadata = metadata_storage[user_id][msg_id]
                await show_metadata_menu(c, cb.message, user_id, msg_id, 
                                        metadata['file_name'], metadata['file_size'])
            except asyncio.TimeoutError:
                await cb.message.reply_text("⏰ Timeout! Please try again.")
                metadata = metadata_storage[user_id][msg_id]
                await show_metadata_menu(c, cb.message, user_id, msg_id, 
                                        metadata['file_name'], metadata['file_size'])
                
        elif action == 'subtitle':
            await cb.answer("📝 Send the subtitle language:")
            await cb.message.edit_text(
                "📝 **Edit Subtitle Language**\n\n"
                "📝 Please send the subtitle language:\n\n"
                "💡 Example: `English` or `Hindi`\n\n"
                "⚠️ Send /cancel to cancel"
            )
            try:
                response = await c.listen(cb.message.chat.id, timeout=60)
                if response.text and response.text.startswith('/cancel'):
                    await response.reply_text("❌ Cancelled!")
                    metadata = metadata_storage[user_id][msg_id]
                    await show_metadata_menu(c, cb.message, user_id, msg_id, 
                                            metadata['file_name'], metadata['file_size'])
                    return
                metadata_storage[user_id][msg_id]['subtitle'] = response.text
                await response.reply_text(f"✅ Subtitle saved: `{response.text}`")
                metadata = metadata_storage[user_id][msg_id]
                await show_metadata_menu(c, cb.message, user_id, msg_id, 
                                        metadata['file_name'], metadata['file_size'])
            except asyncio.TimeoutError:
                await cb.message.reply_text("⏰ Timeout! Please try again.")
                metadata = metadata_storage[user_id][msg_id]
                await show_metadata_menu(c, cb.message, user_id, msg_id, 
                                        metadata['file_name'], metadata['file_size'])
                
        elif action == 'thumb':
            await cb.answer("🎨 Send a photo for thumbnail:")
            await cb.message.edit_text(
                "🎨 **Edit Thumbnail**\n\n"
                "📸 Please send a photo to use as thumbnail:\n\n"
                "💡 Send a high-quality image\n\n"
                "⚠️ Send /cancel to cancel"
            )
            try:
                response = await c.listen(cb.message.chat.id, timeout=60)
                if response.text and response.text.startswith('/cancel'):
                    await response.reply_text("❌ Cancelled!")
                    metadata = metadata_storage[user_id][msg_id]
                    await show_metadata_menu(c, cb.message, user_id, msg_id, 
                                            metadata['file_name'], metadata['file_size'])
                    return
                if response.photo:
                    # Download thumbnail
                    thumb_path = f"downloads/{user_id}/thumb_{msg_id}.jpg"
                    os.makedirs(f"downloads/{user_id}", exist_ok=True)
                    await response.download(thumb_path)
                    metadata_storage[user_id][msg_id]['thumbnail'] = thumb_path
                    await response.reply_text(f"✅ Thumbnail saved!")
                    metadata = metadata_storage[user_id][msg_id]
                    await show_metadata_menu(c, cb.message, user_id, msg_id, 
                                            metadata['file_name'], metadata['file_size'])
                else:
                    await response.reply_text("❌ Please send a valid photo!")
                    metadata = metadata_storage[user_id][msg_id]
                    await show_metadata_menu(c, cb.message, user_id, msg_id, 
                                            metadata['file_name'], metadata['file_size'])
            except asyncio.TimeoutError:
                await cb.message.reply_text("⏰ Timeout! Please try again.")
                metadata = metadata_storage[user_id][msg_id]
                await show_metadata_menu(c, cb.message, user_id, msg_id, 
                                        metadata['file_name'], metadata['file_size'])
                
        elif action == 'apply':
            # Apply all metadata changes
            await apply_metadata_changes(c, cb, user_id, msg_id)
            
    except Exception as e:
        LOGGER.error(f"Metadata callback error: {e}")
        await cb.answer(f"❌ Error: {str(e)}", show_alert=True)


async def apply_metadata_changes(c: Client, cb: CallbackQuery, user_id: int, msg_id: int):
    """Apply metadata changes using FFmpeg and send updated file"""
    try:
        await cb.answer("⚙️ Applying metadata changes...")
        await cb.message.edit_text("⚙️ **Processing...**\n\n🔄 Downloading file...")
        
        # Get original message
        original_msg = await c.get_messages(user_id, msg_id)
        if not (original_msg.video or original_msg.document):
            await cb.message.edit_text("❌ Original file not found!")
            return
        
        media = original_msg.video or original_msg.document
        file_name = media.file_name or "video.mp4"
        
        # Download original file
        download_dir = f"downloads/{user_id}"
        os.makedirs(download_dir, exist_ok=True)
        input_file = f"{download_dir}/input_{msg_id}.mp4"
        
        await cb.message.edit_text("⚙️ **Processing...**\n\n⬇️ Downloading original file...")
        c_time = time.time()
        prog = Progress(user_id, c, cb.message)
        await c.download_media(
            message=media,
            file_name=input_file,
            progress=prog.progress_for_pyrogram,
            progress_args=("📥 Downloading", c_time)
        )
        
        # Build FFmpeg command
        output_file = f"{download_dir}/output_{msg_id}.mp4"
        metadata = metadata_storage[user_id][msg_id]
        
        ffmpeg_cmd = ["ffmpeg", "-i", input_file]
        
        # Add thumbnail if provided
        if metadata['thumbnail']:
            ffmpeg_cmd.extend(["-i", metadata['thumbnail']])
        
        # Add metadata flags
        ffmpeg_cmd.extend(["-map", "0"])
        if metadata['thumbnail']:
            ffmpeg_cmd.extend(["-map", "1", "-disposition:v:1", "attached_pic"])
        
        # Add metadata options
        if metadata['title']:
            ffmpeg_cmd.extend(["-metadata", f"title={metadata['title']}"])
        if metadata['author']:
            ffmpeg_cmd.extend(["-metadata", f"artist={metadata['author']}"])
            ffmpeg_cmd.extend(["-metadata", f"author={metadata['author']}"])
        if metadata['audio']:
            ffmpeg_cmd.extend(["-metadata:s:a:0", f"title={metadata['audio']}"])
        if metadata['subtitle']:
            ffmpeg_cmd.extend(["-metadata:s:s:0", f"language={metadata['subtitle']}"])
        
        # Copy codecs to avoid re-encoding
        ffmpeg_cmd.extend(["-c", "copy", output_file, "-y"])
        
        await cb.message.edit_text("⚙️ **Processing...**\n\n⚙️ Applying metadata changes...")
        
        # Execute FFmpeg
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"FFmpeg failed: {stderr.decode()[:200]}")
        
        # Upload modified file
        await cb.message.edit_text("⚙️ **Processing...**\n\n⬆️ Uploading modified file...")
        
        caption = f"✅ **Metadata Updated**\n\n"
        if metadata['title']:
            caption += f"📝 **Title:** {metadata['title']}\n"
        if metadata['author']:
            caption += f"👤 **Author:** {metadata['author']}\n"
        if metadata['audio']:
            caption += f"🎵 **Audio:** {metadata['audio']}\n"
        if metadata['subtitle']:
            caption += f"📝 **Subtitle:** {metadata['subtitle']}\n"
        
        # Send file
        c_time = time.time()
        prog = Progress(user_id, c, cb.message)
        await c.send_document(
            chat_id=user_id,
            document=output_file,
            caption=caption,
            progress=prog.progress_for_pyrogram,
            progress_args=("📤 Uploading", c_time)
        )
        
        await cb.message.edit_text("✅ **Metadata updated successfully!**\n\n"
                                   "📁 Updated file has been sent!")
        
        # Cleanup
        try:
            os.remove(input_file)
            os.remove(output_file)
            if metadata['thumbnail']:
                os.remove(metadata['thumbnail'])
            del metadata_storage[user_id][msg_id]
        except:
            pass
            
    except Exception as e:
        LOGGER.error(f"Apply metadata error: {e}")
        await cb.message.edit_text(f"❌ **Error applying changes:**\n\n`{str(e)}`")
