import json
import os
import time
import aiofiles
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from core.logger import log_info, log_error, log_debug
from services.xp_calculations import get_dungeon_level
from services.api import get_uuid, get_dungeon_xp
from datetime import timedelta
import asyncio

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
    async def initialize(self):
        await self.load_data()

    def get_reset_timestamps(self) -> Tuple[int, int]:
        now = datetime.now(timezone.utc)
        target_daily = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        next_daily_ts = int(target_daily.timestamp())
        
        if now.month == 12:
            target_monthly = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            target_monthly = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        next_monthly_ts = int(target_monthly.timestamp())
        
        return next_daily_ts, next_monthly_ts

    async def force_update_all(self, status_message=None):
        tracked_users = self.get_tracked_users()
        total_users = len(tracked_users)
        
        if total_users == 0:
            return 0, 0, 0 # updated, errors, total
            
        updated_count = 0
        errors = 0
        processed_count = 0
        sem = asyncio.Semaphore(5)
        
        async def update_user(user_id, uuid):
            nonlocal updated_count, errors, processed_count
            async with sem:
                try:
                    if not uuid:
                        log_error(f"Skipping update for {user_id}: No UUID")
                        errors += 1
                    else:
                        xp_data = await get_dungeon_xp(uuid)
                        if xp_data:
                            self.update_user_data(user_id, xp_data)
                            updated_count += 1
                        else:
                            errors += 1
                except Exception as e:
                    log_error(f"Error updating user {user_id}: {e}")
                    errors += 1
                finally:
                    processed_count += 1
                    if status_message and (processed_count <= 5 or processed_count % 5 == 0):
                        try:
                            asyncio.create_task(status_message.edit(
                                content=f"🔄 **Force Update In Progress**\nProcessing: {processed_count}/{total_users}\nUpdated: {updated_count}\nErrors: {errors}"
                            ))
                        except Exception:
                            pass

        tasks = [update_user(uid, uuid) for uid, uuid in tracked_users]
        await asyncio.gather(*tasks)
                
        return updated_count, errors, total_users

    async def load_data(self):
        if not os.path.exists(DAILY_DATA_FILE):
            log_info("No daily data file found, starting fresh.")
            await self._save_data()
            return

        try:
            async with aiofiles.open(DAILY_DATA_FILE, 'r') as f:
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
            async with aiofiles.open(DAILY_DATA_FILE, 'w') as f:
                await f.write(json.dumps(self.data, indent=4))
        except Exception as e:
            log_error(f"Failed to save daily data: {e}")

    async def register_user(self, user_id: str, ign: str, uuid: str):
        user_id = str(user_id)
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {
                "ign": ign,
                "uuid": uuid
            }
            await self._save_data()
            log_info(f"Registered user {ign} ({user_id}) for daily tracking.")
        elif self.data["users"][user_id]["ign"] != ign:
             self.data["users"][user_id]["ign"] = ign
             await self._save_data()

    def get_tracked_users(self) -> List[Tuple[str, str]]:
        return [(uid, info["uuid"]) for uid, info in self.data["users"].items()]

    async def update_user_data(self, user_id: str, xp_data: dict):
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
        await self._save_data()

    async def check_resets(self):
        now = datetime.now(timezone.utc)
        
        last_reset_ts = self.data.get("last_daily_reset", 0)
        last_reset_date = datetime.fromtimestamp(last_reset_ts, timezone.utc)
        
        if now.date() > last_reset_date.date():
            log_info("Performing Daily Reset...")
            self.data["daily_snapshots"] = self.data["current_xp"].copy()
            self.data["last_daily_reset"] = int(now.timestamp())
        await self._save_data()
             
        last_month_ts = self.data.get("last_monthly_reset", 0)
        last_month_date = datetime.fromtimestamp(last_month_ts, timezone.utc)
        
        if now.month != last_month_date.month or now.year != last_month_date.year:
            log_info("Performing Monthly Reset...")
            self.data["monthly_snapshots"] = self.data["current_xp"].copy()
            self.data["last_monthly_reset"] = int(now.timestamp())
            await self._save_data()

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
            await self._save_data()
            log_info("Daily data sanitized and saved.")
        else:
            log_info("Daily data is clean.")

daily_manager = DailyManager()
