import json
import os
import aiofiles
from typing import Dict, Optional
from core.logger import log_info, log_error

LINK_FILE = "data/user_links.json"

class LinkManager:
    def __init__(self):
        self.links: Dict[str, str] = {}
    async def initialize(self):
        await self.load_links()

    async def load_links(self):
        if not os.path.exists(LINK_FILE):
             self.links = {}
             log_info("No user links file found, starting fresh.")
             return
         
        try:
             async with aiofiles.open(LINK_FILE, 'r') as f:
                 content = await f.read()
                 self.links = json.loads(content)
             log_info(f"Loaded {len(self.links)} user links.")
        except Exception as e:
             log_error(f"Failed to load user links: {e}")
             self.links = {}

    async def save_links(self):
        try:
            async with aiofiles.open(LINK_FILE, 'w') as f:
                await f.write(json.dumps(self.links, indent=4))
        except Exception as e:
            log_error(f"Failed to save user links: {e}")

    async def link_user(self, discord_id: int, ign: str):
        self.links[str(discord_id)] = ign
        await self.save_links()
        log_info(f"Linked discord user {discord_id} to IGN {ign}")

    async def unlink_user(self, discord_id: int) -> bool:
        str_id = str(discord_id)
        if str_id in self.links:
            del self.links[str_id]
            await self.save_links()
            log_info(f"Unlinked discord user {discord_id}")
            return True
        return False

    def get_link(self, discord_id: int) -> Optional[str]:
        return self.links.get(str(discord_id))
