# mergeVideo.py - Modified to use separate downloader.py
import asyncio
import os
import time
from __init__ import (LOGGER, UPLOAD_AS_DOC, UPLOAD_TO_GOFILE, formatDB,
                      gDict, queueDB, replyDB)
from bot import delete_all
from config import Config
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from helpers.display_progress import Progress
from helpers.ffmpeg_helper import MergeSub, MergeVideo, take_screen_shot
from helpers.uploader import uploadVideo
from helpers.utils import UserSettings
from PIL import Image
from pyrogram import Client
from pyrogram.errors import MessageNotModified
from pyrogram.errors.rpc_error import UnknownError
from pyrogram.types import CallbackQuery

# Import our new downloader
from downloader import download_from_tg, download_from_url, cleanup_user_downloads

# Add a global lock to prevent concurrent processes per user
user_processes = {}

async def mergeNow(c: Client, cb: CallbackQuery, new_file_name: str):
    """Enhanced merge function with separate downloader integration and download mode enforcement"""
    user_id = cb.from_user.id
    
    # Check if user already has a process running
    if user_id in user_processes and user_processes[user_id]:
        await cb.answer("⚠️ Please wait! Your previous merge is still processing.", show_alert=True)
        return
    
    # Mark user as having an active process
    user_processes[user_id] = True
    
    try:
        # Get user settings for download mode enforcement
        user_settings = UserSettings(cb.from_user.id, cb.from_user.first_name)
        download_mode = user_settings.download_mode
        
        omess = cb.message.reply_to_message
        vid_list = list()
        sub_list = list()
        sIndex = 0
        await cb.message.edit("⭕ Processing...")
        duration = 0
        
        list_message_ids = queueDB.get(cb.from_user.id)["videos"]
        list_message_ids.sort()
        list_subtitle_ids = queueDB.get(cb.from_user.id)["subtitles"]
        
        LOGGER.info(Config.IS_PREMIUM)
        LOGGER.info(f"Videos: {list_message_ids}")
        LOGGER.info(f"Subs: {list_subtitle_ids}")
        
        if list_message_ids is None:
            await cb.answer("Queue Empty", show_alert=True)
            await cb.message.delete(True)
            return
        
        if not os.path.exists(f"downloads/{str(cb.from_user.id)}/"):
            os.makedirs(f"downloads/{str(cb.from_user.id)}/")
        
        input_ = f"downloads/{str(cb.from_user.id)}/input.txt"
        all = len(list_message_ids)
        n = 1
        
        # Process each video/URL in the queue
        for i in await c.get_messages(
            chat_id=cb.from_user.id, message_ids=list_message_ids):
            
            media = i.video or i.document
            file_dl_path = None
            sub_dl_path = None
            
            try:
                # Check if message contains URL or file
                if i.text and (i.text.startswith('http://') or i.text.startswith('https://')):
                    # Enforce download mode - block URLs in TG mode
                    if download_mode == "tg":
                        await cb.message.edit(
                            "🚫 **URL Blocked**\n\n"
                            "Your download mode is set to **TG File Only**.\n"
                            "This URL cannot be processed.\n\n"
                            "💡 Change to URL mode in /settings or send Telegram files only."
                        )
                        queueDB.get(cb.from_user.id)["videos"].remove(i.id)
                        await asyncio.sleep(5)
                        n += 1
                        continue
                    
                    # Handle Direct Download Link
                    await cb.message.edit(f"📥 Downloading URL ({n}/{all}): `{i.text[:50]}...`")
                    LOGGER.info(f"📥 Starting URL Download: {i.text}")
                    
                    # Use our new downloader for URLs
                    file_dl_path = await download_from_url(
                        url=i.text,
                        user_id=cb.from_user.id,
                        status_message=cb.message
                    )
                    
                    if not file_dl_path:
                        LOGGER.error(f"Failed to download URL: {i.text}")
                        queueDB.get(cb.from_user.id)["videos"].remove(i.id)
                        await cb.message.edit("❗URL Download Failed! Skipping...")
                        await asyncio.sleep(4)
                        n += 1
                        continue
                
                elif media:
                    # Enforce download mode - block TG files in URL mode
                    if download_mode == "url":
                        await cb.message.edit(
                            "🚫 **Telegram File Blocked**\n\n"
                            "Your download mode is set to **URL Download Only**.\n"
                            "This Telegram file cannot be processed.\n\n"
                            "💡 Change to TG File mode in /settings or send URLs only."
                        )
                        queueDB.get(cb.from_user.id)["videos"].remove(i.id)
                        await asyncio.sleep(5)
                        n += 1
                        continue
                    
                    # Handle Telegram File
                    await cb.message.edit(f"📥 Downloading TG File ({n}/{all}): `{media.file_name}`")
                    LOGGER.info(f"📥 Starting TG Download: {media.file_name}")
                    
                    # Use our new downloader for Telegram files
                    file_dl_path = await download_from_tg(
                        message=i,
                        user_id=cb.from_user.id,
                        status_message=cb.message
                    )
                    
                    if not file_dl_path:
                        LOGGER.error(f"Failed to download TG file: {media.file_name}")
                        queueDB.get(cb.from_user.id)["videos"].remove(i.id)
                        await cb.message.edit("❗TG Download Failed! Skipping...")
                        await asyncio.sleep(4)
                        n += 1
                        continue
                
                else:
                    LOGGER.warning(f"No downloadable content in message {i.id}")
                    queueDB.get(cb.from_user.id)["videos"].remove(i.id)
                    await cb.message.edit("❗No downloadable content! Skipping...")
                    await asyncio.sleep(4)
                    n += 1
                    continue
                
                n += 1
                
                if gDict[cb.message.chat.id] and cb.message.id in gDict[cb.message.chat.id]:
                    return
                
                await cb.message.edit(f"✅ Downloaded: `{os.path.basename(file_dl_path)}`")
                LOGGER.info(f"Downloaded Successfully: {os.path.basename(file_dl_path)}")
                await asyncio.sleep(2)
                
            except UnknownError as e:
                LOGGER.info(e)
                pass
            except Exception as downloadErr:
                LOGGER.info(f"Failed to download Error: {downloadErr}")
                queueDB.get(cb.from_user.id)["videos"].remove(i.id)
                await cb.message.edit("❗File Skipped!")
                await asyncio.sleep(4)
                continue
            
            # Handle subtitles if present
            if list_subtitle_ids[sIndex] is not None:
                a = await c.get_messages(
                    chat_id=cb.from_user.id, message_ids=list_subtitle_ids[sIndex]
                )
                sub_dl_path = await c.download_media(
                    message=a,
                    file_name=f"downloads/{str(cb.from_user.id)}/{str(a.id)}/",
                )
                LOGGER.info("Got sub: ", a.document.file_name)
                file_dl_path = await MergeSub(file_dl_path, sub_dl_path, cb.from_user.id)
                LOGGER.info("Added subs")
                sIndex += 1
            
            # Extract metadata
            metadata = extractMetadata(createParser(file_dl_path))
            try:
                if metadata.has("duration"):
                    duration += metadata.get("duration").seconds
                vid_list.append(f"file '{file_dl_path}'")
            except:
                await cleanup_user_data(cb.from_user.id)
                await cb.message.edit("⚠️ Video is corrupted")
                return
        
        # Remove duplicates
        _cache = list()
        for i in range(len(vid_list)):
            if vid_list[i] not in _cache:
                _cache.append(vid_list[i])
        vid_list = _cache
        
        LOGGER.info(f"Trying to merge videos user {cb.from_user.id}")
        await cb.message.edit(f"🔀 Merging videos... Please wait...")
        
        # Create input file for FFmpeg
        with open(input_, "w") as _list:
            _list.write("\n".join(vid_list))
        
        # Merge videos
        merged_video_path = await MergeVideo(
            input_file=input_, user_id=cb.from_user.id, message=cb.message, format_="mkv"
        )
        
        if merged_video_path is None:
            await cb.message.edit("❌ Failed to merge video!")
            await cleanup_user_data(cb.from_user.id)
            return
        
        try:
            await cb.message.edit("✅ Successfully Merged Video!")
        except MessageNotModified:
            await cb.message.edit("Successfully Merged Video! ✅")
        
        LOGGER.info(f"Video merged for: {cb.from_user.first_name}")
        await asyncio.sleep(3)
        
        # Rename file
        file_size = os.path.getsize(merged_video_path)
        os.rename(merged_video_path, new_file_name)
        await cb.message.edit(f"🔄 Renamed to: `{new_file_name.rsplit('/',1)[-1]}`")
        await asyncio.sleep(3)
        merged_video_path = new_file_name
        
        # Check file size limits
        if file_size > 2044723200 and Config.IS_PREMIUM == False:
            await cb.message.edit(
                f"📁 **File too large for regular Telegram!**\n\n"
                f"📊 **Size:** `{get_readable_file_size(file_size)}`\n"
                f"🚫 **Limit:** `2GB`\n\n"
                f"💡 **Tip:** Use GoFile upload option or contact admin for premium access."
            )
            await cleanup_user_data(cb.from_user.id)
            return
        
        if Config.IS_PREMIUM and file_size > 4241280205:
            await cb.message.edit(
                f"📁 **File too large even for premium!**\n\n"
                f"📊 **Size:** `{get_readable_file_size(file_size)}`\n"
                f"🚫 **Limit:** `4GB`\n\n"
                f"💡 **Tip:** Use GoFile upload option for larger files."
            )
            await cleanup_user_data(cb.from_user.id)
            return
        
        await cb.message.edit("🎥 Extracting Video Data...")
        duration = 1
        
        try:
            metadata = extractMetadata(createParser(merged_video_path))
            if metadata.has("duration"):
                duration = metadata.get("duration").seconds
        except Exception as er:
            await cleanup_user_data(cb.from_user.id)
            await cb.message.edit("⭕ Merged Video is corrupted")
            return
        
        # Handle thumbnail
        try:
            user = UserSettings(cb.from_user.id, cb.from_user.first_name)
            thumb_id = user.thumbnail
            if thumb_id is None:
                raise Exception
            video_thumbnail = f"downloads/{str(cb.from_user.id)}_thumb.jpg"
            await c.download_media(message=str(thumb_id), file_name=video_thumbnail)
        except Exception as err:
            LOGGER.info("Generating thumb")
            video_thumbnail = await take_screen_shot(
                merged_video_path, f"downloads/{str(cb.from_user.id)}", (duration / 2)
            )
        
        # Process thumbnail
        width = 1280
        height = 720
        try:
            thumb = extractMetadata(createParser(video_thumbnail))
            height = thumb.get("height")
            width = thumb.get("width")
            img = Image.open(video_thumbnail)
            if width > height:
                img.resize((320, height))
            elif height > width:
                img.resize((width, 320))
            img.save(video_thumbnail)
            Image.open(video_thumbnail).convert("RGB").save(video_thumbnail, "JPEG")
        except:
            await cleanup_user_data(cb.from_user.id)
            await cb.message.edit("⭕ Merged Video is corrupted")
            return
        
        # Upload the video
        await uploadVideo(
            c=c,
            cb=cb,
            merged_video_path=merged_video_path,
            width=width,
            height=height,
            duration=duration,
            video_thumbnail=video_thumbnail,
            file_size=os.path.getsize(merged_video_path),
            upload_mode=UPLOAD_AS_DOC[f"{cb.from_user.id}"],
        )
        
        await cb.message.delete(True)
        await cleanup_user_data(cb.from_user.id)
        
    except Exception as e:
        LOGGER.error(f"Merge process error: {e}")
        await cb.message.edit(f"❌ **Merge Failed!**\n\n🚨 **Error:** `{str(e)}`")
        await cleanup_user_data(cb.from_user.id)
    finally:
        # Always clear the user process flag
        if user_id in user_processes:
            user_processes[user_id] = False

async def cleanup_user_data(user_id):
    """Enhanced cleanup function with downloader integration"""
    try:
        await delete_all(root=f"downloads/{str(user_id)}")
        queueDB.update({user_id: {"videos": [], "subtitles": [], "audios": []}})
        formatDB.update({user_id: None})
        
        # Clear reply database
        if user_id in replyDB:
            del replyDB[user_id]
        
        # Clear process flag
        if user_id in user_processes:
            user_processes[user_id] = False
        
        # Use downloader cleanup function
        cleanup_user_downloads(user_id)
        
        LOGGER.info(f"Cleaned up data for user {user_id}")
    except Exception as e:
        LOGGER.error(f"Cleanup error for user {user_id}: {e}")

def get_readable_file_size(size_bytes):
    """Convert bytes to human readable format"""
    if size_bytes == 0:
        return "0B"
    size_name = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_name)-1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f}{size_name[i]}"
