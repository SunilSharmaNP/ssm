# downloader.py - Enhanced Downloader for SSMERGE Bot
# Supports both Telegram files and Direct Download Links (DDL)

import aiohttp
import asyncio
import os
import time
import logging
from datetime import datetime
from urllib.parse import urlparse, unquote
import re
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
import requests
from hashlib import sha256

# Import from bot modules
from __init__ import LOGGER
from config import Config
from helpers.utils import get_readable_file_size, get_readable_time

# Configuration Constants
DOWNLOAD_CHUNK_SIZE = 8 * 1024 * 1024  # 8MB chunks
DOWNLOAD_CONNECT_TIMEOUT = 60  # seconds
DOWNLOAD_READ_TIMEOUT = 600  # 10 minutes
DOWNLOAD_RETRY_ATTEMPTS = 3
DOWNLOAD_RETRY_WAIT_MIN = 2
DOWNLOAD_RETRY_WAIT_MAX = 10
MAX_URL_LENGTH = 2048
EDIT_THROTTLE_SECONDS = 2.0

# Gofile Configuration
GOFILE_API_URL = "https://api.gofile.io"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Global variables for progress throttling
last_edit_time = {}

class DirectDownloadLinkException(Exception):
    """Exception for direct download link errors"""
    pass

async def smart_progress_editor(status_message, text: str):
    """Smart progress editor with throttling to avoid flood limits"""
    if not status_message or not hasattr(status_message, 'chat'):
        return
    
    message_key = f"{status_message.chat.id}_{status_message.id}"
    now = time.time()
    last_time = last_edit_time.get(message_key, 0)
    
    if (now - last_time) > EDIT_THROTTLE_SECONDS:
        try:
            await status_message.edit_text(text, disable_web_page_preview=True)
            last_edit_time[message_key] = now
        except Exception as e:
            LOGGER.warning(f"Progress update failed: {e}")

def get_time_left(start_time: float, current: int, total: int) -> str:
    """Calculate estimated time remaining"""
    if current <= 0 or total <= 0:
        return "∞"
    
    elapsed = time.time() - start_time
    if elapsed <= 0.1:
        return "∞"
    
    rate = current / elapsed
    if rate == 0:
        return "∞"
    
    remaining_bytes = total - current
    if remaining_bytes <= 0:
        return "0s"
    
    remaining = remaining_bytes / rate
    return get_readable_time(remaining)

def get_speed(start_time: float, current: int) -> str:
    """Calculate download speed"""
    elapsed = time.time() - start_time
    if elapsed <= 0:
        return "0 B/s"
    
    speed = current / elapsed
    return get_readable_file_size(speed) + "/s"

def get_progress_bar(percentage: float, length: int = 20) -> str:
    """Generate progress bar"""
    filled = int(length * percentage)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}]"

def validate_url(url: str) -> tuple[bool, str]:
    """Validate download URL"""
    if not url or not isinstance(url, str):
        return False, "Invalid URL format"
    
    if len(url) > MAX_URL_LENGTH:
        return False, f"URL length exceeds maximum ({MAX_URL_LENGTH} chars)"
    
    parsed_url = urlparse(url)
    if not all([parsed_url.scheme, parsed_url.netloc]):
        return False, "URL must have scheme and netloc"
    
    if parsed_url.scheme not in ('http', 'https'):
        return False, "Only HTTP/HTTPS URLs allowed"
    
    return True, "Valid"

def get_filename_from_url(url: str, fallback_name: str = None) -> str:
    """Extract filename from URL with sanitization"""
    try:
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        filename = unquote(filename)
        
        if '?' in filename:
            filename = filename.split('?')[0]
        
        # Sanitize filename
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.strip(' .').strip()
        filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
        
        if not filename or len(filename) < 3:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = fallback_name or f"download_{timestamp_str}.mp4"
        
        if '.' not in filename:
            filename += '.mp4'
        
        # Limit filename length
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:(200 - len(ext))] + ext
        
        return filename
    
    except Exception as e:
        LOGGER.error(f"Error extracting filename from URL: {e}")
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        return fallback_name or f"download_error_{timestamp_str}.mp4"

def handle_gofile_url(url: str, password: str = None) -> tuple:
    """Handle gofile.io URLs and return direct download link"""
    try:
        _password = sha256(password.encode("utf-8")).hexdigest() if password else ""
        _id = url.split("/")[-1]
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")
    
    def __get_token(session):
        headers = {
            "User-Agent": USER_AGENT,
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
            "Connection": "keep-alive",
        }
        
        __url = f"{GOFILE_API_URL}/accounts"
        try:
            __res = session.post(__url, headers=headers).json()
            if __res["status"] != "ok":
                raise DirectDownloadLinkException("Failed to get token")
            return __res["data"]["token"]
        except Exception as e:
            raise e
    
    def __fetch_links(session, _id, token, folderPath=""):
        _url = f"{GOFILE_API_URL}/contents/{_id}?wt=4fd6sg89d7s6&cache=true"
        headers = {
            "User-Agent": USER_AGENT,
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Authorization": f"Bearer {token}",
        }
        
        if _password:
            _url += f"&password={_password}"
        
        try:
            _json = session.get(_url, headers=headers).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")
        
        if _json["status"] == "error-passwordRequired":
            raise DirectDownloadLinkException("Password required for this link")
        
        if _json["status"] == "error-passwordWrong":
            raise DirectDownloadLinkException("Wrong password")
        
        if _json["status"] == "error-notFound":
            raise DirectDownloadLinkException("File not found on gofile server")
        
        if _json["status"] == "error-notPublic":
            raise DirectDownloadLinkException("This folder is not public")
        
        data = _json["data"]
        details = {"contents": [], "title": data.get("name", _id), "total_size": 0}
        
        contents = data.get("children", {})
        for content in contents.values():
            if content["type"] == "file":
                item = {
                    "path": folderPath or details["title"],
                    "filename": content["name"],
                    "url": content["link"],
                }
                
                if "size" in content:
                    size = content["size"]
                    if isinstance(size, str) and size.isdigit():
                        size = float(size)
                    details["total_size"] += size
                
                details["contents"].append(item)
        
        return details
    
    with requests.Session() as session:
        try:
            token = __get_token(session)
        except Exception as e:
            raise DirectDownloadLinkException(f"Failed to get token: {e}")
        
        try:
            details = __fetch_links(session, _id, token)
        except Exception as e:
            raise DirectDownloadLinkException(str(e))
        
        if len(details["contents"]) >= 1:
            return (details["contents"][0]["url"], f"Cookie: accountToken={token}")
        else:
            raise DirectDownloadLinkException("No downloadable content found")

@retry(
    stop=stop_after_attempt(DOWNLOAD_RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=DOWNLOAD_RETRY_WAIT_MIN, max=DOWNLOAD_RETRY_WAIT_MAX),
    retry=retry_if_exception_type(aiohttp.ClientError) | retry_if_exception_type(asyncio.TimeoutError),
    reraise=True
)
async def _perform_download_request(session: aiohttp.ClientSession, url: str, dest_path: str, status_message, total_size: int):
    """Internal function to perform download with retry logic"""
    start_time = time.time()
    downloaded = 0
    
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            
            # Update total_size if not known
            if total_size == 0 and 'content-length' in response.headers:
                total_size = int(response.headers['content-length'])
            
            with open(dest_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(DOWNLOAD_CHUNK_SIZE):
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Update progress
                    if total_size > 0:
                        progress_percent = downloaded / total_size
                        speed = get_speed(start_time, downloaded)
                        eta = get_time_left(start_time, downloaded, total_size)
                        
                        progress_text = f"""📥 **Downloading from URL...**

📁 **File:** `{os.path.basename(dest_path)}`
📊 **Total:** `{get_readable_file_size(total_size)}`

{get_progress_bar(progress_percent)} `{progress_percent:.1%}`

📈 **Downloaded:** `{get_readable_file_size(downloaded)}`
🚀 **Speed:** `{speed}`
⏱ **ETA:** `{eta}`"""
                        
                        await smart_progress_editor(status_message, progress_text)
        
        return downloaded
    
    except Exception as e:
        LOGGER.error(f"Download request error: {e}")
        raise e

async def download_from_url(url: str, user_id: int, status_message, password: str = None) -> str | None:
    """Download video from direct download link"""
    start_time = time.time()
    
    # Validate URL
    is_valid, error_msg = validate_url(url)
    if not is_valid:
        await smart_progress_editor(status_message, f"❌ **Invalid URL!**\n\n🚨 **Error:** {error_msg}")
        return None
    
    # Handle gofile.io URLs
    parsed_url = urlparse(url)
    headers_dict = {}
    
    if 'gofile.io' in parsed_url.netloc:
        try:
            await smart_progress_editor(status_message, "🔍 **Processing gofile.io link...**")
            direct_url, headers_str = await asyncio.to_thread(handle_gofile_url, url, password)
            
            # Parse headers
            if headers_str:
                for header_line in headers_str.split('\n'):
                    if ':' in header_line:
                        key, value = header_line.split(':', 1)
                        headers_dict[key.strip()] = value.strip()
            
            url = direct_url
            await smart_progress_editor(status_message, "✅ **Gofile.io link processed!**")
        
        except DirectDownloadLinkException as e:
            await smart_progress_editor(status_message, f"❌ **Gofile.io Error!**\n\n🚨 **Error:** {str(e)}")
            return None
        except Exception as e:
            await smart_progress_editor(status_message, f"❌ **Processing Failed!**\n\n🚨 **Error:** {str(e)}")
            return None
    
    # Setup paths
    file_name = get_filename_from_url(url)
    user_download_dir = f"downloads/{str(user_id)}"
    os.makedirs(user_download_dir, exist_ok=True)
    dest_path = os.path.join(user_download_dir, file_name)
    
    # Prevent overwriting
    if os.path.exists(dest_path):
        base, ext = os.path.splitext(file_name)
        timestamp = datetime.now().strftime("_%H%M%S")
        dest_path = os.path.join(user_download_dir, f"{base}{timestamp}{ext}")
        file_name = os.path.basename(dest_path)
    
    try:
        # Initial status
        await smart_progress_editor(status_message, f"🔍 **Connecting...**\n\n📁 **File:** `{file_name}`")
        
        # Setup session
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        if headers_dict:
            headers.update(headers_dict)
        
        timeout_config = aiohttp.ClientTimeout(
            total=None,
            connect=DOWNLOAD_CONNECT_TIMEOUT,
            sock_read=DOWNLOAD_READ_TIMEOUT
        )
        
        async with aiohttp.ClientSession(headers=headers, timeout=timeout_config) as session:
            # Get file info
            total_size = 0
            try:
                async with session.head(url, allow_redirects=True) as head_response:
                    head_response.raise_for_status()
                    total_size = int(head_response.headers.get('content-length', 0))
                    
                    await smart_progress_editor(
                        status_message,
                        f"📡 **Starting Download...**\n\n"
                        f"📁 **File:** `{file_name}`\n"
                        f"📊 **Size:** `{get_readable_file_size(total_size) if total_size > 0 else 'Unknown'}`"
                    )
            
            except Exception:
                LOGGER.warning(f"HEAD request failed for {url}")
                total_size = 0
            
            # Perform download
            downloaded_size = await _perform_download_request(session, url, dest_path, status_message, total_size)
            
            # Verify download
            actual_size = os.path.getsize(dest_path)
            if total_size > 0 and actual_size != total_size:
                os.remove(dest_path)
                await smart_progress_editor(
                    status_message,
                    f"❌ **Download Failed!**\n\n"
                    f"🚨 **Error:** File size mismatch\n"
                    f"📊 **Expected:** `{get_readable_file_size(total_size)}`\n"
                    f"📊 **Received:** `{get_readable_file_size(actual_size)}`"
                )
                return None
            
            # Success
            elapsed_time = time.time() - start_time
            await smart_progress_editor(
                status_message,
                f"✅ **Download Complete!**\n\n"
                f"📁 **File:** `{file_name}`\n"
                f"📊 **Size:** `{get_readable_file_size(actual_size)}`\n"
                f"⏱ **Time:** `{elapsed_time:.1f}s`\n"
                f"🚀 **Speed:** `{get_speed(start_time, actual_size)}`"
            )
            
            return dest_path
    
    except Exception as e:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        
        await smart_progress_editor(
            status_message,
            f"❌ **Download Failed!**\n\n"
            f"📁 **File:** `{file_name}`\n"
            f"🚨 **Error:** `{type(e).__name__}: {str(e)}`\n"
            f"💡 **Tip:** Check URL and try again"
        )
        return None

async def download_from_tg(message, user_id: int, status_message) -> str | None:
    """Download video from Telegram message"""
    try:
        # Setup paths
        user_download_dir = f"downloads/{str(user_id)}"
        os.makedirs(user_download_dir, exist_ok=True)
        
        # Get file information
        file_obj = None
        file_name = "Unknown File"
        file_size = 0
        duration = 0
        
        if message.video:
            file_obj = message.video
            file_name = file_obj.file_name or f"video_{message.id}.mp4"
            file_size = file_obj.file_size
            duration = file_obj.duration or 0
        elif message.document:
            file_obj = message.document
            file_name = file_obj.file_name or f"document_{message.id}"
            file_size = file_obj.file_size
        else:
            await smart_progress_editor(status_message, "❌ **Error:** No downloadable file found")
            return None
        
        # Validate file size (2GB Telegram limit)
        if file_size > 2 * 1024 * 1024 * 1024:
            await smart_progress_editor(
                status_message,
                f"❌ **File Too Large!**\n\n"
                f"📊 **Size:** `{get_readable_file_size(file_size)}`\n"
                f"🚨 **Limit:** `2GB (Telegram Limit)`"
            )
            return None
        
        # Setup destination path
        dest_path = os.path.join(user_download_dir, file_name)
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(file_name)
            timestamp = datetime.now().strftime("_%H%M%S")
            file_name = f"{base}{timestamp}{ext}"
            dest_path = os.path.join(user_download_dir, file_name)
        
        # Initial status
        await smart_progress_editor(
            status_message,
            f"📡 **Starting Telegram Download...**\n\n"
            f"📁 **File:** `{file_name}`\n"
            f"📊 **Size:** `{get_readable_file_size(file_size)}`"
        )
        
        # Progress callback
        start_time = time.time()
        
        async def progress_callback(current, total):
            progress = current / total
            speed = get_speed(start_time, current)
            eta = get_time_left(start_time, current, total)
            
            progress_text = f"""📥 **Downloading from Telegram...**

📁 **File:** `{file_name}`
📊 **Total:** `{get_readable_file_size(total)}`

{get_progress_bar(progress)} `{progress:.1%}`

📈 **Downloaded:** `{get_readable_file_size(current)}`
🚀 **Speed:** `{speed}`
⏱ **ETA:** `{eta}`"""
            
            await smart_progress_editor(status_message, progress_text)
        
        # Download file
        file_path = await message.download(
            file_name=dest_path,
            progress=progress_callback
        )
        
        # Verify download
        if not os.path.exists(file_path):
            await smart_progress_editor(status_message, "❌ **Download Failed:** File not found")
            return None
        
        actual_size = os.path.getsize(file_path)
        elapsed_time = time.time() - start_time
        
        # Success message
        await smart_progress_editor(
            status_message,
            f"✅ **Telegram Download Complete!**\n\n"
            f"📁 **File:** `{file_name}`\n"
            f"📊 **Size:** `{get_readable_file_size(actual_size)}`\n"
            f"⏱ **Time:** `{elapsed_time:.1f}s`\n"
            f"🚀 **Speed:** `{get_speed(start_time, actual_size)}`"
        )
        
        return file_path
    
    except Exception as e:
        error_text = f"""❌ **Telegram Download Failed!**

🚨 **Error:** `{type(e).__name__}: {str(e)}`

💡 **Solutions:**
• Check file availability
• Ensure stable connection
• Try again"""
        
        LOGGER.error(f"Telegram download error: {e}")
        
        # Cleanup partial file
        if 'dest_path' in locals() and os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except:
                pass
        
        await smart_progress_editor(status_message, error_text)
        return None

def cleanup_user_downloads(user_id: int):
    """Clean up user downloads directory"""
    try:
        user_download_dir = f"downloads/{str(user_id)}"
        if os.path.exists(user_download_dir):
            for filename in os.listdir(user_download_dir):
                file_path = os.path.join(user_download_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(user_download_dir)
        LOGGER.info(f"Cleaned up downloads for user {user_id}")
    except Exception as e:
        LOGGER.error(f"Cleanup error for user {user_id}: {e}")

def get_download_info(file_path: str) -> dict:
    """Get information about downloaded file"""
    try:
        if not os.path.exists(file_path):
            return {"exists": False}
        
        stat_info = os.stat(file_path)
        return {
            "exists": True,
            "size": stat_info.st_size,
            "size_human": get_readable_file_size(stat_info.st_size),
            "filename": os.path.basename(file_path)
        }
    except Exception as e:
        LOGGER.error(f"Error getting file info: {e}")
        return {"exists": False, "error": str(e)}
