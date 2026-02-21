from services import json_utils as json
import os
import aiofiles
from typing import Dict, Optional
from core.logger import log_info, log_error

NAMES_FILE = "data/custom_names.json"

class NameManager:
    def __init__(self):
        self.names: Dict[str, dict] = {}

    async def initialize(self):
        await self.load_names()

    async def load_names(self):
        if not os.path.exists(NAMES_FILE):
             self.names = {}
             if not os.path.exists("data"):
                 os.makedirs("data")
             async with aiofiles.open(NAMES_FILE, json.get_write_mode()) as f:
                 await f.write(json.dumps({}, indent=4))
             log_info("No custom names file found, created empty one.")
             return
         
        try:
             async with aiofiles.open(NAMES_FILE, json.get_read_mode()) as f:
                 content = await f.read()
                 self.names = json.loads(content)
             log_info(f"Loaded {len(self.names)} custom names.")
        except Exception as e:
             log_error(f"Failed to load custom names: {e}")
             self.names = {}

    async def save_names(self):
        try:
            async with aiofiles.open(NAMES_FILE, json.get_write_mode()) as f:
                await f.write(json.dumps(self.names, indent=4))
        except Exception as e:
            log_error(f"Failed to save custom names: {e}")

    def get_names(self) -> Dict[str, dict]:
        return self.names

    async def set_name(self, ign: str, display_name: str, color: str):
        self.names[ign.lower()] = {
            "display": display_name,
            "color": color
        }
        await self.save_names()
        log_info(f"Set custom name for {ign}: {display_name} ({color})")

name_manager = NameManager()
