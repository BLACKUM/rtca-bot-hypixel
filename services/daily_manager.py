import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from core.logger import log_info, log_error, log_debug
from services.xp_calculations import get_dungeon_level
from services.api import get_uuid

DAILY_DATA_FILE = "data/daily_data.json"

class DailyManager:
    def __init__(self):
        self.data = {
            "users": {},
            "daily_snapshots": {},
            "monthly_snapshots": {},
            "current_xp": {},
            "last_daily_reset": 0,
            "last_monthly_reset": 0,
            "last_updated": 0
        }
        self.load_data()

    def load_data(self):
        if not os.path.exists(DAILY_DATA_FILE):
            log_info("No daily data file found, starting fresh.")
            self._save_data()
            return

        try:
            with open(DAILY_DATA_FILE, 'r') as f:
                loaded = json.load(f)
                for key in self.data:
                    if key in loaded:
                        self.data[key] = loaded[key]
            log_info(f"Loaded daily data for {len(self.data.get('users', {}))} users.")
        except Exception as e:
            log_error(f"Failed to load daily data: {e}")

    def _save_data(self):
        try:
            with open(DAILY_DATA_FILE, 'w') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            log_error(f"Failed to save daily data: {e}")

    def register_user(self, user_id: str, ign: str, uuid: str):
        user_id = str(user_id)
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {
                "ign": ign,
                "uuid": uuid
            }
            self._save_data()
            log_info(f"Registered user {ign} ({user_id}) for daily tracking.")
        elif self.data["users"][user_id]["ign"] != ign:
             self.data["users"][user_id]["ign"] = ign
             self._save_data()

    def get_tracked_users(self) -> List[Tuple[str, str]]:
        return [(uid, info["uuid"]) for uid, info in self.data["users"].items()]

    def update_user_data(self, user_id: str, xp_data: dict):
        user_id = str(user_id)
        now = int(time.time())
        
        self.data["current_xp"][user_id] = {
            "timestamp": now,
            "cata_xp": xp_data["catacombs"],
            "classes": xp_data["classes"]
        }
        
        if user_id not in self.data["daily_snapshots"]:
             self.data["daily_snapshots"][user_id] = self.data["current_xp"][user_id]
        
        if user_id not in self.data["monthly_snapshots"]:
             self.data["monthly_snapshots"][user_id] = self.data["current_xp"][user_id]
             
        self.data["last_updated"] = now
        self._save_data()

    def check_resets(self):
        now = datetime.now(timezone.utc)
        
        last_reset_ts = self.data.get("last_daily_reset", 0)
        last_reset_date = datetime.fromtimestamp(last_reset_ts, timezone.utc)
        
        if now.date() > last_reset_date.date():
            log_info("Performing Daily Reset...")
            self.data["daily_snapshots"] = self.data["current_xp"].copy()
            self.data["last_daily_reset"] = int(now.timestamp())
        self._save_data()
             
        last_month_ts = self.data.get("last_monthly_reset", 0)
        last_month_date = datetime.fromtimestamp(last_month_ts, timezone.utc)
        
        if now.month != last_month_date.month or now.year != last_month_date.year:
            log_info("Performing Monthly Reset...")
            self.data["monthly_snapshots"] = self.data["current_xp"].copy()
            self.data["last_monthly_reset"] = int(now.timestamp())
            self._save_data()

    def get_last_updated(self) -> int:
        return self.data.get("last_updated", 0)

    def get_daily_stats(self, user_id: str):
        return self._calculate_stats(user_id, "daily_snapshots")

    def get_monthly_stats(self, user_id: str):
        return self._calculate_stats(user_id, "monthly_snapshots")

    def _calculate_stats(self, user_id: str, snapshot_key: str):
        user_id = str(user_id)
        current = self.data["current_xp"].get(user_id)
        start = self.data[snapshot_key].get(user_id)
        
        if not current or not start:
            return None
            
        stats = {
            "cata_gained": current["cata_xp"] - start["cata_xp"],
            "cata_start_xp": start["cata_xp"],
            "cata_current_xp": current["cata_xp"],
            "cata_start_lvl": get_dungeon_level(start["cata_xp"]),
            "cata_current_lvl": get_dungeon_level(current["cata_xp"]),
            "classes": {}
        }
        
        for cls, xp in current["classes"].items():
            start_xp = start["classes"].get(cls, 0)
            stats["classes"][cls] = {
                "gained": xp - start_xp,
                "start_xp": start_xp,
                "current_xp": xp,
                "start_lvl": get_dungeon_level(start_xp),
                "current_lvl": get_dungeon_level(xp)
            }
            
        return stats

    def get_leaderboard(self, type="daily"):
        snapshot_key = "daily_snapshots" if type == "daily" else "monthly_snapshots"
        leaderboard_map = {}
        
        for user_id, info in self.data["users"].items():
            stats = self._calculate_stats(user_id, snapshot_key)
            if stats:
                ign = info["ign"]
                if ign not in leaderboard_map or stats["cata_gained"] > leaderboard_map[ign]["gained"]:
                    leaderboard_map[ign] = {
                        "ign": ign,
                        "gained": stats["cata_gained"],
                        "user_id": user_id
                    }
        
        leaderboard = list(leaderboard_map.values())
        leaderboard.sort(key=lambda x: x["gained"], reverse=True)
        return leaderboard

    # i have no idea why uuid was invalid in the first place, but i've made this function to fix it in the future
    # somebody changed a name... ig that's why
    async def sanitize_data(self):
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
            self._save_data()
            log_info("Daily data sanitized and saved.")
        else:
            log_info("Daily data is clean.")

daily_manager = DailyManager()
