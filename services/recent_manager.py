from services import json_utils as json
import os
import aiofiles
import re
import time
from core.logger import log_info, log_error, log_debug

RECENT_DATA_FILE = "data/recent_teammates.json"

def clean_mc_formatting(text):
    if not text: return ""
    return re.sub(r'§.', '', text).strip()

class RecentManager:
    def __init__(self):
        self.data = {} 
        # Structure:
        # {
        #   "user_uuid": {
        #       "_meta": { "last_scan_ts": 0 },
        #       "teammate_uuid": {
        #           "ign": "Name",
        #           "count": X,
        #           "last_floor": "M7",
        #           "last_ts": 12345,
        #           "last_class": "Archer",
        #           "last_class_level": 50
        #       }
        #   }
        # }

    async def initialize(self):
        await self.load_data()

    async def load_data(self):
        if not os.path.exists(RECENT_DATA_FILE):
             await self._save_data()
             return
        try:
            async with aiofiles.open(RECENT_DATA_FILE, 'rb') as f:
                content = await f.read()
                self.data = json.loads(content)
                log_info(f"Loaded recent data for {len(self.data)} users.")
        except Exception as e:
            log_error(f"Failed to load recent data: {e}")

    async def _save_data(self):
        try:
            os.makedirs(os.path.dirname(RECENT_DATA_FILE), exist_ok=True)
            async with aiofiles.open(RECENT_DATA_FILE, 'wb') as f:
                await f.write(json.dumps(self.data, indent=4))
        except Exception as e:
            log_error(f"Failed to save recent data: {e}")

    async def update_runs(self, user_uuid, runs):
        if not runs: return
        user_uuid = str(user_uuid)
        
        if user_uuid not in self.data:
            self.data[user_uuid] = { "_meta": { "last_scan_ts": 0 } }
            
        user_data = self.data[user_uuid]
        meta = user_data.get("_meta", { "last_scan_ts": 0 })
        user_data["_meta"] = meta
        
        last_scan = meta["last_scan_ts"]
        new_scan_ts = last_scan
        updated = False
        
        sorted_runs = sorted(runs, key=lambda x: x.get("completion_ts", 0))
        
        for run in sorted_runs:
            ts = run.get("completion_ts", 0) / 1000
            if ts <= last_scan:
                continue
                
            if ts > new_scan_ts:
                new_scan_ts = ts
                
            d_type = run.get("dungeon_type", "catacombs")
            tier = run.get("dungeon_tier", 0)
            is_master = "master" in d_type
            floor_prefix = "M" if is_master else "F"
            floor_name = f"{floor_prefix}{tier}"
            if tier == 0 and not is_master: floor_name = "Entrance"

            for p in run.get("participants", []):
                p_uuid = p.get("player_uuid")
                if not p_uuid or p_uuid == user_uuid: continue
                
                if p_uuid not in user_data:
                    user_data[p_uuid] = {
                        "ign": "Unknown",
                        "count": 0,
                        "last_floor": floor_name,
                        "last_ts": ts,
                        "last_class": "Unknown",
                        "last_class_level": 0
                    }
                
                tm = user_data[p_uuid]
                tm["count"] += 1
                
                tm["last_floor"] = floor_name
                tm["last_ts"] = ts
                
                raw_name = p.get("display_name", "Unknown")
                tm["ign"] = clean_mc_formatting(raw_name.split(":")[0])
                
                clean_display = clean_mc_formatting(raw_name)
                if ":" in clean_display:
                    parts = clean_display.split(":")
                    if len(parts) > 1:
                        class_part = parts[1].strip()
                        if "(" in class_part:
                            c_name = class_part.split("(")[0].strip()
                            try:
                                c_lvl = int(class_part.split("(")[1].replace(")", "").strip())
                            except ValueError:
                                c_lvl = 0
                            tm["last_class"] = c_name
                            tm["last_class_level"] = c_lvl
                updated = True

        if updated:
            user_data["_meta"]["last_scan_ts"] = new_scan_ts
            await self._save_data()

    def get_teammates(self, user_uuid):
        user_uuid = str(user_uuid)
        if user_uuid not in self.data:
            return []
            
        teammates = []
        for pid, data in self.data[user_uuid].items():
            if pid == "_meta": continue

            teammates.append((data.get("ign", "Unknown"), data))
            
        teammates.sort(key=lambda x: x[1]["count"], reverse=True)
        return teammates
