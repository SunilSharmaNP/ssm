import time
from pyrogram import filters, Client as mergeApp
from pyrogram.types import Message, InlineKeyboardMarkup, CallbackQuery
from helpers.msg_utils import MakeButtons
from helpers.utils import UserSettings
from __init__ import LOGGER

@mergeApp.on_message(filters.command(["settings"]))
async def f1(c: mergeApp, m: Message):
    """FIXED: Settings command with proper user handling"""
    replay = await m.reply(text="Please wait", quote=True)
    usettings = UserSettings(m.from_user.id, m.from_user.first_name)
    
    # FIXED: Debug logging
    LOGGER.info(f"Settings - User: {usettings.user_id}, Allowed: {usettings.allowed}")
    
    if not usettings.allowed:
        await replay.edit_text(
            "🔐 **Access Required**\n\n"
            "Please login first using `/login <password>`\n"
            "Then try settings again."
        )
        return
    
    await userSettings(
        replay, m.from_user.id, m.from_user.first_name, m.from_user.last_name, usettings
    )

@mergeApp.on_callback_query(filters.regex(r"ch@ng3M0de_|toggleEdit_|toggleDownloadMode_"))
async def settings_callback(c: mergeApp, cb: CallbackQuery):
    """FIXED: Settings callback handler with download mode support"""
    data = cb.data
    user_id = cb.from_user.id
    usettings = UserSettings(user_id, cb.from_user.first_name)
    
    if not usettings.allowed:
        await cb.answer("🔐 Login required!", show_alert=True)
        return
    
    if data.startswith("ch@ng3M0de_"):
        # Extract mode change data
        parts = data.split("_")
        if len(parts) >= 3:
            new_mode = int(parts[2])
            usettings.merge_mode = new_mode
            usettings.set()
            await cb.answer(f"✅ Mode changed to {new_mode}")
    
    elif data.startswith("toggleEdit_"):
        usettings.edit_metadata = not usettings.edit_metadata
        usettings.set()
        await cb.answer(f"✅ Metadata editing: {'ON' if usettings.edit_metadata else 'OFF'}")
    
    elif data.startswith("toggleDownloadMode_"):
        # Toggle between 'tg' and 'url' modes
        current_mode = usettings.download_mode
        new_mode = "url" if current_mode == "tg" else "tg"
        usettings.download_mode = new_mode
        usettings.set()
        mode_name = "URL Download" if new_mode == "url" else "TG File"
        await cb.answer(f"✅ Download mode: {mode_name}", show_alert=True)
    
    # Refresh settings display
    await userSettings(
        cb.message, user_id, cb.from_user.first_name, cb.from_user.last_name, usettings
    )

async def userSettings(
    editable: Message,
    uid: int,
    fname,
    lname,
    usettings: UserSettings,
):
    """FIXED: User settings display function"""
    b = MakeButtons()
    
    if usettings.user_id:
        # FIXED: Mode string mapping
        mode_strings = {
            1: "Video 🎥 + Video 🎥",
            2: "Video 🎥 + Audio 🎵", 
            3: "Video 🎥 + Subtitle 📜",
            4: "Extract"
        }
        
        userMergeModeId = usettings.merge_mode
        userMergeModeStr = mode_strings.get(userMergeModeId, "Video 🎥 + Video 🎥")
        
        editMetadataStr = "✅" if usettings.edit_metadata else "❌"
        
        # Download mode display with visual indicators
        download_mode = usettings.download_mode
        if download_mode == "tg":
            download_mode_str = "📱 TG File"
            download_mode_indicator = "✅ TG | ☐ URL"
        else:
            download_mode_str = "🔗 URL Download"
            download_mode_indicator = "☐ TG | ✅ URL"
        
        uSettingsMessage = f"""
⚙️ **Merge Bot Settings**
━━━━━━━━━━━━━━━━━━━━━━
**User:** {fname} {lname or ''}

**Account Status:**
┣ 👦 **ID:** `{usettings.user_id}`
┣ {'🚫' if usettings.banned else '🫡'} **Ban Status:** {usettings.banned}
┗ {'⚡' if usettings.allowed else '❗'} **Allowed:** {usettings.allowed}

**Bot Settings:**
┣ Ⓜ️ **Merge Mode:** {userMergeModeStr}
┣ {'✅' if usettings.edit_metadata else '❌'} **Edit Metadata:** {usettings.edit_metadata}
┗ 📥 **Download Mode:** {download_mode_str}

**Download Mode:** {download_mode_indicator}
━━━━━━━━━━━━━━━━━━━━━━
💡 **Tip:** Click buttons below to change settings
"""
        
        markup = b.makebuttons(
            [
                "Merge mode",
                userMergeModeStr,
                "Edit Metadata", 
                editMetadataStr,
                "Download Mode",
                download_mode_indicator,
                "Close",
            ],
            [
                "tryotherbutton",
                f"ch@ng3M0de_{uid}_{(userMergeModeId%4)+1}",
                "tryotherbutton",
                f"toggleEdit_{uid}",
                "tryotherbutton",
                f"toggleDownloadMode_{uid}",
                "close",
            ],
            rows=3,
        )
        
        try:
            await editable.edit(
                text=uSettingsMessage, reply_markup=InlineKeyboardMarkup(markup)
            )
        except Exception as e:
            LOGGER.error(f"Settings edit error: {e}")
    
    else:
        # FIXED: Initialize new user
        usettings.name = fname
        usettings.merge_mode = 1
        usettings.allowed = False
        usettings.edit_metadata = False
        usettings.thumbnail = None
        usettings.set()
        await userSettings(editable, uid, fname, lname, usettings)
