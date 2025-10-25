#!/usr/bin/env python3
"""
Encoding Plugin - Handles all encoding-related functionality
Professional video encoding with multiple quality presets
"""

import os
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message
from __init__ import LOGGER, queueDB
from config import Config
from helpers.utils import UserSettings, get_readable_file_size
from helpers.encoding_helper import (
    encode_video, get_user_encoding_settings,
    QUALITY_PRESETS, CRF_PRESETS
)
from helpers.encode_buttons import (
    get_encoding_mode_buttons, get_custom_encoding_buttons,
    get_crf_selection_buttons, get_codec_selection_buttons,
    get_resolution_buttons, get_encoding_speed_buttons,
    get_audio_bitrate_buttons, get_audio_codec_buttons,
    get_current_settings_text, get_encode_confirm_buttons,
    get_help_text, parse_encoding_callback
)
from helpers.uploader import uploadVideo
from helpers.ffmpeg_helper import take_screen_shot


async def handle_encoding_callback(c: Client, cb: CallbackQuery):
    """Main handler for all encoding-related callbacks"""
    try:
        data = cb.data
        user_id = cb.from_user.id
        user = UserSettings(user_id, cb.from_user.first_name)
        
        LOGGER.info(f"Encoding callback: {data} from user {user_id}")
        
        # Check user access
        if not user.allowed and user_id != int(Config.OWNER):
            await cb.answer("🔐 Login required!", show_alert=True)
            return
        
        # Parse callback
        category, value = parse_encoding_callback(data)
        
        # Get user encoding settings
        settings_obj = get_user_encoding_settings(user_id)
        
        # Handle different callback types
        if data == "enc_mode_menu":
            # Show encoding mode selection menu
            await cb.message.edit_text(
                "🎬 **Select Encoding Quality Preset**\n\n"
                "Choose a preset or configure custom settings:\n\n"
                "💡 **Quick Guide:**\n"
                "• H.264: Best compatibility\n"
                "• HEVC: Better compression\n"
                "• Higher resolution = Larger file\n"
                "• Custom: Full control over encoding",
                reply_markup=get_encoding_mode_buttons()
            )
        
        elif data.startswith("enc_preset_"):
            # Quality preset selected
            preset = data.replace("enc_preset_", "")
            settings_obj.set_preset(preset)
            preset_name = QUALITY_PRESETS[preset]["name"]
            
            await cb.answer(f"✅ Preset: {preset_name}", show_alert=False)
            
            # Show confirmation
            await cb.message.edit_text(
                f"✅ **Preset Selected: {preset_name}**\n\n"
                + get_current_settings_text(user_id) +
                "\n\nReady to encode?",
                reply_markup=get_encode_confirm_buttons()
            )
        
        elif data == "enc_custom_menu":
            # Show custom settings menu
            await cb.message.edit_text(
                "⚙️ **Custom Encoding Settings**\n\n"
                + get_current_settings_text(user_id),
                reply_markup=get_custom_encoding_buttons()
            )
        
        elif data == "enc_crf_menu":
            # Show CRF selection
            await cb.message.edit_text(
                "📊 **Select Quality (CRF)**\n\n"
                "Lower values = Better quality but larger file\n"
                "Higher values = Smaller file but lower quality\n\n"
                "💡 **Recommended:** Medium (23/28)",
                reply_markup=get_crf_selection_buttons()
            )
        
        elif data.startswith("enc_crf_"):
            # CRF value selected
            crf_type = value
            if crf_type in CRF_PRESETS:
                # Use current codec to determine CRF value
                current_codec = settings_obj.get_settings().get("codec", "libx264")
                codec_type = "hevc" if "265" in current_codec or "hevc" in current_codec else "h264"
                crf_value = CRF_PRESETS[crf_type][codec_type]
                settings_obj.set_custom_crf(crf_value)
                await cb.answer(f"✅ Quality set: {crf_type.upper()} (CRF {crf_value})")
            
            # Return to custom menu
            await cb.message.edit_text(
                "⚙️ **Custom Encoding Settings**\n\n"
                + get_current_settings_text(user_id),
                reply_markup=get_custom_encoding_buttons()
            )
        
        elif data == "enc_codec_menu":
            # Show codec selection
            await cb.message.edit_text(
                "🎬 **Select Video Codec**\n\n"
                "• H.264: Best compatibility, good quality\n"
                "• HEVC/H.265: Better compression, smaller files\n"
                "• VP9: Open codec, good for web\n"
                "• Copy: No re-encoding (fast but no changes)",
                reply_markup=get_codec_selection_buttons()
            )
        
        elif data.startswith("enc_codec_"):
            # Codec selected
            codec = value
            settings_obj.set_custom_codec(codec)
            await cb.answer(f"✅ Codec: {codec}")
            
            # Return to custom menu
            await cb.message.edit_text(
                "⚙️ **Custom Encoding Settings**\n\n"
                + get_current_settings_text(user_id),
                reply_markup=get_custom_encoding_buttons()
            )
        
        elif data == "enc_resolution_menu":
            # Show resolution selection
            await cb.message.edit_text(
                "📐 **Select Output Resolution**\n\n"
                "Choose target resolution or keep original",
                reply_markup=get_resolution_buttons()
            )
        
        elif data.startswith("enc_res_"):
            # Resolution selected
            if value == "original":
                settings_obj.set_custom_resolution(None)
                await cb.answer("✅ Resolution: Original")
            else:
                settings_obj.set_custom_resolution(value)
                await cb.answer(f"✅ Resolution: {value.replace(':', 'x')}")
            
            # Return to custom menu
            await cb.message.edit_text(
                "⚙️ **Custom Encoding Settings**\n\n"
                + get_current_settings_text(user_id),
                reply_markup=get_custom_encoding_buttons()
            )
        
        elif data == "enc_speed_menu":
            # Show encoding speed selection
            await cb.message.edit_text(
                "⚡ **Select Encoding Speed**\n\n"
                "• Ultra Fast: Quick but larger files\n"
                "• Fast: Good balance\n"
                "• Medium: Recommended\n"
                "• Slow: Better compression\n"
                "• Very Slow: Maximum compression",
                reply_markup=get_encoding_speed_buttons()
            )
        
        elif data.startswith("enc_speed_"):
            # Speed preset selected
            preset = value
            settings_obj.set_custom_preset(preset)
            await cb.answer(f"✅ Speed: {preset.capitalize()}")
            
            # Return to custom menu
            await cb.message.edit_text(
                "⚙️ **Custom Encoding Settings**\n\n"
                + get_current_settings_text(user_id),
                reply_markup=get_custom_encoding_buttons()
            )
        
        elif data == "enc_audio_br_menu":
            # Show audio bitrate selection
            await cb.message.edit_text(
                "🔊 **Select Audio Bitrate**\n\n"
                "• 64k-96k: Low quality\n"
                "• 128k: Standard quality\n"
                "• 192k-256k: High quality\n"
                "• 320k: Maximum quality",
                reply_markup=get_audio_bitrate_buttons()
            )
        
        elif data.startswith("enc_audio_br_"):
            # Audio bitrate selected
            bitrate = value
            settings_obj.set_custom_audio_bitrate(bitrate)
            await cb.answer(f"✅ Audio bitrate: {bitrate}")
            
            # Return to custom menu
            await cb.message.edit_text(
                "⚙️ **Custom Encoding Settings**\n\n"
                + get_current_settings_text(user_id),
                reply_markup=get_custom_encoding_buttons()
            )
        
        elif data == "enc_audio_codec_menu":
            # Show audio codec selection
            await cb.message.edit_text(
                "🎵 **Select Audio Codec**\n\n"
                "• AAC: Best compatibility\n"
                "• Opus: Better quality at low bitrates\n"
                "• MP3: Universal compatibility\n"
                "• Copy: No re-encoding",
                reply_markup=get_audio_codec_buttons()
            )
        
        elif data.startswith("enc_audio_codec_"):
            # Audio codec selected
            codec = value
            settings_obj.set_custom_audio_codec(codec)
            await cb.answer(f"✅ Audio codec: {codec}")
            
            # Return to custom menu
            await cb.message.edit_text(
                "⚙️ **Custom Encoding Settings**\n\n"
                + get_current_settings_text(user_id),
                reply_markup=get_custom_encoding_buttons()
            )
        
        elif data == "enc_start_custom":
            # Start encoding with custom settings
            await cb.message.edit_text(
                "✅ **Ready to Encode**\n\n"
                + get_current_settings_text(user_id) +
                "\n\nConfirm to start encoding",
                reply_markup=get_encode_confirm_buttons()
            )
        
        elif data == "enc_confirm_start":
            # Actually start the encoding process
            await start_encoding_process(c, cb, user_id)
        
        elif data == "enc_cancel":
            # Cancel encoding
            await cb.message.edit_text(
                "❌ **Encoding Cancelled**\n\n"
                "Use /encode command to start again.",
                reply_markup=None
            )
        
        elif data == "enc_help":
            # Show help
            await cb.message.edit_text(
                get_help_text(),
                reply_markup=get_custom_encoding_buttons()
            )
        
        else:
            await cb.answer("🚧 Feature coming soon!", show_alert=False)
    
    except Exception as e:
        LOGGER.error(f"Encoding callback error: {e}")
        await cb.answer("❌ Something went wrong!", show_alert=True)


async def start_encoding_process(c: Client, cb: CallbackQuery, user_id: int):
    """Start the video encoding process"""
    try:
        # Check if user has videos in queue
        if user_id not in queueDB or not queueDB[user_id].get("videos"):
            await cb.message.edit_text(
                "❌ **No Videos to Encode!**\n\n"
                "Please send a video file first using /encode command."
            )
            return
        
        videos = queueDB[user_id]["videos"]
        
        if len(videos) == 0:
            await cb.message.edit_text(
                "❌ **No Videos in Queue!**\n\n"
                "Send a video file to encode."
            )
            return
        
        # Get the first video (for now, encode one at a time)
        video_msg_id = videos[0]
        
        # Create user download directory
        user_dir = f"downloads/{user_id}"
        os.makedirs(user_dir, exist_ok=True)
        
        # Download video
        await cb.message.edit_text(
            "📥 **Downloading Video...**\n\n"
            "⏳ Please wait..."
        )
        
        try:
            video_msg = await c.get_messages(user_id, video_msg_id)
            input_file = await video_msg.download(file_name=user_dir)
            
            LOGGER.info(f"Downloaded: {input_file}")
            
        except Exception as e:
            LOGGER.error(f"Download error: {e}")
            await cb.message.edit_text(
                "❌ **Download Failed!**\n\n"
                f"🚨 Error: `{str(e)}`"
            )
            return
        
        # Prepare output file
        file_ext = input_file.split('.')[-1]
        output_file = f"{user_dir}/encoded_{int(time.time())}.{file_ext}"
        
        # Start encoding
        LOGGER.info(f"Starting encoding: {input_file} -> {output_file}")
        
        encoded_file = await encode_video(
            input_file=input_file,
            output_file=output_file,
            user_id=user_id,
            progress_message=cb.message
        )
        
        if not encoded_file or not os.path.exists(encoded_file):
            await cb.message.edit_text(
                "❌ **Encoding Failed!**\n\n"
                "Please check your settings and try again."
            )
            # Clean up
            if os.path.exists(input_file):
                os.remove(input_file)
            return
        
        # Get file info for upload
        file_size = os.path.getsize(encoded_file)
        
        # Generate thumbnail
        thumbnail_path = None
        try:
            thumbnail_path = await take_screen_shot(encoded_file, user_dir, 10)
        except Exception as e:
            LOGGER.warning(f"Thumbnail generation failed: {e}")
        
        # Get video info
        from helpers.encoding_helper import get_video_info
        video_info = await get_video_info(encoded_file)
        
        width = video_info.get("width", 1280) if video_info else 1280
        height = video_info.get("height", 720) if video_info else 720
        duration = int(video_info.get("duration", 0)) if video_info else 0
        
        # Upload the encoded video
        from __init__ import UPLOAD_AS_DOC
        upload_mode = UPLOAD_AS_DOC.get(str(user_id), False)
        
        await uploadVideo(
            c, cb, encoded_file,
            width, height, duration,
            thumbnail_path, file_size, upload_mode
        )
        
        # Clean up
        try:
            if os.path.exists(input_file):
                os.remove(input_file)
            if os.path.exists(encoded_file):
                os.remove(encoded_file)
            if thumbnail_path and os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
        except Exception as e:
            LOGGER.warning(f"Cleanup error: {e}")
        
        # Clear user queue
        queueDB[user_id]["videos"] = []
        
        await cb.message.edit_text(
            "✅ **Encoding & Upload Complete!**\n\n"
            "📤 Your encoded video has been uploaded above ⬆️\n\n"
            "💡 Use /encode to encode another video"
        )
    
    except Exception as e:
        LOGGER.error(f"Encoding process error: {e}")
        await cb.message.edit_text(
            "❌ **Encoding Failed!**\n\n"
            f"🚨 Error: `{str(e)}`\n\n"
            "💡 Try again or contact support"
        )
