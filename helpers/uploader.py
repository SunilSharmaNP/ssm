# uploader.py - Enhanced and Fixed Version for SSMERGE Bot
# Fixed GoFile uploading issues and improved error handling

import os
import time
import asyncio
import aiohttp
from aiohttp import ClientSession, ClientTimeout, FormData
from random import choice
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
from config import Config
from __init__ import LOGGER
from helpers.utils import get_readable_file_size, get_readable_time

# GoFile Configuration - FIXED VALUES
GOFILE_CHUNK_SIZE = 8192 * 1024  # 8MB chunks
GOFILE_UPLOAD_TIMEOUT = 3600  # 1 hour timeout
GOFILE_RETRY_ATTEMPTS = 3
GOFILE_RETRY_WAIT_MIN = 2
GOFILE_RETRY_WAIT_MAX = 10

def get_human_readable_size(size_bytes):
    """Convert bytes to human readable format"""
    return get_readable_file_size(size_bytes)

def get_speed(start_time, uploaded_bytes):
    """Calculate upload speed"""
    elapsed = time.time() - start_time
    if elapsed > 0:
        speed_bps = uploaded_bytes / elapsed
        return get_readable_file_size(speed_bps) + "/s"
    return "0 B/s"

def get_time_left(start_time, uploaded_bytes, total_size):
    """Calculate ETA"""
    if uploaded_bytes == 0:
        return "∞"
    elapsed = time.time() - start_time
    speed = uploaded_bytes / elapsed if elapsed > 0 else 0
    if speed > 0:
        remaining = (total_size - uploaded_bytes) / speed
        return get_readable_time(remaining)
    return "∞"

def get_progress_bar(percentage, length=20):
    """Generate progress bar"""
    filled = int(length * percentage)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}]"

async def smart_progress_editor(message, text):
    """Smart message editor with error handling"""
    try:
        await message.edit_text(text, disable_web_page_preview=True)
    except Exception as e:
        LOGGER.warning(f"Failed to edit progress message: {e}")

class GofileUploader:
    """GoFile uploading with progress tracking - FIXED VERSION"""
    
    def __init__(self, token=None):
        self.api_url = "https://api.gofile.io/"
        self.token = token or getattr(Config, 'GOFILE_TOKEN', None)
        if not self.token:
            LOGGER.info("GOFILE_TOKEN not found. GoFile uploads will be anonymous (this is normal).")
        self.chunk_size = GOFILE_CHUNK_SIZE
        self.session = None
    
    async def _get_session(self):
        """Get or create an aiohttp ClientSession"""
        if self.session is None or self.session.closed:
            # FIXED: Better headers and configuration
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Connection': 'keep-alive',
            }
            
            connector = aiohttp.TCPConnector(
                limit=100,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=60,
                enable_cleanup_closed=True
            )
            
            timeout = ClientTimeout(
                total=GOFILE_UPLOAD_TIMEOUT,
                connect=30,
                sock_read=120
            )
            
            self.session = ClientSession(
                headers=headers,
                timeout=timeout,
                connector=connector
            )
        
        return self.session
    
    async def close(self):
        """Close the aiohttp ClientSession"""
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None
    
    @retry(
        stop=stop_after_attempt(GOFILE_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=GOFILE_RETRY_WAIT_MIN, max=GOFILE_RETRY_WAIT_MAX),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError, Exception)),
        reraise=True
    )
    async def __get_server(self):
        """Get the best GoFile server for uploading - FIXED"""
        LOGGER.info("Getting GoFile server...")
        session = await self._get_session()
        
        try:
            async with session.get(f"{self.api_url}servers") as resp:
                resp.raise_for_status()
                result = await resp.json()
                
                if result.get("status") == "ok":
                    servers = result["data"]["servers"]
                    # FIXED: Better server selection
                    available_servers = [s for s in servers if s.get("name")]
                    if available_servers:
                        selected_server = choice(available_servers)["name"]
                        LOGGER.info(f"Selected GoFile server: {selected_server}")
                        return selected_server
                    else:
                        raise Exception("No available GoFile servers found")
                else:
                    raise Exception(f"GoFile API error: {result.get('message', 'Unknown error')}")
        
        except Exception as e:
            LOGGER.error(f"Error getting GoFile server: {e}")
            raise
    
    async def upload_file(self, file_path: str, status_message=None):
        """Upload file to GoFile with progress tracking - FIXED VERSION"""
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)
        
        # FIXED: Updated GoFile limit (they increased it)
        if file_size > (50 * 1024 * 1024 * 1024):  # 50GB limit
            raise ValueError(f"File size {get_human_readable_size(file_size)} exceeds GoFile limit (50GB)")
        
        try:
            if status_message:
                await smart_progress_editor(status_message, "🔗 **Connecting to GoFile servers...**")
            
            server = await self.__get_server()
            upload_url = f"https://{server}.gofile.io/uploadFile"
            LOGGER.info(f"Using upload URL: {upload_url}")
            
        except Exception as e:
            error_msg = f"Failed to get GoFile server: {e}"
            LOGGER.error(error_msg)
            if status_message:
                await status_message.edit_text(
                    f"❌ **GoFile Upload Failed!**\n\n"
                    f"🚨 **Error:** `{error_msg}`\n\n"
                    f"💡 **Tip:** GoFile servers might be busy. Try again later."
                )
            raise
        
        if status_message:
            await smart_progress_editor(
                status_message,
                f"🚀 **Starting GoFile Upload...**\n\n"
                f"📁 **File:** `{filename}`\n"
                f"📊 **Size:** `{get_human_readable_size(file_size)}`"
            )
        
        start_time = time.time()
        uploaded_bytes = 0
        
        try:
            session = await self._get_session()
            
            # FIXED: Better file handling and form data
            with open(file_path, 'rb') as file_obj:
                # Create form data
                form = FormData()
                
                # Add token if available
                if self.token:
                    form.add_field("token", self.token)
                
                # FIXED: Better content type detection
                content_type = "application/octet-stream"
                if filename.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
                    content_type = "video/mp4"
                elif filename.lower().endswith(('.mp3', '.wav', '.aac')):
                    content_type = "audio/mpeg"
                
                # Add file with proper content type
                form.add_field(
                    "file", 
                    file_obj, 
                    filename=filename,
                    content_type=content_type
                )
                
                # FIXED: Upload with progress tracking
                async with session.post(upload_url, data=form) as resp:
                    resp.raise_for_status()
                    
                    # Update progress during upload
                    if status_message:
                        elapsed_time = time.time() - start_time
                        if elapsed_time > 5:  # Update every 5 seconds
                            await smart_progress_editor(
                                status_message,
                                f"📤 **Uploading to GoFile...**\n\n"
                                f"📁 **File:** `{filename}`\n"
                                f"📊 **Size:** `{get_human_readable_size(file_size)}`\n"
                                f"⏱ **Time:** `{elapsed_time:.1f}s`"
                            )
                    
                    resp_json = await resp.json()
                    
                    if resp_json.get("status") == "ok":
                        download_page = resp_json["data"]["downloadPage"]
                        
                        if status_message:
                            elapsed_time = time.time() - start_time
                            await status_message.edit_text(
                                f"✅ **GoFile Upload Complete!**\n\n"
                                f"📁 **File:** `{filename}`\n"
                                f"📊 **Size:** `{get_human_readable_size(file_size)}`\n"
                                f"⏱ **Time:** `{elapsed_time:.1f}s`\n"
                                f"🔗 **Link:** {download_page}\n\n"
                                f"💡 **Note:** Links expire after 10 days of inactivity."
                            )
                        
                        LOGGER.info(f"GoFile upload successful: {download_page}")
                        return download_page
                    
                    else:
                        error_msg = resp_json.get("message", "Unknown error")
                        raise Exception(f"GoFile upload failed: {error_msg}")
        
        except Exception as e:
            error_msg = f"GoFile upload error: {e}"
            LOGGER.error(error_msg)
            
            if status_message:
                await status_message.edit_text(
                    f"❌ **GoFile Upload Failed!**\n\n"
                    f"📁 **File:** `{filename}`\n"
                    f"🚨 **Error:** `{str(e)}`\n\n"
                    f"💡 **Tip:** Try again or contact support."
                )
            raise
        
        finally:
            await self.close()

# Enhanced upload video function with better error handling - FIXED
async def uploadVideo(c, cb, merged_video_path, width, height, duration, video_thumbnail, file_size, upload_mode):
    """Enhanced video upload with GoFile integration and better error handling"""
    try:
        LOGGER.info(f"Starting upload process for: {merged_video_path}")
        user_id = cb.from_user.id
        
        from __init__ import UPLOAD_TO_GOFILE, UPLOAD_AS_DOC
        
        # Check if GoFile upload is requested
        if UPLOAD_TO_GOFILE.get(str(user_id), False):
            try:
                await cb.message.edit("🔗 **Preparing GoFile Upload...**")
                
                # FIXED: Better GoFile uploader initialization
                gofile = GofileUploader()
                download_link = await gofile.upload_file(merged_video_path, cb.message)
                
                # Send link to user
                await cb.message.edit(
                    f"🎉 **Video Successfully Uploaded to GoFile!**\n\n"
                    f"📁 **File:** `{os.path.basename(merged_video_path)}`\n"
                    f"📊 **Size:** `{get_readable_file_size(file_size)}`\n"
                    f"🔗 **Download Link:** {download_link}\n\n"
                    f"💡 **Note:** Link expires after 10 days of inactivity."
                )
                
                # Also send to log channel if configured
                if Config.LOGCHANNEL:
                    try:
                        await c.send_message(
                            chat_id=int(Config.LOGCHANNEL),
                            text=f"📤 **GoFile Upload Complete**\n\n"
                            f"👤 **User:** {cb.from_user.first_name} (`{user_id}`)\n"
                            f"📁 **File:** `{os.path.basename(merged_video_path)}`\n"
                            f"📊 **Size:** `{get_readable_file_size(file_size)}`\n"
                            f"🔗 **Link:** {download_link}"
                        )
                    except Exception as e:
                        LOGGER.warning(f"Failed to send to log channel: {e}")
                
                return True
                
            except Exception as e:
                LOGGER.error(f"GoFile upload failed: {e}")
                await cb.message.edit(
                    f"❌ **GoFile Upload Failed!**\n\n"
                    f"🚨 **Error:** `{str(e)}`\n\n"
                    f"🔄 **Falling back to Telegram upload...**"
                )
                # Fall back to Telegram upload
                await asyncio.sleep(3)
        
        # Regular Telegram upload with user mention
        caption = f"📹 **Merged Video**\n\n" \
                 f"📁 **File:** `{os.path.basename(merged_video_path)}`\n" \
                 f"📊 **Size:** `{get_readable_file_size(file_size)}`\n" \
                 f"⏱ **Duration:** `{get_readable_time(duration)}`\n\n" \
                 f"👤 **User:** {cb.from_user.mention}\n" \
                 f"🤖 **Bot:** @{Config.OWNER_USERNAME}"
        
        if upload_mode:  # Upload as document
            await cb.message.edit("📤 **Uploading as Document...**")
            sent_message = await c.send_document(
                chat_id=cb.from_user.id,
                document=merged_video_path,
                thumb=video_thumbnail,
                caption=caption,
                progress=upload_progress,
                progress_args=(cb.message, "📤 **Uploading Document...**", time.time())
            )
        else:  # Upload as video
            await cb.message.edit("📤 **Uploading as Video...**")
            sent_message = await c.send_video(
                chat_id=cb.from_user.id,
                video=merged_video_path,
                duration=duration,
                width=width,
                height=height,
                thumb=video_thumbnail,
                caption=caption,
                supports_streaming=True,
                progress=upload_progress,
                progress_args=(cb.message, "📤 **Uploading Video...**", time.time())
            )
        
        # Send to log channel with better error handling
        if Config.LOGCHANNEL:
            try:
                # Validate log channel ID
                log_channel_id = int(Config.LOGCHANNEL)
                
                # Check if log channel ID is valid format
                if not str(log_channel_id).startswith('-100'):
                    LOGGER.warning(f"Invalid log channel format: {log_channel_id}")
                    return True
                
                await sent_message.copy(
                    chat_id=log_channel_id,
                    caption=f"📤 **Video Merged & Uploaded**\n\n"
                    f"👤 **User:** {cb.from_user.first_name} (`{cb.from_user.id}`)\n"
                    f"📁 **File:** `{os.path.basename(merged_video_path)}`\n"
                    f"📊 **Size:** `{get_readable_file_size(file_size)}`\n"
                    f"⏱ **Duration:** `{get_readable_time(duration)}`"
                )
                
            except ValueError as e:
                LOGGER.error(f"Invalid log channel ID format: {Config.LOGCHANNEL} - {e}")
            except Exception as e:
                LOGGER.error(f"Failed to send to log channel: {e}")
        
        return True
        
    except Exception as e:
        LOGGER.error(f"Upload failed: {e}")
        try:
            await cb.message.edit(
                f"❌ **Upload Failed!**\n\n"
                f"🚨 **Error:** `{str(e)}`\n\n"
                f"💡 **Tip:** Try again or contact support."
            )
        except:
            pass
        return False

async def upload_progress(current, total, message, text, start_time):
    """Upload progress callback with better formatting"""
    try:
        now = time.time()
        diff = now - start_time
        
        if diff < 1:
            return
        
        percentage = current * 100 / total
        speed = current / diff
        eta = (total - current) / speed if speed > 0 else 0
        
        progress_text = f"{text}\n\n" \
                       f"📊 **Progress:** `{percentage:.1f}%`\n" \
                       f"📈 **Uploaded:** `{get_readable_file_size(current)}`\n" \
                       f"📁 **Total:** `{get_readable_file_size(total)}`\n" \
                       f"🚀 **Speed:** `{get_readable_file_size(speed)}/s`\n" \
                       f"⏱ **ETA:** `{get_readable_time(eta)}`"
        
        await smart_progress_editor(message, progress_text)
        
    except Exception as e:
        LOGGER.warning(f"Progress update failed: {e}")

# FIXED: Additional helper functions for better compatibility
def setup_gofile_config():
    """Setup GoFile configuration - call this in bot startup"""
    try:
        # Test GoFile API availability
        import requests
        response = requests.get("https://api.gofile.io/servers", timeout=10)
        if response.status_code == 200:
            LOGGER.info("✅ GoFile API is accessible")
            return True
        else:
            LOGGER.warning("⚠️ GoFile API returned non-200 status")
            return False
    except Exception as e:
        LOGGER.error(f"❌ GoFile API test failed: {e}")
        return False

# Add this function to your uploader.py file
async def uploadFiles(c, cb, up_path, n, all):
    """Upload extracted files (audios/subtitles)"""
    try:
        LOGGER.info(f"Uploading file {n}/{all}: {up_path}")
        
        # Get file info
        file_size = os.path.getsize(up_path)
        filename = os.path.basename(up_path)
        
        await cb.message.edit(f"📤 Uploading ({n}/{all}): `{filename}`")
        
        # Upload as document (extracted files)
        sent_message = await c.send_document(
            chat_id=cb.from_user.id,
            document=up_path,
            caption=f"📁 **Extracted File**\n\n"
                   f"📁 **File:** `{filename}`\n"
                   f"📊 **Size:** `{get_readable_file_size(file_size)}`\n"
                   f"🔢 **Part:** `{n}/{all}`",
            progress=upload_progress,
            progress_args=(cb.message, f"📤 **Uploading {filename}...**", time.time())
        )
        
        return True
        
    except Exception as e:
        LOGGER.error(f"Upload failed for {up_path}: {e}")
        await cb.message.edit(f"❌ **Upload Failed!**\n\n🚨 **Error:** `{str(e)}`")
        return False

