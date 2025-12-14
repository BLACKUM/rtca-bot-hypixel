import json
import os
from typing import Dict, List, Optional
from core.logger import log_info, log_error, log_debug

DATA_FILE = "data/rng_data.json"

from core.config import RNG_DROPS

class RngManager:
    def __init__(self):
        self.data: Dict[str, Dict[str, Dict[str, int]]] = {}
        self.load_data()

    def load_data(self):
        if not os.path.exists(DATA_FILE):
            self.data = {}
            log_info("No RNG data file found, starting fresh.")
            return
        
        try:
            with open(DATA_FILE, 'r') as f:
                loaded_data = json.load(f)
                
            self.data = {}
            migrated = False
            
            for user_id, user_data in loaded_data.items():
                if "_settings" in user_data:
                     pass
                
                has_floor_keys = any(k in RNG_DROPS for k in user_data.keys())
                
                if not has_floor_keys and user_data:
                    if "Main" in user_data:
                        self.data[user_id] = user_data["Main"]
                        migrated = True
                        
                        if "_settings" in user_data:
                             self.data[user_id]["_settings"] = user_data["_settings"]
                             
                    else:
                        found = False
                        for p_name, p_data in user_data.items():
                            if p_name == "_settings": continue
                            if isinstance(p_data, dict):
                                self.data[user_id] = p_data
                                if "_settings" in user_data:
                                     self.data[user_id]["_settings"] = user_data["_settings"]
                                migrated = True
                                found = True
                                break
                        if not found:
                             self.data[user_id] = user_data
                else:
                    self.data[user_id] = user_data

            if migrated:
                log_info("Migrated RNG data from Profiles to Flat structure.")
                self.save_data()
                
            log_info(f"Loaded RNG data for {len(self.data)} users.")
        except Exception as e:
            log_error(f"Failed to load RNG data: {e}")
            self.data = {}

    def save_data(self):
        try:
            with open(DATA_FILE, 'w') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            log_error(f"Failed to save RNG data: {e}")

    def get_user_stats(self, user_id: str) -> Dict[str, Dict[str, int]]:
        raw = self.data.get(user_id, {})
        return {k: v for k, v in raw.items() if not k.startswith("_")}

    def get_floor_stats(self, user_id: str, floor_name: str) -> Dict[str, int]:
        user_stats = self.get_user_stats(user_id)
        return user_stats.get(floor_name, {})

    def update_drop(self, user_id: str, floor_name: str, item_name: str, change: int) -> int:
        user_id = str(user_id)
        if user_id not in self.data:
            self.data[user_id] = {}
        
        if floor_name not in self.data[user_id]:
            self.data[user_id][floor_name] = {}
        
        current_count = self.data[user_id][floor_name].get(item_name, 0)
        new_count = current_count + change
        
        if new_count < 0:
            new_count = 0
            
        self.data[user_id][floor_name][item_name] = new_count
        self.save_data()
        
        log_info(f"Updated drop for {user_id}: {item_name} -> {new_count} (Change: {change})")
        return new_count

    def set_drop_count(self, user_id: str, floor_name: str, item_name: str, count: int) -> int:
        user_id = str(user_id)
        if user_id not in self.data:
            self.data[user_id] = {}
        
        if floor_name not in self.data[user_id]:
            self.data[user_id][floor_name] = {}
            
        if count < 0:
            count = 0
            
        self.data[user_id][floor_name][item_name] = count
        self.save_data()
        
        log_info(f"Set drop for {user_id}: {item_name} -> {count}")
        return count

    def get_default_target(self, user_id: str) -> Optional[str]:
        return self.data.get(user_id, {}).get("_settings", {}).get("default_target")

    def set_default_target(self, user_id: str, target_id: str):
        user_id = str(user_id)
        target_id = str(target_id)
        
        if user_id not in self.data:
            self.data[user_id] = {}
        
        if "_settings" not in self.data[user_id]:
            self.data[user_id]["_settings"] = {}
            
        self.data[user_id]["_settings"]["default_target"] = target_id
        self.save_data()
        log_info(f"Set default target search for {user_id} to {target_id}")

rng_manager = RngManager()
