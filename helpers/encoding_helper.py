#!/usr/bin/env python3
"""
Professional Video Encoding Helper
Supports multiple quality presets, custom CRF, codecs, and advanced FFmpeg options
"""

import os
import asyncio
import time
import re
from typing import Optional, Dict, Any
from __init__ import LOGGER
from helpers.utils import get_readable_file_size, get_readable_time

# Encoding Quality Presets
QUALITY_PRESETS = {
    "1080p_h264": {
        "name": "1080p H.264",
        "resolution": "1920:1080",
        "codec": "libx264",
        "crf": "23",
        "preset": "medium",
        "audio_bitrate": "192k"
    },
    "1080p_hevc": {
        "name": "1080p HEVC/H.265",
        "resolution": "1920:1080",
        "codec": "libx265",
        "crf": "28",
        "preset": "medium",
        "audio_bitrate": "192k"
    },
    "720p_h264": {
        "name": "720p H.264",
        "resolution": "1280:720",
        "codec": "libx264",
        "crf": "23",
        "preset": "medium",
        "audio_bitrate": "128k"
    },
    "720p_hevc": {
        "name": "720p HEVC/H.265",
        "resolution": "1280:720",
        "codec": "libx265",
        "crf": "28",
        "preset": "medium",
        "audio_bitrate": "128k"
    },
    "480p_h264": {
        "name": "480p H.264",
        "resolution": "854:480",
        "codec": "libx264",
        "crf": "23",
        "preset": "medium",
        "audio_bitrate": "96k"
    },
    "480p_hevc": {
        "name": "480p HEVC/H.265",
        "resolution": "854:480",
        "codec": "libx265",
        "crf": "28",
        "preset": "medium",
        "audio_bitrate": "96k"
    },
    "custom": {
        "name": "Custom Settings",
        "resolution": None,
        "codec": "libx264",
        "crf": "23",
        "preset": "medium",
        "audio_bitrate": "128k"
    }
}

# CRF Values (Constant Rate Factor)
# Lower = Better quality, Larger file
# Higher = Lower quality, Smaller file
CRF_PRESETS = {
    "best": {"h264": "18", "hevc": "23"},
    "high": {"h264": "21", "hevc": "26"},
    "medium": {"h264": "23", "hevc": "28"},
    "low": {"h264": "26", "hevc": "31"},
    "potato": {"h264": "30", "hevc": "35"}
}

# FFmpeg Encoding Presets
# ultrafast = fast encoding, larger file
# slow = slow encoding, better compression
ENCODING_PRESETS = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]

# Audio Bitrates
AUDIO_BITRATES = ["64k", "96k", "128k", "192k", "256k", "320k"]

# Video Codecs
VIDEO_CODECS = {
    "libx264": "H.264/AVC",
    "libx265": "H.265/HEVC",
    "libvpx-vp9": "VP9",
    "copy": "Copy (No Re-encoding)"
}

# Audio Codecs
AUDIO_CODECS = {
    "aac": "AAC",
    "libopus": "Opus",
    "libmp3lame": "MP3",
    "copy": "Copy (No Re-encoding)"
}


class EncodingSettings:
    """Stores encoding settings for a user"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.preset = "720p_h264"  # Default
        self.custom_crf = None
        self.custom_resolution = None
        self.custom_codec = None
        self.custom_preset = None
        self.custom_audio_bitrate = None
        self.custom_audio_codec = None
    
    def get_settings(self) -> Dict[str, Any]:
        """Get current encoding settings"""
        if self.preset == "custom":
            return {
                "codec": self.custom_codec or "libx264",
                "crf": self.custom_crf or "23",
                "resolution": self.custom_resolution,
                "preset": self.custom_preset or "medium",
                "audio_bitrate": self.custom_audio_bitrate or "128k",
                "audio_codec": self.custom_audio_codec or "aac"
            }
        else:
            preset_data = QUALITY_PRESETS[self.preset].copy()
            # Apply custom overrides
            if self.custom_crf:
                preset_data["crf"] = self.custom_crf
            if self.custom_preset:
                preset_data["preset"] = self.custom_preset
            if self.custom_audio_bitrate:
                preset_data["audio_bitrate"] = self.custom_audio_bitrate
            return preset_data
    
    def set_preset(self, preset: str):
        """Set quality preset"""
        if preset in QUALITY_PRESETS:
            self.preset = preset
    
    def set_custom_crf(self, crf: str):
        """Set custom CRF value"""
        self.custom_crf = crf
    
    def set_custom_resolution(self, resolution: str):
        """Set custom resolution (e.g., '1920:1080')"""
        self.custom_resolution = resolution
    
    def set_custom_codec(self, codec: str):
        """Set custom video codec"""
        if codec in VIDEO_CODECS:
            self.custom_codec = codec
    
    def set_custom_preset(self, preset: str):
        """Set custom encoding preset"""
        if preset in ENCODING_PRESETS:
            self.custom_preset = preset
    
    def set_custom_audio_bitrate(self, bitrate: str):
        """Set custom audio bitrate"""
        if bitrate in AUDIO_BITRATES:
            self.custom_audio_bitrate = bitrate
    
    def set_custom_audio_codec(self, codec: str):
        """Set custom audio codec"""
        if codec in AUDIO_CODECS:
            self.custom_audio_codec = codec


# Global storage for user encoding settings
user_encoding_settings = {}


def get_user_encoding_settings(user_id: int) -> EncodingSettings:
    """Get or create encoding settings for a user"""
    if user_id not in user_encoding_settings:
        user_encoding_settings[user_id] = EncodingSettings(user_id)
    return user_encoding_settings[user_id]


async def encode_video(
    input_file: str,
    output_file: str,
    user_id: int,
    progress_message=None,
    preset: Optional[str] = None
) -> Optional[str]:
    """
    Encode video with specified settings
    
    Args:
        input_file: Path to input video
        output_file: Path to output video
        user_id: User ID for settings
        progress_message: Pyrogram message for progress updates
        preset: Override preset (optional)
    
    Returns:
        Path to encoded video or None if failed
    """
    try:
        if not os.path.exists(input_file):
            LOGGER.error(f"Input file not found: {input_file}")
            return None
        
        # Get encoding settings
        settings_obj = get_user_encoding_settings(user_id)
        if preset:
            settings_obj.set_preset(preset)
        settings = settings_obj.get_settings()
        
        LOGGER.info(f"Encoding with settings: {settings}")
        
        # Build FFmpeg command
        ffmpeg_cmd = ["ffmpeg", "-i", input_file, "-y"]
        
        # Video codec
        if settings.get("codec") == "copy":
            ffmpeg_cmd.extend(["-c:v", "copy"])
        else:
            ffmpeg_cmd.extend(["-c:v", settings.get("codec", "libx264")])
            
            # CRF
            ffmpeg_cmd.extend(["-crf", settings.get("crf", "23")])
            
            # Preset
            ffmpeg_cmd.extend(["-preset", settings.get("preset", "medium")])
            
            # Resolution
            if settings.get("resolution"):
                # Use scale filter with proper aspect ratio handling
                ffmpeg_cmd.extend([
                    "-vf", 
                    f"scale={settings['resolution']}:force_original_aspect_ratio=decrease,pad={settings['resolution']}:(ow-iw)/2:(oh-ih)/2"
                ])
        
        # Audio codec
        audio_codec = settings.get("audio_codec", "aac")
        if audio_codec == "copy":
            ffmpeg_cmd.extend(["-c:a", "copy"])
        else:
            ffmpeg_cmd.extend(["-c:a", audio_codec])
            ffmpeg_cmd.extend(["-b:a", settings.get("audio_bitrate", "128k")])
        
        # Additional optimizations
        if settings.get("codec") == "libx264":
            ffmpeg_cmd.extend(["-profile:v", "high", "-level", "4.0"])
        elif settings.get("codec") == "libx265":
            ffmpeg_cmd.extend(["-x265-params", "log-level=error"])
        
        # Output file
        ffmpeg_cmd.append(output_file)
        
        LOGGER.info(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
        
        # Update progress
        if progress_message:
            await progress_message.edit_text(
                "🔄 **Starting Encoding...**\n\n"
                f"📁 **Input:** `{os.path.basename(input_file)}`\n"
                f"🎬 **Codec:** `{settings.get('codec', 'libx264')}`\n"
                f"📊 **Quality (CRF):** `{settings.get('crf', '23')}`\n"
                f"🎯 **Preset:** `{settings.get('preset', 'medium')}`\n"
                f"🔊 **Audio:** `{settings.get('audio_bitrate', '128k')}`\n\n"
                "⏳ This may take a while depending on file size..."
            )
        
        # Execute FFmpeg
        start_time = time.time()
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Monitor progress
        last_update = 0
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            
            line_str = line.decode().strip()
            
            # Parse progress from FFmpeg output
            if progress_message and time.time() - last_update > 5:
                # Look for time progress
                time_match = re.search(r'time=(\d+):(\d+):(\d+\.?\d*)', line_str)
                if time_match:
                    hours = int(time_match.group(1))
                    minutes = int(time_match.group(2))
                    seconds = float(time_match.group(3))
                    current_time = hours * 3600 + minutes * 60 + seconds
                    
                    elapsed = time.time() - start_time
                    
                    try:
                        await progress_message.edit_text(
                            "🔄 **Encoding in Progress...**\n\n"
                            f"📁 **File:** `{os.path.basename(input_file)}`\n"
                            f"⏱ **Elapsed:** `{get_readable_time(elapsed)}`\n"
                            f"🎬 **Codec:** `{settings.get('codec', 'libx264')}`\n"
                            f"📊 **CRF:** `{settings.get('crf', '23')}`\n\n"
                            "💡 Please be patient, encoding takes time..."
                        )
                        last_update = time.time()
                    except Exception as e:
                        LOGGER.warning(f"Failed to update progress: {e}")
        
        # Wait for process to complete
        await process.wait()
        
        if process.returncode == 0 and os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            elapsed = time.time() - start_time
            
            if progress_message:
                await progress_message.edit_text(
                    "✅ **Encoding Complete!**\n\n"
                    f"📁 **Output:** `{os.path.basename(output_file)}`\n"
                    f"📊 **Size:** `{get_readable_file_size(file_size)}`\n"
                    f"⏱ **Time:** `{get_readable_time(elapsed)}`\n"
                    f"🎬 **Codec:** `{settings.get('codec', 'libx264')}`\n"
                    f"📈 **Quality:** `{settings.get('crf', '23')}`\n\n"
                    "📤 Uploading now..."
                )
            
            LOGGER.info(f"Encoding successful: {output_file}")
            return output_file
        else:
            LOGGER.error(f"Encoding failed with return code: {process.returncode}")
            return None
    
    except Exception as e:
        LOGGER.error(f"Encoding error: {e}")
        if progress_message:
            try:
                await progress_message.edit_text(
                    "❌ **Encoding Failed!**\n\n"
                    f"🚨 **Error:** `{str(e)}`\n\n"
                    "💡 Try with different settings or contact support."
                )
            except:
                pass
        return None


async def get_video_info(file_path: str) -> Optional[Dict[str, Any]]:
    """Get video information using ffprobe"""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration,codec_name",
            "-of", "json",
            file_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            import json
            data = json.loads(stdout.decode())
            stream = data.get("streams", [{}])[0]
            
            return {
                "width": stream.get("width"),
                "height": stream.get("height"),
                "duration": float(stream.get("duration", 0)),
                "codec": stream.get("codec_name")
            }
    except Exception as e:
        LOGGER.error(f"Failed to get video info: {e}")
    
    return None
