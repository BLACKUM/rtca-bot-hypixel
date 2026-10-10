from services import json_utils as json
import os
import time
import aiofiles
from typing import List, Optional, Tuple
from core.logger import log_info, log_error
from services.api import get_uuid

DAILY_DATA_FILE = "data/daily_data.json"



class DailyManager:
    def __init__(self):
        self.data = {
            "users": {}
        }
    async def initialize(self):
        await self.load_data()

    async def load_data(self):
        if not os.path.exists(DAILY_DATA_FILE):
            log_info("No daily data file found, starting fresh.")
            await self._save_data()
            return

        try:
            async with aiofiles.open(DAILY_DATA_FILE, json.get_read_mode()) as f:
                content = await f.read()
                loaded = json.loads(content)
                for key in self.data:
                    if key in loaded:
                        self.data[key] = loaded[key]
            log_info(f"Loaded daily data for {len(self.data.get('users', {}))} users.")
        except Exception as e:
            log_error(f"Failed to load daily data: {e}")

    async def _save_data(self):
        try:
            temp_path = DAILY_DATA_FILE + ".tmp"
            async with aiofiles.open(temp_path, json.get_write_mode()) as f:
                await f.write(json.dumps(self.data))
            os.replace(temp_path, DAILY_DATA_FILE)
        except Exception as e:
            log_error(f"Failed to save daily data: {e}")

    async def register_user(self, user_id: str, ign: str, uuid: str):
        user_id = str(user_id)
        if not uuid or len(uuid) != 32:
             log_error(f"Invalid UUID provided for registration: {uuid} ({ign})")
             return

        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {
                "ign": ign,
                "uuid": uuid,
                "forced_profile": None
            }
            await self._save_data()
            log_info(f"Registered user {ign} ({user_id}).")
        elif self.data["users"][user_id]["ign"] != ign:
             self.data["users"][user_id]["ign"] = ign
             await self._save_data()

    def get_tracked_users(self) -> List[Tuple[str, str]]:
        return [(uid, info["uuid"]) for uid, info in self.data["users"].items()]

    async def set_user_profile(self, user_id: str, profile_name: Optional[str]):
        user_id = str(user_id)
        if user_id not in self.data["users"]:
            return False
        
        self.data["users"][user_id]["forced_profile"] = profile_name
        await self._save_data()
        log_info(f"Set forced profile for {user_id} to {profile_name}")
        return True

    async def sanitize_data(self):
        sanitize_stamp = "data/.last_sanitize"
        now = time.time()
        if os.path.exists(sanitize_stamp):
            last_run = os.path.getmtime(sanitize_stamp)
            if now - last_run < 86400:
                log_info("Skipping sanitize_data (ran within last 24h).")
                return

        log_info("Sanitizing daily data...")
        updates = False
        for user_id, info in self.data["users"].items():
            uuid = info.get("uuid", "")
            ign = info.get("ign", "")

            if not uuid or len(uuid) != 32:
                log_info(f"Detected invalid UUID for {ign} ({uuid}). Fetching correct UUID...")
                new_uuid = await get_uuid(ign)
                if new_uuid:
                    self.data["users"][user_id]["uuid"] = new_uuid
                    log_info(f"Fixed UUID for {ign}: {new_uuid}")
                    updates = True
                else:
                    log_error(f"Failed to fix UUID for {ign}")

        if updates:
            await self._save_data()
            log_info("Daily data sanitized and saved.")
        else:
            log_info("Daily data is clean.")

        with open(sanitize_stamp, "w") as f:
            f.write(str(now))
