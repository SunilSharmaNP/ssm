#!/usr/bin/env python3
"""
Encoding Button Interface
Professional button-based UI for encoding settings
Based on VE repository's professional approach
"""

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from helpers.encoding_helper import (
    QUALITY_PRESETS, CRF_PRESETS, ENCODING_PRESETS,
    AUDIO_BITRATES, VIDEO_CODECS, AUDIO_CODECS
)


def get_encoding_mode_buttons():
    """Main encoding mode selection buttons"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 1080p H.264", callback_data="enc_preset_1080p_h264"),
         InlineKeyboardButton("🎬 1080p HEVC", callback_data="enc_preset_1080p_hevc")],
        [InlineKeyboardButton("📹 720p H.264", callback_data="enc_preset_720p_h264"),
         InlineKeyboardButton("📹 720p HEVC", callback_data="enc_preset_720p_hevc")],
        [InlineKeyboardButton("📱 480p H.264", callback_data="enc_preset_480p_h264"),
         InlineKeyboardButton("📱 480p HEVC", callback_data="enc_preset_480p_hevc")],
        [InlineKeyboardButton("⚙️ Custom Settings", callback_data="enc_custom_menu")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_start")]
    ])


def get_custom_encoding_buttons():
    """Custom encoding settings menu"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Quality (CRF)", callback_data="enc_crf_menu"),
         InlineKeyboardButton("🎬 Video Codec", callback_data="enc_codec_menu")],
        [InlineKeyboardButton("📐 Resolution", callback_data="enc_resolution_menu"),
         InlineKeyboardButton("⚡ Encoding Speed", callback_data="enc_speed_menu")],
        [InlineKeyboardButton("🔊 Audio Bitrate", callback_data="enc_audio_br_menu"),
         InlineKeyboardButton("🎵 Audio Codec", callback_data="enc_audio_codec_menu")],
        [InlineKeyboardButton("✅ Start Encoding", callback_data="enc_start_custom"),
         InlineKeyboardButton("🔙 Back", callback_data="enc_mode_menu")]
    ])


def get_crf_selection_buttons():
    """CRF (Quality) selection buttons"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌟 Best (18/23)", callback_data="enc_crf_best"),
         InlineKeyboardButton("⭐ High (21/26)", callback_data="enc_crf_high")],
        [InlineKeyboardButton("📊 Medium (23/28)", callback_data="enc_crf_medium"),
         InlineKeyboardButton("📉 Low (26/31)", callback_data="enc_crf_low")],
        [InlineKeyboardButton("🥔 Potato (30/35)", callback_data="enc_crf_potato")],
        [InlineKeyboardButton("🔙 Back", callback_data="enc_custom_menu")]
    ])


def get_codec_selection_buttons():
    """Video codec selection buttons"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 H.264/AVC", callback_data="enc_codec_libx264"),
         InlineKeyboardButton("🎯 H.265/HEVC", callback_data="enc_codec_libx265")],
        [InlineKeyboardButton("🌐 VP9", callback_data="enc_codec_libvpx-vp9"),
         InlineKeyboardButton("📋 Copy (No Re-encode)", callback_data="enc_codec_copy")],
        [InlineKeyboardButton("🔙 Back", callback_data="enc_custom_menu")]
    ])


def get_resolution_buttons():
    """Resolution selection buttons"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖥️ 1920x1080 (1080p)", callback_data="enc_res_1920:1080"),
         InlineKeyboardButton("📺 1280x720 (720p)", callback_data="enc_res_1280:720")],
        [InlineKeyboardButton("📱 854x480 (480p)", callback_data="enc_res_854:480"),
         InlineKeyboardButton("📱 640x360 (360p)", callback_data="enc_res_640:360")],
        [InlineKeyboardButton("🔄 Keep Original", callback_data="enc_res_original")],
        [InlineKeyboardButton("🔙 Back", callback_data="enc_custom_menu")]
    ])


def get_encoding_speed_buttons():
    """Encoding speed/preset selection buttons"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Ultra Fast", callback_data="enc_speed_ultrafast"),
         InlineKeyboardButton("🏃 Fast", callback_data="enc_speed_fast")],
        [InlineKeyboardButton("🚶 Medium", callback_data="enc_speed_medium"),
         InlineKeyboardButton("🐌 Slow (Best)", callback_data="enc_speed_slow")],
        [InlineKeyboardButton("🐢 Very Slow (Max Quality)", callback_data="enc_speed_veryslow")],
        [InlineKeyboardButton("🔙 Back", callback_data="enc_custom_menu")]
    ])


def get_audio_bitrate_buttons():
    """Audio bitrate selection buttons"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📉 64k", callback_data="enc_audio_br_64k"),
         InlineKeyboardButton("📊 96k", callback_data="enc_audio_br_96k")],
        [InlineKeyboardButton("📊 128k", callback_data="enc_audio_br_128k"),
         InlineKeyboardButton("📈 192k", callback_data="enc_audio_br_192k")],
        [InlineKeyboardButton("🔊 256k", callback_data="enc_audio_br_256k"),
         InlineKeyboardButton("💎 320k", callback_data="enc_audio_br_320k")],
        [InlineKeyboardButton("🔙 Back", callback_data="enc_custom_menu")]
    ])


def get_audio_codec_buttons():
    """Audio codec selection buttons"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎵 AAC", callback_data="enc_audio_codec_aac"),
         InlineKeyboardButton("🎯 Opus", callback_data="enc_audio_codec_libopus")],
        [InlineKeyboardButton("🎼 MP3", callback_data="enc_audio_codec_libmp3lame"),
         InlineKeyboardButton("📋 Copy", callback_data="enc_audio_codec_copy")],
        [InlineKeyboardButton("🔙 Back", callback_data="enc_custom_menu")]
    ])


def get_current_settings_text(user_id):
    """Generate text showing current encoding settings"""
    from helpers.encoding_helper import get_user_encoding_settings
    
    settings_obj = get_user_encoding_settings(user_id)
    settings = settings_obj.get_settings()
    
    preset_name = QUALITY_PRESETS.get(settings_obj.preset, {}).get("name", "Custom")
    
    text = f"""⚙️ **Current Encoding Settings**

📊 **Preset:** `{preset_name}`
🎬 **Video Codec:** `{settings.get('codec', 'libx264')}`
📈 **Quality (CRF):** `{settings.get('crf', '23')}`
⚡ **Speed Preset:** `{settings.get('preset', 'medium')}`
📐 **Resolution:** `{settings.get('resolution') or 'Original'}`
🔊 **Audio Bitrate:** `{settings.get('audio_bitrate', '128k')}`
🎵 **Audio Codec:** `{settings.get('audio_codec', 'aac')}`

💡 **Tip:** Lower CRF = Better quality but larger file
"""
    return text


def get_encode_confirm_buttons():
    """Confirmation buttons before encoding"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm & Encode", callback_data="enc_confirm_start")],
        [InlineKeyboardButton("⚙️ Change Settings", callback_data="enc_custom_menu"),
         InlineKeyboardButton("❌ Cancel", callback_data="enc_cancel")]
    ])


def get_encoding_progress_buttons():
    """Buttons shown during encoding"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel Encoding", callback_data="enc_cancel_process")]
    ])


def parse_encoding_callback(callback_data: str):
    """
    Parse encoding callback data
    Returns: (category, value) tuple
    """
    if not callback_data.startswith("enc_"):
        return None, None
    
    parts = callback_data.split("_", 2)
    
    if len(parts) < 2:
        return None, None
    
    category = parts[1]
    value = parts[2] if len(parts) > 2 else None
    
    return category, value


def get_help_text():
    """Get encoding help text"""
    return """📖 **Encoding Guide**

**Quality Presets:**
• 1080p/720p/480p - Quick preset selection
• H.264 - Standard codec, good compatibility
• HEVC/H.265 - Better compression, newer codec

**CRF (Constant Rate Factor):**
• Lower values = Higher quality, Larger file
• 18-23: Nearly lossless to excellent
• 23-28: Good quality (recommended)
• 28+: Lower quality, smaller files

**Encoding Speed:**
• Ultra Fast: Quick but larger files
• Medium: Balanced (recommended)
• Slow/Very Slow: Best compression

**Audio Bitrate:**
• 96k-128k: Good for most content
• 192k-256k: High quality audio
• 320k: Maximum quality

💡 **Recommendations:**
• For archival: 1080p HEVC, CRF 23, Slow
• For sharing: 720p H.264, CRF 23, Medium
• For quick preview: 480p H.264, CRF 26, Fast
"""
