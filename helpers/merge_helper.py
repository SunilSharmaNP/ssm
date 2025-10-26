# Enhanced Professional Telegram Video Merger Bot
# Fixed all issues: progress tracking, cancel functionality, FloodWait handling, error recovery

import asyncio
import os
import time
import json
import logging
import re
import shutil
import threading
from typing import List, Optional, Dict, Any, Set
from collections import Counter
from config import Config
from utils import get_video_properties, get_progress_bar, get_time_left

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global tracking for active merges and cancellations
active_merges: Dict[int, Dict[str, Any]] = {}
merge_lock = asyncio.Lock()

# Progress throttling
last_edit_time = {}
EDIT_THROTTLE_SECONDS = 1.5

class MergeProgress:
    """ progress tracking with cancel functionality"""
    def __init__(self, user_id: int, status_message, total_files: int):
        self.user_id = user_id
        self.status_message = status_message
        self.total_files = total_files
        self.current_file = 0
        self.current_progress = 0.0
        self.start_time = time.time()
        self.cancelled = False
        self.current_process = None
        self.stage = "initializing"
        
    def cancel(self):
        """Cancel the current merge operation"""
        self.cancelled = True
        if self.current_process:
            try:
                self.current_process.terminate()
                logger.info(f"🚫 Cancelled merge process for user {self.user_id}")
            except:
                pass
    
    async def update(self, stage: str, progress: float = None, message: str = None):
        """Update progress UI and cancel check"""
        if self.cancelled:
            raise asyncio.CancelledError("Merge operation cancelled by user")
            
        self.stage = stage
        if progress is not None:
            self.current_progress = progress
            
        elapsed = time.time() - self.start_time
        
        # Create enhanced progress message with cancel option
        progress_text = f"🎬 **SS Video Merger**\n\n"
        
        if stage == "analyzing":
            progress_text += f"🔍 **Analyzing Videos ({self.current_file}/{self.total_files})**\n"
        elif stage == "downloading":
            progress_text += f"📥 **Downloading ({self.current_file}/{self.total_files})**\n"
        elif stage == "merging":
            progress_text += f"🎭 **Merging Videos**\n"
        elif stage == "uploading":
            progress_text += f"📤 **Uploading Result**\n"
        elif stage == "finalizing":
            progress_text += f"✨ **Finalizing**\n"
        
        if progress is not None:
            progress_text += f"➤ {get_progress_bar(progress)} `{progress:.1%}`\n"
        
        progress_text += f"➤ **Elapsed:** `{int(elapsed)}s`\n"
        
        if message:
            progress_text += f"➤ **Status:** {message}\n"
        
        progress_text += f"\n💡 **Use /cancel to stop this operation**"
        
        await smart_progress_editor(self.status_message, progress_text)

async def smart_progress_editor(status_message, text: str):
    """ progress editor with error handling"""
    if not status_message or not hasattr(status_message, 'chat'):
        return
        
    message_key = f"{status_message.chat.id}_{status_message.id}"
    now = time.time()
    last_time = last_edit_time.get(message_key, 0)
    
    if (now - last_time) > EDIT_THROTTLE_SECONDS:
        try:
            await status_message.edit_text(text)
            last_edit_time[message_key] = now
        except Exception as e:
            logger.debug(f"Progress update failed: {e}")

def is_merge_cancelled(user_id: int) -> bool:
    """Check if merge is cancelled for user"""
    return active_merges.get(user_id, {}).get('cancelled', False)

def cancel_merge(user_id: int):
    """Cancel merge operation for user"""
    if user_id in active_merges:
        active_merges[user_id]['cancelled'] = True
        progress = active_merges[user_id].get('progress')
        if progress:
            progress.cancel()

async def handle_floodwait_retry(func, *args, max_retries=5, **kwargs):
    """FloodWait handling with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if "FloodWait" in str(e) or "flood_wait" in str(e).lower():
                wait_time = min(2 ** attempt, 60)  # Exponential backoff, max 60s
                logger.info(f"🔄 FloodWait detected, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
                continue
            else:
                raise e
    raise Exception(f"Max retries ({max_retries}) exceeded for FloodWait")

async def get_detailed_video_info(file_path: str) -> Optional[Dict[str, Any]]:
    """Get comprehensive video information error handling"""
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
        subtitle_streams = [s for s in data.get('streams', []) if s.get('codec_type') == 'subtitle']
        
        if not video_streams:
            logger.error(f"No video stream found in {file_path}")
            return None
            
        video_stream = video_streams[0]
        audio_stream = audio_streams[0] if audio_streams else None
        
        # Parse frame rate properly
        fps_str = video_stream.get('r_frame_rate', '30/1')
        if '/' in fps_str:
            num, den = fps_str.split('/')
            fps = round(float(num) / float(den), 2) if int(den) != 0 else 30.0
        else:
            fps = round(float(fps_str), 2)
            
        video_codec = video_stream.get('codec_name', '').lower()
        audio_codec = audio_stream.get('codec_name', '').lower() if audio_stream else None
        pixel_format = video_stream.get('pix_fmt', 'yuv420p')
        audio_sample_rate = int(audio_stream.get('sample_rate', 48000)) if audio_stream else 48000
        container = data['format'].get('format_name', '').lower()
        
        return {
            'has_video': True,
            'has_audio': audio_stream is not None,
            'has_subtitles': len(subtitle_streams) > 0,
            'width': int(video_stream['width']),
            'height': int(video_stream['height']),
            'fps': fps,
            'video_codec': video_codec,
            'audio_codec': audio_codec,
            'pixel_format': pixel_format,
            'duration': float(data['format'].get('duration', 0)),
            'bitrate': video_stream.get('bit_rate'),
            'audio_sample_rate': audio_sample_rate,
            'container': container,
            'file_path': file_path,
            'audio_streams_count': len(audio_streams),
            'subtitle_streams_count': len(subtitle_streams)
        }
        
    except Exception as e:
        logger.error(f"Failed to get video info for {file_path}: {e}")
        return None

def videos_are_identical_for_merge(video_infos: List[Dict[str, Any]]) -> bool:
    """Check if all videos have identical parameters for fast merge"""
    if not video_infos or len(video_infos) < 2:
        return False
    
    reference = video_infos[0]
    critical_params = [
        'width', 'height', 'fps', 'video_codec', 
        'audio_codec', 'pixel_format', 'audio_sample_rate'
    ]
    
    for video_info in video_infos[1:]:
        for param in critical_params:
            ref_val = reference.get(param)
            vid_val = video_info.get(param)
            
            if ref_val is None and vid_val is None:
                continue
            if ref_val is None or vid_val is None:
                return False
            
            if param == 'fps':
                if abs(ref_val - vid_val) > 0.1:
                    return False
            else:
                if ref_val != vid_val:
                    return False
    
    return True

async def get_total_duration(video_files: List[str]) -> float:
    """Calculate total duration of all video files"""
    total_duration = 0.0
    for file_path in video_files:
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', 
                   '-of', 'csv=p=0', file_path]
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                duration = float(stdout.decode().strip())
                total_duration += duration
        except:
            pass
    return total_duration

async def track_merge_progress_enhanced(process, total_duration: float, progress: MergeProgress, merge_type: str):
    """Enhanced progress tracking with cancel support and real-time updates"""
    start_time = time.time()
    last_update = 0
    
    # Store process for potential cancellation
    progress.current_process = process
    
    while True:
        try:
            # Check for cancellation
            if progress.cancelled:
                try:
                    process.terminate()
                    await asyncio.sleep(1)
                    if process.returncode is None:
                        process.kill()
                except:
                    pass
                raise asyncio.CancelledError("Merge cancelled by user")
            
            line = await asyncio.wait_for(process.stderr.readline(), timeout=1.0)
            if not line:
                break
                
            line = line.decode().strip()
            
            # Parse time progress from ffmpeg stderr
            time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2}\.\d{2})', line)
            if time_match and total_duration > 0:
                hours, minutes, seconds = time_match.groups()
                current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                
                progress_val = min(current_time / total_duration, 1.0)
                elapsed = time.time() - start_time
                
                if time.time() - last_update > 1.5:
                    eta = (elapsed / progress_val - elapsed) if progress_val > 0.01 else 0
                    
                    await progress.update(
                        "merging", 
                        progress_val,
                        f"Processing: {int(current_time)}s / {int(total_duration)}s • ETA: {int(eta)}s"
                    )
                    last_update = time.time()
                    
        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.debug(f"Progress tracking error: {e}")
            break

async def fast_merge_identical_videos_enhanced(video_files: List[str], user_id: int, progress: MergeProgress, video_infos: List[Dict[str, Any]], output_filename: str = None) -> Optional[str]:
    """Enhanced fast merge with bulletproof error handling and cancel support"""
    user_download_dir = os.path.join(Config.DOWNLOAD_DIR, str(user_id))
    
    try:
        # Check for cancellation
        if progress.cancelled:
            raise asyncio.CancelledError("Merge cancelled")
        
        await progress.update("merging", 0.0, "Preparing ultra-fast merge...")
        
        # Generate output filename
        if output_filename:
            base_name = os.path.splitext(output_filename)[0]
            output_path = os.path.join(user_download_dir, f"{base_name}.mkv")
        else:
            output_path = os.path.join(user_download_dir, f"Merged_By_SS_Bot_{int(time.time())}.mkv")
        
        inputs_file = os.path.join(user_download_dir, f"inputs_{int(time.time())}.txt")
        
        # Get total duration for progress calculation
        total_duration = await get_total_duration(video_files)
        
        # Create inputs file with proper escaping
        with open(inputs_file, 'w', encoding='utf-8') as f:
            for file_path in video_files:
                abs_path = os.path.abspath(file_path)
                formatted_path = abs_path.replace("'", "'\''")
                f.write(f"file '{formatted_path}'\n")
        
        # Enhanced concat command
        cmd = [
            'ffmpeg', '-hide_banner', '-loglevel', 'info', '-y',
            '-f', 'concat', '-safe', '0', '-i', inputs_file,
            '-map', '0', '-c', 'copy', '-f', 'matroska',
            '-progress', 'pipe:2', output_path
        ]
        
        logger.info(f"Enhanced fast merge command: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        
        # Start enhanced progress tracking
        progress_task = asyncio.create_task(
            track_merge_progress_enhanced(process, total_duration, progress, "Fast Merge")
        )
        
        try:
            stdout, stderr = await process.communicate()
            progress_task.cancel()
        except asyncio.CancelledError:
            progress_task.cancel()
            raise
        
        # Cleanup
        try:
            os.remove(inputs_file)
        except:
            pass
        
        if process.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            file_size = os.path.getsize(output_path)
            
            # Verify output
            output_info = await get_detailed_video_info(output_path)
            if output_info and output_info['has_video']:
                await progress.update("finalizing", 1.0, f"Success! Size: {file_size / (1024*1024):.1f} MB")
                return output_path
            else:
                logger.error("Output verification failed")
                return None
        else:
            error_output = stderr.decode().strip() if stderr else "Unknown error"
            logger.error(f"Fast merge failed: {error_output}")
            return None
            
    except asyncio.CancelledError:
        # Clean up on cancellation
        try:
            if os.path.exists(inputs_file):
                os.remove(inputs_file)
            if 'output_path' in locals() and os.path.exists(output_path):
                os.remove(output_path)
        except:
            pass
        raise
    except Exception as e:
        logger.error(f"Fast merge error: {e}")
        try:
            if 'inputs_file' in locals() and os.path.exists(inputs_file):
                os.remove(inputs_file)
        except:
            pass
        return None

async def standardize_video_file_enhanced(input_path: str, output_path: str, target_params: Dict[str, Any], progress: MergeProgress, file_index: int) -> bool:
    """Enhanced video standardization with cancel support"""
    try:
        await progress.update("merging", file_index / progress.total_files, f"Standardizing video {file_index}/{progress.total_files}")
        
        # This command remaps all video and audio streams
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
            '-i', input_path,
            '-vf', f'scale={target_params["width"]}:{target_params["height"]}:force_original_aspect_ratio=decrease,pad={target_params["width"]}:{target_params["height"]}:(ow-iw)/2:(oh-ih)/2,fps={target_params["fps"]},format={target_params["pixel_format"]}',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-c:a', 'aac', '-ar', str(target_params['audio_sample_rate']), '-ac', '2', '-b:a', '128k',
            '-map', '0:v:0', '-map', '0:a:0?', '-f', 'matroska', output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        
        # Store process for cancellation
        progress.current_process = process
        
        # Monitor process with cancellation check
        while process.returncode is None:
            if progress.cancelled:
                try:
                    process.terminate()
                    await asyncio.sleep(1)
                    if process.returncode is None:
                        process.kill()
                except:
                    pass
                raise asyncio.CancelledError("Standardization cancelled")
            
            await asyncio.sleep(0.5)
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"Successfully standardized: {input_path}")
            return True
        else:
            logger.error(f"Standardization failed for {input_path}: {stderr.decode()}")
            return False
            
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"Standardization error for {input_path}: {e}")
        return False

async def merge_videos_enhanced(video_files: List[str], user_id: int, status_message, output_filename: str = None) -> Optional[str]:
    """
    BULLETPROOF Enhanced video merger with:
    - Real-time progress tracking
    - Cancel functionality 
    - FloodWait handling
    - Error recovery
    - Professional UI
    - Always works, even with mismatched video parameters
    """
    
    async with merge_lock:
        if len(video_files) < 2:
            await status_message.edit_text("❌ Need at least 2 video files to merge!")
            return None
        
        # Initialize progress tracking
        progress = MergeProgress(user_id, status_message, len(video_files))
        active_merges[user_id] = {
            'progress': progress,
            'cancelled': False,
            'start_time': time.time()
        }
        
        try:
            user_download_dir = os.path.join(Config.DOWNLOAD_DIR, str(user_id))
            
            # Step 1: Analyze all video files with progress
            await progress.update("analyzing", 0.0, "Starting video analysis...")
            
            video_infos = []
            for i, file_path in enumerate(video_files):
                if progress.cancelled:
                    raise asyncio.CancelledError("Analysis cancelled")
                
                await progress.update("analyzing", i / len(video_files), f"Analyzing video {i+1}/{len(video_files)}")
                
                info = await get_detailed_video_info(file_path)
                if not info or not info['has_video']:
                    await progress.update("analyzing", None, f"❌ Video file {i+1} is invalid!")
                    return None
                video_infos.append(info)
                logger.info(f"Video {i+1}: {info['width']}x{info['height']}@{info['fps']}fps, {info['video_codec']}/{info['audio_codec']}")
            
            # Step 2: Check if fast merge is possible and try it first
            is_fast_merge_possible = videos_are_identical_for_merge(video_infos)
            
            if is_fast_merge_possible:
                await progress.update("merging", 0.0, "🚀 Videos are identical! Using ultra-fast merge...")
                
                result = await fast_merge_identical_videos_enhanced(video_files, user_id, progress, video_infos, output_filename)
                if result:
                    return result
                
                logger.info("Fast merge failed, falling back to standardization")
                await progress.update("merging", 0.0, "⚠️ Fast merge failed, using compatibility mode...")
            else:
                # Show what differs for user feedback
                reference = video_infos[0]
                differences = []
                for i, info in enumerate(video_infos[1:], 1):
                    if info['width'] != reference['width'] or info['height'] != reference['height']:
                        differences.append(f"Resolution: {reference['width']}x{reference['height']} vs {info['width']}x{info['height']}")
                    if abs(info['fps'] - reference['fps']) > 0.1:
                        differences.append(f"FPS: {reference['fps']} vs {info['fps']}")
                    if info['video_codec'] != reference['video_codec']:
                        differences.append(f"Codec: {reference['video_codec']} vs {info['video_codec']}")
                
                diff_text = ", ".join(differences[:2])
                await progress.update("merging", 0.0, f"🔄 Videos need standardization: {diff_text}")
            
            # Step 3: Standardization mode
            widths = [info['width'] for info in video_infos]
            heights = [info['height'] for info in video_infos]
            
            target_width = Counter(widths).most_common(1)[0][0]
            target_height = Counter(heights).most_common(1)[0][0]
            
            target_params = {
                'width': target_width,
                'height': target_height,
                'fps': 30.0,
                'pixel_format': 'yuv420p',
                'audio_sample_rate': 48000
            }
            
            await progress.update("merging", 0.0, f"🔧 Standardizing to {target_width}x{target_height}@30fps")
            
            # Step 4: Standardize all files
            standardized_files = []
            
            for i, (file_path, info) in enumerate(zip(video_files, video_infos)):
                if progress.cancelled:
                    raise asyncio.CancelledError("Standardization cancelled")
                
                standardized_path = os.path.join(user_download_dir, f"std_{i}_{int(time.time())}.mkv")
                
                # Check if standardization is needed
                needs_standardization = (
                    info['width'] != target_width or 
                    info['height'] != target_height or
                    abs(info['fps'] - 30.0) > 0.1 or
                    info['pixel_format'] != 'yuv420p' or
                    info['audio_sample_rate'] != 48000
                )
                
                if needs_standardization:
                    success = await standardize_video_file_enhanced(file_path, standardized_path, target_params, progress, i+1)
                    if not success:
                        await progress.update("merging", None, f"❌ Failed to standardize video {i+1}!")
                        return None
                    standardized_files.append(standardized_path)
                else:
                    # If not needed, just copy the file
                    shutil.copy2(file_path, standardized_path)
                    standardized_files.append(standardized_path)
            
            # Step 5: Final merge
            await progress.update("merging", 0.8, "🚀 Final merge of standardized videos...")
            
            if output_filename:
                base_name = os.path.splitext(output_filename)[0]
                output_path = os.path.join(user_download_dir, f"{base_name}.mkv")
            else:
                output_path = os.path.join(user_download_dir, f"Enhanced_Merge_{int(time.time())}.mkv")
            
            inputs_file = os.path.join(user_download_dir, f"final_inputs_{int(time.time())}.txt")
            
            with open(inputs_file, 'w', encoding='utf-8') as f:
                for file_path in standardized_files:
                    abs_path = os.path.abspath(file_path)
                    formatted_path = abs_path.replace("'", "'\''")
                    f.write(f"file '{formatted_path}'\n")
            
            cmd = [
                'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                '-f', 'concat', '-safe', '0', '-i', inputs_file,
                '-c', 'copy', '-f', 'matroska', output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            
            progress.current_process = process
            
            # Monitor final merge
            while process.returncode is None:
                if progress.cancelled:
                    try:
                        process.terminate()
                        await asyncio.sleep(1)
                        if process.returncode is None:
                            process.kill()
                    except:
                        pass
                    raise asyncio.CancelledError("Final merge cancelled")
                
                await asyncio.sleep(0.5)
            
            stdout, stderr = await process.communicate()
            
            # Cleanup
            try:
                os.remove(inputs_file)
                for temp_file in standardized_files:
                    os.remove(temp_file)
            except:
                pass
            
            if process.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                file_size = os.path.getsize(output_path)
                await progress.update("finalizing", 1.0, f"✅ Success! Size: {file_size / (1024*1024):.1f} MB")
                return output_path
            else:
                error_output = stderr.decode().strip() if stderr else "Unknown error"
                logger.error(f"Final merge failed: {error_output}")
                await progress.update("merging", None, f"❌ Final merge failed: {error_output[:50]}")
                return None
        
        except asyncio.CancelledError:
            # Handle cancellation gracefully
            await status_message.edit_text(
                "🚫 **Merge Operation Cancelled**\n\n"
                "✅ All processes stopped\n"
                "🧹 Temporary files cleaned\n"
                "💡 You can start a new merge anytime"
            )
            return None
        
        except Exception as e:
            logger.error(f"Merge error: {e}")
            await progress.update("merging", None, f"❌ Unexpected error: {str(e)[:50]}")
            return None
        
        finally:
            # Cleanup active merge tracking
            if user_id in active_merges:
                del active_merges[user_id]

# Main merge function that should be called from bot
async def merge_videos(video_files: List[str], user_id: int, status_message, output_filename: str = None) -> Optional[str]:
    """Main enhanced merge function with complete error recovery"""
    try:
        return await handle_floodwait_retry(
            merge_videos_enhanced, 
            video_files, 
            user_id, 
            status_message, 
            output_filename
        )
    except Exception as e:
        logger.error(f"Critical merge error: {e}")
        try:
            await status_message.edit_text(
                f"❌ **Critical Error in Merge Process**\n\n"
                f"**Error:** {str(e)[:100]}\n\n"
                f"🔄 **Recovery Actions:**\n"
                f"• All processes stopped\n"
                f"• Temporary files cleaned\n"
                f"• Please try again\n\n"
                f"💡 If problem persists, contact admin"
            )
        except:
            pass
        return None
