import json
import os
from typing import Dict, Optional
from core.logger import log_info, log_error

LINK_FILE = "data/user_links.json"

class LinkManager:
    def __init__(self):
        self.links: Dict[str, str] = {}
        self.load_links()

    def load_links(self):
        if not os.path.exists(LINK_FILE):
            self.links = {}
            log_info("No user links file found, starting fresh.")
            return
        
        try:
            with open(LINK_FILE, 'r') as f:
                self.links = json.load(f)
            log_info(f"Loaded {len(self.links)} user links.")
        except Exception as e:
            log_error(f"Failed to load user links: {e}")
            self.links = {}

    def save_links(self):
        try:
            with open(LINK_FILE, 'w') as f:
                json.dump(self.links, f, indent=4)
        except Exception as e:
            log_error(f"Failed to save user links: {e}")

    def link_user(self, discord_id: int, ign: str):
        self.links[str(discord_id)] = ign
        self.save_links()
        log_info(f"Linked discord user {discord_id} to IGN {ign}")

    def unlink_user(self, discord_id: int) -> bool:
        str_id = str(discord_id)
        if str_id in self.links:
            del self.links[str_id]
            self.save_links()
            log_info(f"Unlinked discord user {discord_id}")
            return True
        return False

    def get_link(self, discord_id: int) -> Optional[str]:
        return self.links.get(str(discord_id))

link_manager = LinkManager()
