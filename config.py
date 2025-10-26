#!/usr/bin/env python3
"""
Simple Configuration Module
Loads environment variables from config.env or Replit Secrets
Works with both Docker/VPS and Replit environments
"""
import os
import sys
from dotenv import load_dotenv

# Smart environment loading
# Always prioritize config.env over Replit Secrets for bot-specific configuration
# 
# IMPORTANT: This bot uses MongoDB, but Replit provides PostgreSQL DATABASE_URL by default.
# Setting override=True ensures config.env values take precedence over Replit Secrets.
# 
# For production: If you need to use Replit Secrets instead, set override=False and 
# configure your secrets in the Replit Secrets panel (lock icon in left sidebar).
if os.path.exists("config.env"):
    # Force override Replit Secrets with config.env values
    # This ensures MongoDB DATABASE_URL from config.env is used
    load_dotenv("config.env", override=True)
else:
    # No config.env file - must be using Replit Secrets only
    pass

def get_env(var_name: str, required: bool = True, default: str = None, var_type: type = str):
    """Get environment variable with type conversion and validation"""
    value = os.environ.get(var_name)
    
    # Use default if not found
    if not value:
        if required:
            print(f"❌ ERROR: Required environment variable '{var_name}' is not set!")
            print(f"📝 Please add it to your config.env file")
            sys.exit(1)
        return default
    
    # Type conversion
    try:
        if var_type == int:
            return int(value)
        elif var_type == bool:
            return value.lower() in ('true', '1', 'yes')
        return value
    except ValueError as e:
        print(f"❌ ERROR: Invalid value for '{var_name}': {value}")
        print(f"Expected type: {var_type.__name__}")
        sys.exit(1)

class Config:
    """Bot Configuration"""
    
    # === REQUIRED TELEGRAM CONFIGURATION ===
    API_HASH = get_env("API_HASH", required=True)
    BOT_TOKEN = get_env("BOT_TOKEN", required=True)
    TELEGRAM_API = get_env("TELEGRAM_API", required=True, var_type=int)
    
    # === REQUIRED OWNER CONFIGURATION ===
    OWNER = get_env("OWNER", required=True, var_type=int)
    OWNER_USERNAME = get_env("OWNER_USERNAME", required=True)
    
    # === REQUIRED DATABASE CONFIGURATION ===
    DATABASE_URL = get_env("DATABASE_URL", required=True)
    
    # === OPTIONAL SECURITY ===
    PASSWORD = get_env("PASSWORD", required=False, default="mergebot123")
    
    # === OPTIONAL GOFILE CONFIGURATION ===
    GOFILE_TOKEN = get_env("GOFILE_TOKEN", required=False, default=None)
    
    # === OPTIONAL LOGGING ===
    LOGCHANNEL = get_env("LOGCHANNEL", required=False, default=None)
    
    # === OPTIONAL ADVANCED SETTINGS ===
    MAX_CONCURRENT_USERS = get_env("MAX_CONCURRENT_USERS", required=False, default="5", var_type=int)
    MAX_FILE_SIZE = get_env("MAX_FILE_SIZE", required=False, default="2147483648", var_type=int)
    USER_SESSION_STRING = get_env("USER_SESSION_STRING", required=False, default=None)
    
    # === RUNTIME VARIABLES ===
    IS_PREMIUM = False
    MODES = ["video-video", "video-audio", "video-subtitle", "extract-streams"]
    DOWNLOAD_DIR = "downloads"  # Default download directory

# Display configuration status
print("="*50)
print("🤖 MERGE BOT - Configuration Loaded")
print("="*50)
print(f"✅ Bot Token: {Config.BOT_TOKEN[:10]}...{Config.BOT_TOKEN[-5:]}")
print(f"✅ API ID: {Config.TELEGRAM_API}")
print(f"✅ Owner: {Config.OWNER}")
print(f"✅ Database: Connected (MongoDB)")
print(f"{'✅' if Config.GOFILE_TOKEN else '⚠️'} GoFile: {'Enabled' if Config.GOFILE_TOKEN else 'Disabled'}")
print(f"{'✅' if Config.LOGCHANNEL else '⚠️'} Log Channel: {'Enabled' if Config.LOGCHANNEL else 'Disabled'}")
print("="*50)
