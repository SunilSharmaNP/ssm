from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from pyrogram.types import CallbackQuery
from config import Config
from __init__ import LOGGER, MERGE_MODE


class Database(object):
    client = MongoClient(Config.DATABASE_URL)
    mergebot = client.MergeBot


async def addUser(uid, fname, lname):
    try:
        userDetails = {
            "_id": uid,
            "name": f"{fname} {lname}",
        }
        Database.mergebot.users.insert_one(userDetails)
        LOGGER.info(f"New user added id={uid}\n{fname} {lname} \n")
    except DuplicateKeyError:
        LOGGER.info(f"Duplicate Entry Found for id={uid}\n{fname} {lname} \n")
    return


async def broadcast():
    a = Database.mergebot.mergeSettings.find({})
    return a


async def allowUser(uid, fname, lname):
    try:
        a = Database.mergebot.allowedUsers.insert_one(
            {
                "_id": uid,
            }
        )
    except DuplicateKeyError:
        LOGGER.info(f"Duplicate Entry Found for id={uid}\n{fname} {lname} \n")
    return


async def allowedUser(uid):
    a = Database.mergebot.allowedUsers.find_one({"_id": uid})
    try:
        if uid == a["_id"]:
            return True
    except TypeError:
        return False


async def saveThumb(uid, fid):
    try:
        Database.mergebot.thumbnail.insert_one({"_id": uid, "thumbid": fid})
    except DuplicateKeyError:
        Database.mergebot.thumbnail.replace_one({"_id": uid}, {"thumbid": fid})


async def delThumb(uid):
    Database.mergebot.thumbnail.delete_many({"_id": uid})
    return True


async def getThumb(uid):
    res = Database.mergebot.thumbnail.find_one({"_id": uid})
    return res["thumbid"]


async def deleteUser(uid):
    Database.mergebot.mergeSettings.delete_many({"_id": uid})


async def addUserRcloneConfig(cb: CallbackQuery, fileId):
    try:
        await cb.message.edit("Adding file to DB")
        uid = cb.from_user.id
        Database.mergebot.rcloneData.insert_one({"_id": uid, "rcloneFileId": fileId})
    except Exception as err:
        LOGGER.info("Updating rclone")
        await cb.message.edit("Updating file in DB")
        uid = cb.from_user.id
        Database.mergebot.rcloneData.replace_one({"_id": uid}, {"rcloneFileId": fileId})
    await cb.message.edit("Done")
    return


async def getUserRcloneConfig(uid):
    try:
        res = Database.mergebot.rcloneData.find_one({"_id": uid})
        return res["rcloneFileId"]
    except Exception as err:
        return None


def getUserMergeSettings(uid: int):
    try:
        res_cur = Database.mergebot.mergeSettings.find_one({"_id": uid})
        return res_cur
    except Exception as e:
        LOGGER.info(e)
        return None


def setUserMergeSettings(uid: int, name: str, mode, edit_metadata, banned, allowed, thumbnail, upload_as_doc=False, upload_to_drive=False, download_mode="tg"):
    """Enhanced function with download mode preference"""
    modes = Config.MODES
    if uid:
        try:
            Database.mergebot.mergeSettings.insert_one(
                document={
                    "_id": uid,
                    "name": name,
                    "user_settings": {
                        "merge_mode": mode,
                        "edit_metadata": edit_metadata,
                        "upload_as_doc": upload_as_doc,
                        "upload_to_drive": upload_to_drive,
                        "download_mode": download_mode,
                    },
                    "isAllowed": allowed,
                    "isBanned": banned,
                    "thumbnail": thumbnail,
                }
            )
            LOGGER.info("User {} settings saved - Mode: {}, Download: {}".format(uid, modes[mode - 1] if mode <= len(modes) else "Unknown", download_mode))
        except Exception:
            Database.mergebot.mergeSettings.replace_one(
                filter={"_id": uid},
                replacement={
                    "name": name,
                    "user_settings": {
                        "merge_mode": mode,
                        "edit_metadata": edit_metadata,
                        "upload_as_doc": upload_as_doc,
                        "upload_to_drive": upload_to_drive,
                        "download_mode": download_mode,
                    },
                    "isAllowed": allowed,
                    "isBanned": banned,
                    "thumbnail": thumbnail,
                },
            )
            LOGGER.info("User {} settings updated - Mode: {}, Download: {}".format(uid, modes[mode - 1] if mode <= len(modes) else "Unknown", download_mode))
        MERGE_MODE[uid] = mode
    # elif mode == 2:
    #     try:
    #         Database.mergebot.mergeModes.insert_one(
    #             document={"_id": uid, modes[0]: 0, modes[1]: 1, modes[2]: 0}
    #         )
    #         LOGGER.info("User {} Mode updated to {}".format(uid, modes[1]))
    #     except Exception:
    #         rep = Database.mergebot.mergeModes.replace_one(
    #             filter={"_id": uid},
    #             replacement={modes[0]: 0, modes[1]: 1, modes[2]: 0},
    #         )
    #         LOGGER.info("User {} Mode updated to {}".format(uid, modes[1]))
    #     MERGE_MODE[uid] = 2
    #     # Database.mergebot.mergeModes.delete_many({'id':uid})
    # elif mode == 3:
    #     try:
    #         Database.mergebot.mergeModes.insert_one(
    #             document={"_id": uid, modes[0]: 0, modes[1]: 0, modes[2]: 1}
    #         )
    #         LOGGER.info("User {} Mode updated to {}".format(uid, modes[2]))
    #     except Exception:
    #         rep = Database.mergebot.mergeModes.replace_one(
    #             filter={"_id": uid},
    #             replacement={modes[0]: 0, modes[1]: 0, modes[2]: 1},
    #         )
    #         LOGGER.info("User {} Mode updated to {}".format(uid, modes[2]))
    #     MERGE_MODE[uid]=3
    LOGGER.info(MERGE_MODE)


def enableMetadataToggle(uid: int, value: bool):
    """Enable metadata editing for user"""
    try:
        result = Database.mergebot.mergeSettings.update_one(
            {"_id": uid},
            {"$set": {"user_settings.edit_metadata": value}}
        )
        LOGGER.info(f"Metadata toggle enabled for user {uid}: {value}")
        return result.modified_count > 0
    except Exception as e:
        LOGGER.error(f"Error enabling metadata toggle: {e}")
        return False


def disableMetadataToggle(uid: int, value: bool):
    """Disable metadata editing for user"""
    try:
        result = Database.mergebot.mergeSettings.update_one(
            {"_id": uid},
            {"$set": {"user_settings.edit_metadata": value}}
        )
        LOGGER.info(f"Metadata toggle disabled for user {uid}: {value}")
        return result.modified_count > 0
    except Exception as e:
        LOGGER.error(f"Error disabling metadata toggle: {e}")
        return False


# Authorized Chats Management

async def add_authorized_chat(chat_id: int, chat_title: str = None):
    """Add or update authorized group/chat."""
    try:
        from datetime import datetime
        data = {
            "_id": chat_id,
            "chat_title": chat_title or f"Chat {chat_id}",
            "added_date": datetime.utcnow(),
            "is_active": True
        }
        Database.mergebot.authorized_chats.update_one(
            {"_id": chat_id},
            {"$setOnInsert": data},
            upsert=True
        )
        LOGGER.info(f"Authorized chat added: {chat_id} - {chat_title}")
        return True
    except Exception as e:
        LOGGER.error(f"Error adding authorized chat {chat_id}: {e}")
        return False


async def remove_authorized_chat(chat_id: int):
    """Remove authorized chat."""
    try:
        result = Database.mergebot.authorized_chats.delete_one({"_id": chat_id})
        LOGGER.info(f"Authorized chat removed: {chat_id}")
        return result.deleted_count > 0
    except Exception as e:
        LOGGER.error(f"Error removing authorized chat {chat_id}: {e}")
        return False


async def is_authorized_chat(chat_id: int):
    """Check if chat is in authorized list."""
    try:
        doc = Database.mergebot.authorized_chats.find_one({"_id": chat_id})
        return bool(doc and doc.get("is_active", False))
    except Exception as e:
        LOGGER.error(f"Error checking authorized chat {chat_id}: {e}")
        return False


async def get_authorized_chats():
    """Fetch all active authorized chats."""
    try:
        cursor = Database.mergebot.authorized_chats.find({"is_active": True})
        return list(cursor)
    except Exception as e:
        LOGGER.error(f"Error getting authorized chats: {e}")
        return []


def set_download_mode(uid: int, mode: str):
    """Set user's download mode (tg or url)"""
    try:
        result = Database.mergebot.mergeSettings.update_one(
            {"_id": uid},
            {"$set": {"user_settings.download_mode": mode}}
        )
        LOGGER.info(f"Download mode set for user {uid}: {mode}")
        return result.modified_count > 0
    except Exception as e:
        LOGGER.error(f"Error setting download mode: {e}")
        return False


def get_download_mode(uid: int):
    """Get user's download mode"""
    try:
        res = Database.mergebot.mergeSettings.find_one({"_id": uid})
        if res and "user_settings" in res:
            return res["user_settings"].get("download_mode", "tg")
        return "tg"  # Default mode
    except Exception as e:
        LOGGER.error(f"Error getting download mode: {e}")
        return "tg"
