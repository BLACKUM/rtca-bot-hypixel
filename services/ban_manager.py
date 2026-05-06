from services import json_utils as json
import os
import time
import aiofiles
from typing import Dict, Optional, List
from core.logger import log_info, log_error

BANS_FILE = "data/ip_bans.json"


class BanManager:
    def __init__(self):
        self.bans: Dict[str, dict] = {}

    async def initialize(self):
        await self.load_bans()

    async def load_bans(self):
        if not os.path.exists(BANS_FILE):
            self.bans = {}
            if not os.path.exists("data"):
                os.makedirs("data")
            async with aiofiles.open(BANS_FILE, json.get_write_mode()) as f:
                await f.write(json.dumps({}, indent=4))
            log_info("No IP bans file found, created empty one.")
            return

        try:
            async with aiofiles.open(BANS_FILE, json.get_read_mode()) as f:
                content = await f.read()
                self.bans = json.loads(content)
            log_info(f"Loaded {len(self.bans)} IP bans.")
        except Exception as e:
            log_error(f"Failed to load IP bans: {e}")
            self.bans = {}

    async def save_bans(self):
        try:
            async with aiofiles.open(BANS_FILE, json.get_write_mode()) as f:
                await f.write(json.dumps(self.bans, indent=4))
        except Exception as e:
            log_error(f"Failed to save IP bans: {e}")

    def is_banned(self, ip: str) -> bool:
        return ip in self.bans

    def get_ban(self, ip: str) -> Optional[dict]:
        return self.bans.get(ip)

    def get_all(self) -> Dict[str, dict]:
        return self.bans

    async def ban(self, ip: str, reason: str, banned_by: int) -> bool:
        ip = ip.strip()
        if not ip:
            return False
        self.bans[ip] = {
            "reason": reason or "No reason provided",
            "banned_by": str(banned_by),
            "banned_at": int(time.time()),
        }
        await self.save_bans()
        log_info(f"IP banned: {ip} by {banned_by} (reason: {reason})")
        return True

    async def unban(self, ip: str) -> bool:
        ip = ip.strip()
        if ip not in self.bans:
            return False
        del self.bans[ip]
        await self.save_bans()
        log_info(f"IP unbanned: {ip}")
        return True


ban_manager = BanManager()
