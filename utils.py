# utils.py - Essential Helper Functions for Enhanced Bot

import os
import re
import json
import asyncio
import subprocess
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def get_human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    if size_bytes == 0:
        return "0B"
    units = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {units[i]}"

def get_progress_bar(progress: float, length: int = 20) -> str:
    """Get a styled progress bar."""
    filled_len = int(length * progress)
    bar = "█" * filled_len + "░" * (length - filled_len)
    return bar

def get_time_left(start_time: float, current: int, total: int) -> str:
    """Calculate estimated time remaining."""
    import time
    
    if current <= 0 or total <= 0:
        return "Calculating..."
    
    elapsed = time.time() - start_time
    if elapsed <= 0.2:
        return "Calculating..."
    
    rate = current / elapsed
    if rate == 0:
        return "Calculating..."
    
    remaining_bytes = total - current
    if remaining_bytes <= 0:
        return "0s"
        
    remaining = remaining_bytes / rate
    
    if remaining < 60:
        return f"{int(remaining)}s"
    elif remaining < 3600:
        return f"{int(remaining // 60)}m {int(remaining % 60)}s"
    else:
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)
        return f"{hours}h {minutes}m"

def get_speed(start_time: float, current: int) -> str:
    """Calculate speed with better formatting."""
    import time
    
    elapsed = time.time() - start_time
    if elapsed <= 0:
        return "0 B/s"
    
    speed = current / elapsed
    
    if speed < 1024:
        return f"{speed:.0f} B/s"
    elif speed < 1024 * 1024:
        return f"{speed / 1024:.1f} KB/s"
    else:
        return f"{speed / (1024 * 1024):.2f} MB/s"

async def get_video_properties(file_path: str) -> Optional[Dict[str, Any]]:
    """Get comprehensive video information using ffprobe."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', file_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"ffprobe failed for {file_path}: {stderr.decode()}")
            return None
            
        data = json.loads(stdout.decode())
        
        video_streams = [s for s in data.get('streams', []) if s.get('codec_type') == 'video']
        audio_streams = [s for s in data.get('streams', []) if s.get('codec_type') == 'audio']
        
        if not video_streams:
            logger.error(f"No video stream found in {file_path}")
            return None
            
        video_stream = video_streams[0]
        
        # Parse duration
        duration = float(data.get('format', {}).get('duration', 0))
        
        # Parse frame rate
        fps_str = video_stream.get('r_frame_rate', '30/1')
        if '/' in fps_str:
            num, den = fps_str.split('/')
            fps = round(float(num) / float(den), 2) if int(den) != 0 else 30.0
        else:
            fps = round(float(fps_str), 2)
        
        return {
            'duration': int(duration),
            'width': int(video_stream.get('width', 0)),
            'height': int(video_stream.get('height', 0)),
            'fps': fps,
            'codec': video_stream.get('codec_name', ''),
            'has_audio': len(audio_streams) > 0,
            'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
        }
        
    except Exception as e:
        logger.error(f"Failed to get video properties for {file_path}: {e}")
        return None

def cleanup_files(directory: str):
    """Clean up files in directory."""
    try:
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                    elif os.path.isdir(file_path):
                        import shutil
                        shutil.rmtree(file_path)
                except Exception as e:
                    logger.error(f"Error deleting {file_path}: {e}")
    except Exception as e:
        logger.error(f"Error cleaning up directory {directory}: {e}")

def is_valid_url(url: str) -> bool:
    """Validate if string is a valid URL."""
    try:
        if not url or not isinstance(url, str):
            return False
        
        # Check if starts with http/https
        if not url.startswith(('http://', 'https://')):
            return False
        
        parsed_url = urlparse(url)
        return all([parsed_url.scheme, parsed_url.netloc])
    except Exception:
        return False

def get_readable_file_size(size_in_bytes: int) -> str:
    """Get readable file size - alias for compatibility."""
    return get_human_readable_size(size_in_bytes)

def get_readable_time(seconds: int) -> str:
    """Convert seconds to readable time format."""
    if seconds < 0:
        return "Unknown"
    
    periods = [
        ('d', 86400),
        ('h', 3600),
        ('m', 60),
        ('s', 1)
    ]
    
    result = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result.append(f"{int(period_value)}{period_name}")
    
    return ' '.join(result) if result else '0s'

# Export all functions
__all__ = [
    'get_human_readable_size',
    'get_progress_bar',
    'get_time_left',
    'get_speed',
    'get_video_properties',
    'cleanup_files',
    'is_valid_url',
    'get_readable_file_size',
    'get_readable_time'
]
