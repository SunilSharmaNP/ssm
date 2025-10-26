# SSMERGE Bot - Complete Implementation Guide
## Required Modifications Based on User Requirements

### ✅ Current Status
- Bot is running and functional
- Database schema has `download_mode` field
- UserSettings class supports download mode preference
- Basic merge and encoding functionality working

### 🔧 Required Modifications

## 1. Group-Only Authorization (CRITICAL)
**Current Issue:** Bot works in private chats
**Required:** Bot should only work in authorized groups for normal users

**Files to Modify:**
- `bot.py` - Update authorization check in all command handlers
- `helpers/utils.py` - Modify `is_authorized_user()` logic

**Implementation:**
```python
# In bot.py - Add to each command handler
@app.on_message(filters.command("start"))
async def start_handler(c: Client, m: Message):
    user_id = m.from_user.id
    chat_id = m.chat.id
    
    # Owner/Admin always allowed everywhere
    if user_id == Config.OWNER or user_id in Config.ADMINS:
        # Allow
        pass
    else:
        # Normal users: Only in authorized groups
        if chat_id == user_id:  # Private chat
            return await m.reply_text(
                "🚫 **Private Chat Blocked**\n\n"
                "This bot works only in authorized groups.\n"
                f"Contact owner: @{Config.OWNER_USERNAME}"
            )
        else:  # Group chat - check if authorized
            # Check if group is in authorized list
            # Use database or config AUTH_GROUPS list
            pass
```

## 2. Download Mode Enforcement (CRITICAL)
**Current Issue:** No enforcement of TG File vs URL mode
**Required:** Block URLs in TG mode, block files in URL mode

**Files to Modify:**
- `bot.py` - Add message type checking
- `plugins/download_mode_settings.py` - Create settings UI

**Implementation:**
```python
# In bot.py - Add handler for videos and URLs
@app.on_message(filters.video & filters.private)
async def handle_video(c: Client, m: Message):
    user = UserSettings(m.from_user.id, m.from_user.first_name)
    
    # Check download mode
    if user.download_mode == "url":
        await m.reply_text(
            "🚫 **Telegram Files Blocked**\n\n"
            "Your download mode is set to **URL Download**.\n"
            "Send download links instead of files.\n\n"
            "💡 Change mode: Use `/settings` to switch to TG File mode."
        )
        return
    
    # Process TG file
    # Add to queue...

@app.on_message(filters.text & filters.private)
async def handle_text(c: Client, m: Message):
    text = m.text
    
    # Check if it's a URL
    if text.startswith("http"):
        user = UserSettings(m.from_user.id, m.from_user.first_name)
        
        # Check download mode
        if user.download_mode == "tg":
            await m.reply_text(
                "🚫 **URLs Blocked**\n\n"
                "Your download mode is set to **TG File Only**.\n"
                "Send Telegram video files instead of URLs.\n\n"
                "💡 Change mode: Use `/settings` to switch to URL Download mode."
            )
            return
        
        # Process URL
        # Download and add to queue...
```

## 3. Real-Time Progress Indicators (CRITICAL)
**Current Issue:** No progress tracking visible during operations
**Required:** Show progress for download/merge/encode/upload with cancel option

**Files to Modify:**
- `downloader.py` - Add progress callbacks
- `helpers/uploader.py` - Add upload progress
- `plugins/mergeVideo.py` - Add merge progress
- `plugins/encoding.py` - Add encoding progress

**Implementation Pattern:**
```python
# Progress update function
async def update_progress(status_msg, stage: str, current: int, total: int, start_time: float):
    elapsed = time.time() - start_time
    percentage = current / total if total > 0 else 0
    speed = current / elapsed if elapsed > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0
    
    progress_text = f"""
🎬 **{stage}**

{get_progress_bar(percentage)} `{percentage:.1%}`

📊 **Status:**
├ **Processed:** `{get_readable_file_size(current)}`
├ **Total:** `{get_readable_file_size(total)}`
├ **Speed:** `{get_readable_file_size(speed)}/s`
├ **ETA:** `{get_readable_time(eta)}`
└ **Elapsed:** `{get_readable_time(elapsed)}`

💡 **Use /cancel to stop this operation**
"""
    await status_msg.edit_text(progress_text)

# In download function
async def download_from_url(url, user_id, status_message):
    start_time = time.time()
    downloaded = 0
    
    async with session.get(url) as response:
        total_size = int(response.headers.get('content-length', 0))
        
        async for chunk in response.content.iter_chunked(1024*256):
            # Check for cancellation
            if is_download_cancelled(user_id):
                raise DownloadCancelledException()
            
            downloaded += len(chunk)
            
            # Update progress every 2 seconds
            if time.time() - last_update > 2:
                await update_progress(
                    status_message, "Downloading", 
                    downloaded, total_size, start_time
                )
```

## 4. Settings UI with Download Mode (CRITICAL)
**Current Issue:** Settings buttons not working/showing selection
**Required:** Working settings with visual selection indicators

**File to Create/Modify:**
- `plugins/download_mode_settings.py`

**Implementation:**
```python
# Settings callback handler
@app.on_callback_query(filters.regex("^settings"))
async def settings_handler(c: Client, cb: CallbackQuery):
    user = UserSettings(cb.from_user.id, cb.from_user.first_name)
    
    # Create settings text with current values
    settings_text = f"""
⚙️ **Your Settings**

👤 **Name:** {user.name}
🆔 **User ID:** `{user.user_id}`

**Current Settings:**
├ **Merge Mode:** {get_mode_name(user.merge_mode)}
├ **Download Mode:** {user.download_mode.upper()}
├ **Upload as Doc:** {"✅ Yes" if user.upload_as_doc else "❌ No"}
└ **Edit Metadata:** {"✅ Yes" if user.edit_metadata else "❌ No"}
"""
    
    # Create keyboard with selection indicators
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"{'✅' if user.download_mode == 'tg' else '☑️'} TG File Mode",
            callback_data="set_download_tg"
        )],
        [InlineKeyboardButton(
            f"{'✅' if user.download_mode == 'url' else '☑️'} URL Download Mode",
            callback_data="set_download_url"
        )],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
    ])
    
    await cb.message.edit_text(settings_text, reply_markup=keyboard)

# Download mode toggle handlers
@app.on_callback_query(filters.regex("^set_download_(tg|url)"))
async def set_download_mode(c: Client, cb: CallbackQuery):
    mode = "tg" if "tg" in cb.data else "url"
    user = UserSettings(cb.from_user.id, cb.from_user.first_name)
    user.download_mode = mode
    user.set()
    
    await cb.answer(
        f"✅ Download mode changed to: {mode.upper()}",
        show_alert=True
    )
    
    # Refresh settings display
    await settings_handler(c, cb)
```

## 5. Enhanced Cancel Functionality (CRITICAL)
**Current Issue:** FFmpeg continues running after cancel
**Required:** Proper process termination

**Files to Modify:**
- `bot.py` - Improve cancel command
- All processing modules - Add cancel checks

**Implementation:**
```python
# Global tracking
active_processes = {}  # {user_id: process_object}

# In cancel command
@app.on_message(filters.command(["cancel", "canx"]))
async def cancel_handler(c: Client, m: Message):
    user_id = m.from_user.id
    
    # Kill active FFmpeg process
    if user_id in active_processes:
        process = active_processes[user_id]
        try:
            process.terminate()
            await asyncio.sleep(2)
            if process.poll() is None:  # Still running
                process.kill()
            LOGGER.info(f"Killed FFmpeg process for user {user_id}")
        except:
            pass
        del active_processes[user_id]
    
    # Clear queue and cleanup
    clear_user_data(user_id)
    
    await m.reply_text(
        "🚫 **Operation Cancelled**\n\n"
        "✅ Process terminated\n"
        "🧹 Queue cleared\n"
        "💾 Temporary files deleted\n\n"
        "🚀 Ready for new tasks!"
    )

# In merge/encode functions
async def merge_videos(...):
    process = await asyncio.create_subprocess_exec(...)
    
    # Track process
    active_processes[user_id] = process
    
    try:
        # Process video
        ...
    finally:
        # Clean up
        if user_id in active_processes:
            del active_processes[user_id]
```

## 6. Custom Filename + Upload Destination Workflow (CRITICAL)
**Current Issue:** No filename customization or upload choice
**Required:** Ask for filename → Ask upload destination → Handle accordingly

**Files to Modify:**
- `plugins/mergeVideo.py`
- `plugins/encoding.py`

**Implementation:**
```python
# After merge/encode completes
async def handle_merge_complete(c: Client, user_id: int, merged_file: str):
    # Ask for custom filename
    await c.send_message(
        user_id,
        f"✅ **Merge Complete!**\n\n"
        f"📁 **Current Name:** `{os.path.basename(merged_file)}`\n\n"
        f"💬 **Send custom filename** (without extension)\n"
        f"or click **Skip** to use current name.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭ Skip", callback_data="skip_rename")]
        ])
    )
    
    # Set user state to wait for filename
    user_data[user_id]["state"] = "waiting_for_filename"
    user_data[user_id]["merged_file"] = merged_file

# Filename handler
@app.on_message(filters.text & filters.private & is_waiting_for_filename)
async def filename_handler(c: Client, m: Message):
    user_id = m.from_user.id
    custom_name = m.text.strip()
    
    # Validate filename
    # Rename file with custom name
    merged_file = user_data[user_id]["merged_file"]
    ext = os.path.splitext(merged_file)[1]
    new_path = os.path.join(os.path.dirname(merged_file), f"{custom_name}{ext}")
    os.rename(merged_file, new_path)
    user_data[user_id]["merged_file"] = new_path
    
    # Ask for upload destination
    await ask_upload_destination(c, user_id)

async def ask_upload_destination(c: Client, user_id: int):
    await c.send_message(
        user_id,
        "📤 **Upload Destination**\n\n"
        "Where do you want to upload this file?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 Telegram", callback_data="upload_tg")],
            [InlineKeyboardButton("🌐 GoFile", callback_data="upload_gofile")]
        ])
    )

# Upload destination handlers
@app.on_callback_query(filters.regex("^upload_(tg|gofile)"))
async def upload_destination_handler(c: Client, cb: CallbackQuery):
    user_id = cb.from_user.id
    destination = "telegram" if "tg" in cb.data else "gofile"
    merged_file = user_data[user_id]["merged_file"]
    
    if destination == "telegram":
        # Ask for thumbnail
        await cb.message.edit_text(
            "📸 **Send Thumbnail**\n\n"
            "Send a photo to use as thumbnail\n"
            "or click **Skip** to use auto-generated thumbnail.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏭ Skip", callback_data="skip_thumbnail")]
            ])
        )
        user_data[user_id]["state"] = "waiting_for_thumbnail"
    else:
        # Upload to GoFile directly
        await upload_to_gofile(c, cb, merged_file)

# Thumbnail handler
@app.on_message(filters.photo & filters.private & is_waiting_for_thumbnail)
async def thumbnail_handler(c: Client, m: Message):
    # Download thumbnail
    # Upload video with thumbnail
    # Tag user in completion message

# Upload with user tagging
async def upload_complete_notification(c: Client, user_id: int, file_info: dict):
    user = await c.get_users(user_id)
    await c.send_message(
        user_id,
        f"✅ **Upload Complete!** {user.mention}\n\n"
        f"📁 **File:** `{file_info['name']}`\n"
        f"📊 **Size:** `{file_info['size']}`\n"
        f"📍 **Location:** {file_info['location']}\n\n"
        f"🔗 **Link:** {file_info['link'] if 'link' in file_info else 'Sent above'}"
    )
```

## 7. Fix Stats Button (MINOR)
**Current Issue:** Stats callback not working
**Files to Modify:**
- `bot.py` or callback handler file

**Check:**
- Callback data matches button data
- Handler is registered properly
- User permission check is correct

---

## 📋 Implementation Priority

### PHASE 1 (Immediate - Core Functionality)
1. ✅ Group-only authorization
2. ✅ Download mode enforcement (TG vs URL blocking)
3. ✅ Settings UI with working buttons

### PHASE 2 (Essential - User Experience)
4. ✅ Progress indicators for all operations
5. ✅ Enhanced cancel with FFmpeg termination
6. ✅ Fix stats button

### PHASE 3 (Advanced - Workflow)
7. ✅ Custom filename workflow
8. ✅ Upload destination choice
9. ✅ Thumbnail support for TG uploads
10. ✅ User tagging in completion messages

---

## 🔍 Testing Checklist

- [ ] Bot blocks private chats for normal users
- [ ] Bot works in authorized groups
- [ ] TG File mode blocks URLs
- [ ] URL mode blocks TG files
- [ ] Settings show current selection with ✅
- [ ] Settings buttons are clickable and functional
- [ ] Download progress shows real-time updates
- [ ] Merge/Encode progress shows real-time updates
- [ ] Upload progress shows real-time updates
- [ ] Cancel button appears in all progress messages
- [ ] Cancel command kills FFmpeg properly
- [ ] After merge, bot asks for filename
- [ ] After filename, bot asks for upload destination
- [ ] GoFile upload works with custom filename
- [ ] TG upload asks for thumbnail
- [ ] Completion message tags user
- [ ] Stats button works for owner/admin

---

## 📝 Additional Notes

**Database Schema:** Already supports `download_mode` field ✅

**Configuration Required:**
- Add AUTH_GROUPS list in config.py
- Set proper owner ID and username
- Configure GoFile token (optional)

**Error Handling:**
- All operations should have try-catch blocks
- User-friendly error messages
- Automatic cleanup on errors

**Performance:**
- Use async/await throughout
- Progress updates throttled (max 1 per 2 seconds)
- Efficient file handling

---

## 🚀 Next Steps

1. Implement Phase 1 changes
2. Test thoroughly
3. Implement Phase 2 changes
4. Test thoroughly
5. Implement Phase 3 changes
6. Final comprehensive testing
7. Deploy to production

---

*This guide provides a complete roadmap for implementing all requested features.*
