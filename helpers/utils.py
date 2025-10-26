# helpers/utils.py - FIXED VERSION
import pickle
import os
import threading
import time
from helpers.database import setUserMergeSettings, getUserMergeSettings

SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]

def get_readable_file_size(size_in_bytes) -> str:
    if size_in_bytes is None:
        return "0B"
    index = 0
    while size_in_bytes >= 1024:
        size_in_bytes /= 1024
        index += 1
    try:
        return f"{round(size_in_bytes, 2)}{SIZE_UNITS[index]}"
    except IndexError:
        return "File too large"

def get_readable_time(seconds: float) -> str:
    result = ""
    seconds = int(seconds)
    (days, remainder) = divmod(seconds, 86400)
    days = int(days)
    if days != 0:
        result += f"{days}d"
    (hours, remainder) = divmod(remainder, 3600)
    hours = int(hours)
    if hours != 0:
        result += f"{hours}h"
    (minutes, seconds) = divmod(remainder, 60)
    minutes = int(minutes)
    if minutes != 0:
        result += f"{minutes}m"
    seconds = int(seconds)
    result += f"{seconds}s"
    return result

def get_path_size(path: str) -> int:
    """Calculate total size of a directory or file in bytes"""
    if not os.path.exists(path):
        return 0
    
    if os.path.isfile(path):
        return os.path.getsize(path)
    
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
                except Exception as e:
                    print(f"Error getting size of {file_path}: {e}")
                    continue
    except Exception as e:
        print(f"Error walking directory {path}: {e}")
        return 0
    
    return total_size

class UserSettings(object):
    """Enhanced UserSettings class with download mode preference"""
    
    def __init__(self, uid: int, name: str):
        self.user_id: int = uid
        self.name: str = name
        self.merge_mode: int = 1
        self.edit_metadata: bool = False
        self.allowed: bool = False
        self.thumbnail = None
        self.banned: bool = False
        self.upload_as_doc: bool = False
        self.upload_to_drive: bool = False
        self.download_mode: str = "tg"  # NEW: TG File vs URL Download mode
        self.get()

    def get(self):
        """Get user settings from database"""
        try:
            cur = getUserMergeSettings(self.user_id)
            if cur is not None:
                self.name = cur.get("name", self.name)
                user_settings = cur.get("user_settings", {})
                self.merge_mode = user_settings.get("merge_mode", 1)
                self.edit_metadata = user_settings.get("edit_metadata", False)
                self.upload_as_doc = user_settings.get("upload_as_doc", False)
                self.upload_to_drive = user_settings.get("upload_to_drive", False)
                self.download_mode = user_settings.get("download_mode", "tg")  # NEW
                self.allowed = cur.get("isAllowed", False)
                self.thumbnail = cur.get("thumbnail", None)
                self.banned = cur.get("isBanned", False)
                
                return {
                    "uid": self.user_id,
                    "name": self.name,
                    "user_settings": {
                        "merge_mode": self.merge_mode,
                        "edit_metadata": self.edit_metadata,
                        "upload_as_doc": self.upload_as_doc,
                        "upload_to_drive": self.upload_to_drive,
                        "download_mode": self.download_mode,
                    },
                    "isAllowed": self.allowed,
                    "isBanned": self.banned,
                    "thumbnail": self.thumbnail,
                }
            else:
                # New user - set defaults and save
                return self.set()
        except Exception as e:
            # Database error - set defaults and save
            print(f"Database error in get(): {e}")
            return self.set()

    def set(self):
        """Save all user settings to database"""
        try:
            setUserMergeSettings(
                uid=self.user_id,
                name=self.name,
                mode=self.merge_mode,
                edit_metadata=self.edit_metadata,
                banned=self.banned,
                allowed=self.allowed,
                thumbnail=self.thumbnail,
                upload_as_doc=self.upload_as_doc,
                upload_to_drive=self.upload_to_drive,
                download_mode=self.download_mode,  # NEW
            )
            return self.get()
        except Exception as e:
            print(f"Database error in set(): {e}")
            return None

    def is_allowed(self) -> bool:
        """Check if user is allowed"""
        return self.allowed and not self.banned

    def __str__(self):
        return f"UserSettings(uid={self.user_id}, name='{self.name}', allowed={self.allowed}, banned={self.banned})"
