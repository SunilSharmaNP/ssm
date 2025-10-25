# helpers/merge_helper.py - Merge Process Handler
import os
import time
import asyncio
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from __init__ import queueDB, LOGGER
from helpers.utils import get_readable_file_size, get_readable_time

async def start_merge_process(c, cb, user_id):
    """Start the merge process for user queue"""
    try:
        if user_id not in queueDB:
            await cb.message.edit_text("❌ **Queue Empty!**\nPlease add videos first.")
            return
            
        videos = queueDB[user_id]["videos"]
        audios = queueDB[user_id].get("audios", [])
        subtitles = queueDB[user_id].get("subtitles", [])
        
        if len(videos) < 2:
            await cb.message.edit_text("❌ **Need at least 2 videos to merge!**")
            return
        
        # Create user download directory
        user_dir = f"downloads/{user_id}"
        os.makedirs(user_dir, exist_ok=True)
        
        # Start progress message
        progress_msg = await cb.message.edit_text(
            "📥 **Downloading Files...**\n\n"
            f"🎬 Videos: {len(videos)}\n"
            f"🎵 Audios: {len(audios)}\n" 
            f"📝 Subtitles: {len(subtitles)}\n\n"
            "⏳ Please wait..."
        )
        
        # Download all files
        downloaded_files = []
        
        for i, video_id in enumerate(videos):
            try:
                await progress_msg.edit_text(
                    f"📥 **Downloading Video {i+1}/{len(videos)}...**\n\n"
                    "⏳ Please wait..."
                )
                
                # Get message
                video_msg = await c.get_messages(user_id, video_id)
                
                # Download file with unique filename to avoid conflicts
                filename = f"{user_dir}/video_{i+1}_{video_id}.mp4"
                file_path = await video_msg.download(file_name=filename)
                downloaded_files.append(file_path)
                
                LOGGER.info(f"Downloaded: {file_path}")
                
            except Exception as e:
                LOGGER.error(f"Download error for video {video_id}: {e}")
                continue
        
        if len(downloaded_files) < 2:
            await progress_msg.edit_text(
                "❌ **Download Failed!**\n\n"
                "Could not download enough files to merge.\n"
                "Please try again."
            )
            return
        
        # Start merge process
        await progress_msg.edit_text(
            "🔄 **Merging Videos...**\n\n"
            f"📁 Files: {len(downloaded_files)}\n"
            "⏳ This may take a while..."
        )
        
        # Simple merge using ffmpeg
        output_file = f"{user_dir}/merged_video_{int(time.time())}.mp4"
        
        try:
            # Create file list for ffmpeg concat
            file_list_path = f"{user_dir}/file_list.txt"
            with open(file_list_path, 'w') as f:
                for file_path in downloaded_files:
                    f.write(f"file '{os.path.abspath(file_path)}'\n")
            
            # Run ffmpeg merge command
            ffmpeg_cmd = [
                "ffmpeg", "-f", "concat", "-safe", "0",
                "-i", file_list_path,
                "-c", "copy", output_file, "-y"
            ]
            
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(output_file):
                # Success - upload merged video
                file_size = os.path.getsize(output_file)
                
                await progress_msg.edit_text(
                    "📤 **Uploading Merged Video...**\n\n"
                    f"📊 Size: {get_readable_file_size(file_size)}\n"
                    "⏳ Please wait..."
                )
                
                # Upload merged video
                await c.send_video(
                    chat_id=user_id,
                    video=output_file,
                    caption=f"✅ **Merge Complete!**\n\n"
                           f"🎬 Merged {len(downloaded_files)} videos\n"
                           f"📊 Size: {get_readable_file_size(file_size)}",
                    supports_streaming=True
                )
                
                # Clean up
                try:
                    for file_path in downloaded_files:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    if os.path.exists(output_file):
                        os.remove(output_file)
                    if os.path.exists(file_list_path):
                        os.remove(file_list_path)
                except:
                    pass
                
                # Clear user queue
                queueDB[user_id] = {"videos": [], "subtitles": [], "audios": []}
                
                await progress_msg.edit_text(
                    "✅ **Merge Completed Successfully!**\n\n"
                    f"🎬 Merged {len(downloaded_files)} videos\n"
                    f"📊 Final Size: {get_readable_file_size(file_size)}\n"
                    "📤 Video uploaded above ⬆️"
                )
                
            else:
                # Merge failed
                error_msg = stderr.decode() if stderr else "Unknown error"
                await progress_msg.edit_text(
                    "❌ **Merge Failed!**\n\n"
                    f"🚨 Error: FFmpeg process failed\n"
                    "💡 Make sure FFmpeg is installed and try again."
                )
                LOGGER.error(f"FFmpeg error: {error_msg}")
                
        except Exception as e:
            await progress_msg.edit_text(
                "❌ **Merge Failed!**\n\n"
                f"🚨 Error: {str(e)}\n"
                "💡 Please try again or contact support."
            )
            LOGGER.error(f"Merge process error: {e}")
            
    except Exception as e:
        await cb.message.edit_text(
            "❌ **Process Failed!**\n\n" 
            f"🚨 Error: {str(e)}\n"
            "💡 Please try again."
        )
        LOGGER.error(f"Start merge process error: {e}")
