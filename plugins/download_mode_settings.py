# plugins/download_mode_settings.py - Download Mode Settings Plugin
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from helpers.utils import UserSettings
from __init__ import LOGGER

@Client.on_message(filters.command(["settings", "downloadsettings"]) & filters.private)
async def download_settings_handler(c: Client, m: Message):
    """Show download mode settings"""
    user = UserSettings(m.from_user.id, m.from_user.first_name)
    
    if user.banned:
        await m.reply_text("🚫 **Access Denied** - You are banned", quote=True)
        return
    
    if not user.allowed:
        await m.reply_text(
            "❌ **Unauthorized**\n\n"
            "Please use /login to access the bot",
            quote=True
        )
        return
    
    # Get current mode
    current_mode = user.download_mode
    
    # Create buttons with visual selection indicator
    tg_text = "✅ TG File Mode" if current_mode == "tg" else "TG File Mode"
    url_text = "✅ URL Download Mode" if current_mode == "url" else "URL Download Mode"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(tg_text, callback_data="dlmode_tg")],
        [InlineKeyboardButton(url_text, callback_data="dlmode_url")],
        [InlineKeyboardButton("🔙 Close", callback_data="close_settings")]
    ])
    
    settings_text = f"""
⚙️ **Download Mode Settings**

**Current Mode:** `{current_mode.upper()}`

📥 **TG File Mode:**
• Accept video files from Telegram
• Block URL links
• Fast direct download

🔗 **URL Download Mode:**
• Accept direct download URLs
• Block Telegram video files
• Support for DDL and GoFile.io

💡 **Select your preferred download mode below:**
"""
    
    await m.reply_text(settings_text, reply_markup=keyboard, quote=True)


@Client.on_callback_query(filters.regex(r"^dlmode_"))
async def download_mode_callback(c: Client, cb: CallbackQuery):
    """Handle download mode selection"""
    user = UserSettings(cb.from_user.id, cb.from_user.first_name)
    
    if user.banned:
        await cb.answer("🚫 You are banned", show_alert=True)
        return
    
    if not user.allowed:
        await cb.answer("❌ Unauthorized", show_alert=True)
        return
    
    # Get selected mode from callback data
    mode = cb.data.split("_")[1]  # tg or url
    
    # Update user settings
    user.download_mode = mode
    user.set()
    
    LOGGER.info(f"User {user.user_id} changed download mode to: {mode}")
    
    # Update button display
    tg_text = "✅ TG File Mode" if mode == "tg" else "TG File Mode"
    url_text = "✅ URL Download Mode" if mode == "url" else "URL Download Mode"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(tg_text, callback_data="dlmode_tg")],
        [InlineKeyboardButton(url_text, callback_data="dlmode_url")],
        [InlineKeyboardButton("🔙 Close", callback_data="close_settings")]
    ])
    
    settings_text = f"""
⚙️ **Download Mode Settings**

**Current Mode:** `{mode.upper()}`

📥 **TG File Mode:**
• Accept video files from Telegram
• Block URL links
• Fast direct download

🔗 **URL Download Mode:**
• Accept direct download URLs
• Block Telegram video files
• Support for DDL and GoFile.io

💡 **Select your preferred download mode below:**
"""
    
    try:
        await cb.edit_message_text(settings_text, reply_markup=keyboard)
        await cb.answer(f"✅ Mode changed to {mode.upper()}", show_alert=False)
    except Exception as e:
        LOGGER.error(f"Error updating message: {e}")
        await cb.answer(f"✅ Mode changed to {mode.upper()}", show_alert=True)


@Client.on_callback_query(filters.regex(r"^close_settings$"))
async def close_settings_callback(c: Client, cb: CallbackQuery):
    """Close settings menu"""
    try:
        await cb.message.delete()
        await cb.answer("Settings closed", show_alert=False)
    except Exception as e:
        LOGGER.error(f"Error deleting message: {e}")
        await cb.answer("Settings closed", show_alert=True)
